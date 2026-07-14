"""
Dump/test JSON returned by the current frontend/API scaffold.

This tests:
- app.frontend.api_client.py indirectly through HTTP API calls
- app.frontend.dashboard.py through direct Dashboard method calls
- app.frontend.app_shell.py render helpers when possible
- app.frontend.portfolio_summary.py import/scaffold visibility
- app.frontend.watchlist.py import/scaffold visibility

Requires uvicorn to be running for HTTP API checks:
    uvicorn app.core.main:app --host 0.0.0.0 --port 8000 --reload

Outputs JSON files to:
    tmp/frontend_json/
"""

import dataclasses
import datetime as dt
import importlib
import inspect
import json
import os
import traceback
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
USER_ID = int(os.getenv("USER_ID", "1"))
OUTDIR = Path(os.getenv("OUTDIR", "tmp/frontend_json"))


def to_jsonable(value: Any) -> Any:
    """Convert dataclasses, datetimes, objects, etc. into JSON-safe data."""
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()

    if dataclasses.is_dataclass(value):
        return to_jsonable(dataclasses.asdict(value))

    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(v) for v in value]

    if hasattr(value, "__dict__"):
        data = {
            k: v
            for k, v in vars(value).items()
            if not k.startswith("_")
        }
        return to_jsonable(data)

    return repr(value)


def write_json(name: str, payload: Any) -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    path = OUTDIR / f"{name}.json"
    path.write_text(json.dumps(to_jsonable(payload), indent=2, sort_keys=True))
    print(f"WROTE {path}")


def fetch_json(path: str) -> dict:
    url = f"{BASE_URL}{path}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "dev-dump-frontend-json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
            try:
                parsed = json.loads(body)
            except Exception:
                parsed = {"raw": body}

            return {
                "ok": True,
                "status": response.status,
                "url": url,
                "data": parsed,
            }

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"raw": body}

        return {
            "ok": False,
            "status": e.code,
            "url": url,
            "data": parsed,
        }

    except Exception as e:
        return {
            "ok": False,
            "status": None,
            "url": url,
            "error": f"{type(e).__name__}: {e}",
        }


def dump_http_api_json() -> dict:
    """Dump the JSON currently returned by the actual API endpoints."""
    endpoints = {
        "health": "/api/health",
        "dashboard_full": f"/api/api/dashboard/?user_id={USER_ID}",
        "portfolio_summary": f"/api/api/dashboard/portfolio?user_id={USER_ID}",
        "watchlist": f"/api/api/dashboard/watchlist?user_id={USER_ID}",
        "opportunities": (
            f"/api/api/dashboard/opportunities?"
            f"user_id={USER_ID}&limit=10"
        ),
        "risk_settings": f"/api/api/dashboard/risk-settings?user_id={USER_ID}",
    }

    results = {}

    print("\n=== HTTP API JSON ===")
    for name, path in endpoints.items():
        result = fetch_json(path)
        results[name] = result
        status = result.get("status")
        ok = result.get("ok")
        print(f"{name}: ok={ok} status={status}")
        write_json(f"http_{name}", result)

    write_json("http_all", results)
    return results


def dump_module_inventory() -> dict:
    """Show what the Python frontend scaffold actually exposes."""
    module_names = [
        "app.frontend.api_client",
        "app.frontend.app_shell",
        "app.frontend.dashboard",
        "app.frontend.portfolio_summary",
        "app.frontend.watchlist",
    ]

    inventory = {}

    print("\n=== FRONTEND MODULE INVENTORY ===")
    for module_name in module_names:
        try:
            module = importlib.import_module(module_name)
            public = [name for name in dir(module) if not name.startswith("_")]

            callables = {}
            classes = []

            for name in public:
                value = getattr(module, name)

                if inspect.isclass(value) and value.__module__ == module.__name__:
                    classes.append(name)

                if callable(value) and getattr(value, "__module__", None) == module.__name__:
                    try:
                        callables[name] = str(inspect.signature(value))
                    except Exception:
                        callables[name] = "signature unavailable"

            inventory[module_name] = {
                "ok": True,
                "public": public,
                "classes": classes,
                "callables": callables,
            }

            print(f"\nOK: {module_name}")
            print("classes:", classes)
            print("callables:", callables)

        except Exception as e:
            inventory[module_name] = {
                "ok": False,
                "error": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc(),
            }
            print(f"\nFAILED: {module_name}: {type(e).__name__}: {e}")

    write_json("module_inventory", inventory)
    return inventory


def try_direct_dashboard_methods() -> dict:
    """
    Call the direct Python dashboard methods.

    This helps test app.frontend.dashboard.py without going through HTTP.
    """
    print("\n=== DIRECT DASHBOARD METHOD JSON ===")

    results = {}

    try:
        from app.core.database import SessionLocal
        from app.frontend.dashboard import Dashboard

        dashboard = Dashboard()
        db = SessionLocal()

        try:
            method_specs = [
                ("portfolio_summary", "get_portfolio_summary", [USER_ID, db]),
                ("watchlist", "get_watchlist", [USER_ID, db]),
                ("opportunities", "get_top_opportunities", [USER_ID, db, 10]),
                ("open_trades", "get_open_trades", [USER_ID, db]),
                ("recent_news", "get_recent_news", [USER_ID, db]),
                ("risk_settings", "get_risk_settings", [USER_ID, db]),
                ("dashboard_data", "get_dashboard_data", [USER_ID, db]),
                ("dashboard", "get_dashboard", [USER_ID, db]),
            ]

            for output_name, method_name, args in method_specs:
                if not hasattr(dashboard, method_name):
                    results[output_name] = {
                        "ok": False,
                        "skipped": True,
                        "reason": f"Dashboard has no {method_name} method",
                    }
                    continue

                method = getattr(dashboard, method_name)

                try:
                    value = method(*args)
                    results[output_name] = {
                        "ok": True,
                        "method": method_name,
                        "data": to_jsonable(value),
                    }
                    print(f"{output_name}: OK via {method_name}")

                except TypeError:
                    # Some local methods may use a different signature.
                    results[output_name] = {
                        "ok": False,
                        "method": method_name,
                        "error": "TypeError, likely method signature mismatch",
                        "signature": str(inspect.signature(method)),
                        "traceback": traceback.format_exc(),
                    }
                    print(f"{output_name}: TypeError via {method_name}")

                except Exception as e:
                    results[output_name] = {
                        "ok": False,
                        "method": method_name,
                        "error": f"{type(e).__name__}: {e}",
                        "traceback": traceback.format_exc(),
                    }
                    print(f"{output_name}: ERROR via {method_name}: {e}")

        finally:
            db.close()

    except Exception as e:
        results["setup_error"] = {
            "ok": False,
            "error": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc(),
        }
        print(f"direct dashboard setup failed: {type(e).__name__}: {e}")

    write_json("direct_dashboard_methods", results)
    return results


def try_app_shell_renderers(http_results: dict) -> dict:
    """
    Try app_shell render helpers against the dashboard JSON.

    These may return dicts, strings, or internal render objects depending on
    how the scaffold is implemented.
    """
    print("\n=== APP SHELL RENDER HELPERS ===")

    results = {}

    dashboard_payload = (
        http_results
        .get("dashboard_full", {})
        .get("data", {})
    )

    try:
        shell = importlib.import_module("app.frontend.app_shell")

        render_inputs = {
            "render_portfolio_section": dashboard_payload.get("portfolio_summary"),
            "render_watchlist_section": dashboard_payload.get("watchlist"),
            "render_opportunities_section": dashboard_payload.get("top_opportunities"),
            "render_trades_section": dashboard_payload.get("open_trades"),
            "render_news_section": dashboard_payload.get("recent_news"),
            "render_risk_settings_section": dashboard_payload.get("risk_settings"),
        }

        for function_name, payload in render_inputs.items():
            if not hasattr(shell, function_name):
                results[function_name] = {
                    "ok": False,
                    "skipped": True,
                    "reason": "function not present",
                }
                continue

            fn = getattr(shell, function_name)

            try:
                signature = inspect.signature(fn)
                required_positional = [
                    p
                    for p in signature.parameters.values()
                    if p.default is inspect._empty
                    and p.kind in (
                        inspect.Parameter.POSITIONAL_ONLY,
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    )
                ]

                if len(required_positional) > 1:
                    results[function_name] = {
                        "ok": False,
                        "skipped": True,
                        "reason": "more than one required positional arg",
                        "signature": str(signature),
                    }
                    continue

                value = fn(payload)
                results[function_name] = {
                    "ok": True,
                    "signature": str(signature),
                    "data": to_jsonable(value),
                }
                print(f"{function_name}: OK")

            except Exception as e:
                results[function_name] = {
                    "ok": False,
                    "error": f"{type(e).__name__}: {e}",
                    "traceback": traceback.format_exc(),
                }
                print(f"{function_name}: ERROR: {e}")

    except Exception as e:
        results["setup_error"] = {
            "ok": False,
            "error": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc(),
        }

    write_json("app_shell_renderers", results)
    return results


def main():
    print(f"BASE_URL={BASE_URL}")
    print(f"USER_ID={USER_ID}")
    print(f"OUTDIR={OUTDIR}")

    module_inventory = dump_module_inventory()
    http_results = dump_http_api_json()
    direct_dashboard = try_direct_dashboard_methods()
    shell_renderers = try_app_shell_renderers(http_results)

    all_results = {
        "module_inventory": module_inventory,
        "http_results": http_results,
        "direct_dashboard": direct_dashboard,
        "shell_renderers": shell_renderers,
    }

    write_json("all_frontend_checks", all_results)

    print("\nDone.")
    print(f"Open JSON files in: {OUTDIR}")


if __name__ == "__main__":
    main()

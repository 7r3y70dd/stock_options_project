"""Options-specific analysis and utilities.

Uses lazy imports to avoid requiring QuantLib unless explicitly imported.
"""


def __getattr__(name):
    """Lazy import QuantLibPricingEngine only when accessed."""
    if name == "QuantLibPricingEngine":
        from app.options.pricing import QuantLibPricingEngine
        return QuantLibPricingEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["QuantLibPricingEngine"]

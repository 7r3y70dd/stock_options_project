"""Options-specific analysis and utilities."""

__all__ = []

# Lazy import to avoid requiring QuantLib if not needed
def __getattr__(name):
    if name == "QuantLibPricingEngine":
        try:
            from app.options.pricing import QuantLibPricingEngine
            return QuantLibPricingEngine
        except ImportError:
            raise ImportError(
                f"Cannot import {name}. QuantLib is required for pricing functionality. "
                "Install it with: pip install QuantLib"
            )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

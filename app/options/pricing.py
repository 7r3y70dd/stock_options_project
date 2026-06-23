"""QuantLib-based option pricing engine for theoretical valuation.

Provides Black-Scholes pricing and Greeks calculation using QuantLib.
"""

import logging
from typing import Optional, Dict, Tuple
from datetime import datetime

try:
    import QuantLib as ql
    QUANTLIB_AVAILABLE = True
except ImportError:
    QUANTLIB_AVAILABLE = False

logger = logging.getLogger(__name__)


class QuantLibPricingEngine:
    """Option pricing engine using QuantLib's Black-Scholes model.
    
    Calculates theoretical option prices and Greeks for comparison with market prices.
    """

    def __init__(self):
        """Initialize pricing engine.
        
        Raises:
            ImportError: If QuantLib is not installed.
        """
        if not QUANTLIB_AVAILABLE:
            raise ImportError(
                "QuantLib is not installed. Install it with: pip install QuantLib"
            )
        logger.info("QuantLibPricingEngine initialized")

    @staticmethod
    def calculate_theoretical_price(
        underlying_price: float,
        strike: float,
        time_to_expiration: float,
        risk_free_rate: float,
        volatility: float,
        contract_type: str,
        dividend_yield: float = 0.0,
    ) -> Optional[float]:
        """Calculate theoretical option price using Black-Scholes model.
        
        Args:
            underlying_price: Current price of underlying asset
            strike: Strike price of the option
            time_to_expiration: Time to expiration in years (e.g., 0.25 for 3 months)
            risk_free_rate: Risk-free interest rate as decimal (e.g., 0.05 for 5%)
            volatility: Implied volatility as decimal (e.g., 0.25 for 25%)
            contract_type: "call" or "put"
            dividend_yield: Dividend yield as decimal (default: 0.0)
            
        Returns:
            Theoretical option price, or None if calculation fails
        """
        try:
            if not QUANTLIB_AVAILABLE:
                logger.warning("QuantLib not available, cannot calculate theoretical price")
                return None
            
            if time_to_expiration <= 0:
                logger.warning(f"Invalid time to expiration: {time_to_expiration}")
                return None
            
            if volatility <= 0:
                logger.warning(f"Invalid volatility: {volatility}")
                return None
            
            # Set up QuantLib objects
            spot = ql.SimpleQuote(underlying_price)
            flat_ts = ql.FlatForwardCurve(
                0, ql.TARGET(), risk_free_rate, ql.Actual365Fixed()
            )
            dividend_ts = ql.FlatForwardCurve(
                0, ql.TARGET(), dividend_yield, ql.Actual365Fixed()
            )
            vol_ts = ql.BlackConstantVol(
                0, ql.TARGET(), volatility, ql.Actual365Fixed()
            )
            
            # Create process
            process = ql.BlackScholesMertonProcess(
                ql.QuoteHandle(spot),
                ql.YieldTermStructureHandle(dividend_ts),
                ql.YieldTermStructureHandle(flat_ts),
                ql.BlackVolTermStructureHandle(vol_ts),
            )
            
            # Create option
            exercise = ql.EuropeanExercise(
                ql.Date.todaysDate() + ql.Period(int(time_to_expiration * 365), ql.Days)
            )
            
            if contract_type.lower() == "call":
                payoff = ql.PlainVanillaPayoff(ql.Option.Call, strike)
            elif contract_type.lower() == "put":
                payoff = ql.PlainVanillaPayoff(ql.Option.Put, strike)
            else:
                logger.error(f"Invalid contract type: {contract_type}")
                return None
            
            option = ql.VanillaOption(payoff, exercise)
            
            # Calculate price using Black-Scholes engine
            engine = ql.AnalyticEuropeanEngine(process)
            option.setPricingEngine(engine)
            
            price = option.NPV()
            return float(price) if price > 0 else None
            
        except Exception as e:
            logger.error(f"Error calculating theoretical price: {e}", exc_info=True)
            return None

    @staticmethod
    def calculate_greeks(
        underlying_price: float,
        strike: float,
        time_to_expiration: float,
        risk_free_rate: float,
        volatility: float,
        contract_type: str,
        dividend_yield: float = 0.0,
    ) -> Optional[Dict[str, float]]:
        """Calculate option Greeks using Black-Scholes model.
        
        Args:
            underlying_price: Current price of underlying asset
            strike: Strike price of the option
            time_to_expiration: Time to expiration in years
            risk_free_rate: Risk-free interest rate as decimal
            volatility: Implied volatility as decimal
            contract_type: "call" or "put"
            dividend_yield: Dividend yield as decimal (default: 0.0)
            
        Returns:
            Dictionary with delta, gamma, theta, vega, or None if calculation fails
        """
        try:
            if not QUANTLIB_AVAILABLE:
                logger.warning("QuantLib not available, cannot calculate Greeks")
                return None
            
            if time_to_expiration <= 0 or volatility <= 0:
                logger.warning(f"Invalid inputs: time={time_to_expiration}, vol={volatility}")
                return None
            
            # Set up QuantLib objects
            spot = ql.SimpleQuote(underlying_price)
            flat_ts = ql.FlatForwardCurve(
                0, ql.TARGET(), risk_free_rate, ql.Actual365Fixed()
            )
            dividend_ts = ql.FlatForwardCurve(
                0, ql.TARGET(), dividend_yield, ql.Actual365Fixed()
            )
            vol_ts = ql.BlackConstantVol(
                0, ql.TARGET(), volatility, ql.Actual365Fixed()
            )
            
            # Create process
            process = ql.BlackScholesMertonProcess(
                ql.QuoteHandle(spot),
                ql.YieldTermStructureHandle(dividend_ts),
                ql.YieldTermStructureHandle(flat_ts),
                ql.BlackVolTermStructureHandle(vol_ts),
            )
            
            # Create option
            exercise = ql.EuropeanExercise(
                ql.Date.todaysDate() + ql.Period(int(time_to_expiration * 365), ql.Days)
            )
            
            if contract_type.lower() == "call":
                payoff = ql.PlainVanillaPayoff(ql.Option.Call, strike)
            elif contract_type.lower() == "put":
                payoff = ql.PlainVanillaPayoff(ql.Option.Put, strike)
            else:
                logger.error(f"Invalid contract type: {contract_type}")
                return None
            
            option = ql.VanillaOption(payoff, exercise)
            
            # Calculate Greeks using Black-Scholes engine
            engine = ql.AnalyticEuropeanEngine(process)
            option.setPricingEngine(engine)
            
            greeks = {
                "delta": float(option.delta()),
                "gamma": float(option.gamma()),
                "theta": float(option.theta()),
                "vega": float(option.vega()),
                "rho": float(option.rho()),
            }
            
            return greeks
            
        except Exception as e:
            logger.error(f"Error calculating Greeks: {e}", exc_info=True)
            return None

    @staticmethod
    def compare_prices(
        market_price: Optional[float],
        theoretical_price: Optional[float],
    ) -> Tuple[Optional[float], Optional[str]]:
        """Compare market price with theoretical price.
        
        Args:
            market_price: Market mid-price (bid + ask) / 2
            theoretical_price: Theoretical price from Black-Scholes
            
        Returns:
            Tuple of (price_difference, assessment) where assessment is:
            - "overpriced": market price > theoretical price
            - "underpriced": market price < theoretical price
            - "fair": prices are approximately equal
            - None if comparison cannot be made
        """
        if market_price is None or theoretical_price is None:
            return None, None
        
        if theoretical_price == 0:
            return None, None
        
        difference = market_price - theoretical_price
        pct_difference = (difference / theoretical_price) * 100
        
        # Classify based on percentage difference
        if pct_difference > 5:  # Market price > 5% above theoretical
            assessment = "overpriced"
        elif pct_difference < -5:  # Market price > 5% below theoretical
            assessment = "underpriced"
        else:
            assessment = "fair"
        
        return difference, assessment

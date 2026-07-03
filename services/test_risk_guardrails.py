"""Tests for risk guardrails in options trading."""
from services.options_service import (
    OptionContract,
    OptionsChainFilter,
    FilteredContract,
    OptionsService,
)


def test_options_chain_filter():
    """Test options chain filtering."""
    service = OptionsService()
    
    contracts = [
        OptionContract(
            symbol="AAPL",
            strike=150.0,
            expiration="2024-01-19",
            option_type="call",
            bid=2.5,
            ask=2.6,
            last=2.55,
            volume=1000,
            open_interest=5000,
            implied_volatility=0.25,
        ),
        OptionContract(
            symbol="AAPL",
            strike=150.0,
            expiration="2024-01-19",
            option_type="put",
            bid=2.4,
            ask=2.5,
            last=2.45,
            volume=800,
            open_interest=4000,
            implied_volatility=0.24,
        ),
    ]
    
    # Test filtering by calls
    calls = service.filter_chain(contracts, OptionsChainFilter.CALLS)
    assert len(calls) == 1
    assert calls[0].option_type == "call"
    
    # Test filtering by puts
    puts = service.filter_chain(contracts, OptionsChainFilter.PUTS)
    assert len(puts) == 1
    assert puts[0].option_type == "put"
    
    # Test scoring
    scored = service.score_contracts(contracts)
    assert len(scored) == 2
    assert all(isinstance(s, FilteredContract) for s in scored)

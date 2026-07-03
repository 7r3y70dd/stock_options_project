"""Options service for handling options chain data and filtering."""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class OptionsChainFilter(Enum):
    """Filter options for options chain queries."""
    ALL = "all"
    CALLS = "calls"
    PUTS = "puts"
    IN_THE_MONEY = "itm"
    OUT_OF_THE_MONEY = "otm"
    AT_THE_MONEY = "atm"


@dataclass
class OptionContract:
    """Represents a single option contract."""
    symbol: str
    strike: float
    expiration: str
    option_type: str  # 'call' or 'put'
    bid: float
    ask: float
    last: float
    volume: int
    open_interest: int
    implied_volatility: float
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None


@dataclass
class FilteredContract:
    """Represents a filtered option contract with metadata."""
    contract: OptionContract
    score: float
    reason: str
    metadata: Dict[str, Any]


class OptionsService:
    """Service for managing options chain data and filtering."""

    def __init__(self):
        """Initialize the options service."""
        self.contracts: List[OptionContract] = []

    def filter_chain(
        self,
        contracts: List[OptionContract],
        filter_type: OptionsChainFilter = OptionsChainFilter.ALL,
    ) -> List[OptionContract]:
        """Filter options chain by type."""
        if filter_type == OptionsChainFilter.ALL:
            return contracts
        elif filter_type == OptionsChainFilter.CALLS:
            return [c for c in contracts if c.option_type.lower() == "call"]
        elif filter_type == OptionsChainFilter.PUTS:
            return [c for c in contracts if c.option_type.lower() == "put"]
        return contracts

    def score_contracts(
        self,
        contracts: List[OptionContract],
    ) -> List[FilteredContract]:
        """Score and filter contracts based on criteria."""
        filtered = []
        for contract in contracts:
            score = self._calculate_score(contract)
            filtered.append(
                FilteredContract(
                    contract=contract,
                    score=score,
                    reason="Scored based on Greeks and volume",
                    metadata={"bid_ask_spread": contract.ask - contract.bid},
                )
            )
        return sorted(filtered, key=lambda x: x.score, reverse=True)

    def _calculate_score(self, contract: OptionContract) -> float:
        """Calculate a score for an option contract."""
        score = 0.0
        if contract.volume > 0:
            score += min(contract.volume / 1000, 10)
        if contract.open_interest > 0:
            score += min(contract.open_interest / 1000, 10)
        if contract.implied_volatility > 0:
            score += contract.implied_volatility * 10
        return score

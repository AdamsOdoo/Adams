"""Small, dependency-free Shopify money contract used by read DTOs."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MoneyDTO:
    """One exact Shopify money side, retained as a JSON-safe decimal string."""

    amount: str | None
    currency_code: str | None

    def __post_init__(self) -> None:
        amount = self.amount
        if amount is not None and (not isinstance(amount, str) or not amount.strip()):
            raise TypeError("money amount must be a non-empty string or None")
        currency = self.currency_code
        if currency is not None and (not isinstance(currency, str) or not currency.strip()):
            raise TypeError("money currency_code must be a non-empty string or None")
        object.__setattr__(self, "amount", amount.strip() if isinstance(amount, str) else amount)
        object.__setattr__(self, "currency_code", currency.strip() if isinstance(currency, str) else currency)
        if self.amount is not None and not re.fullmatch(
            r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", self.amount
        ):
            raise ValueError("money amount must be a decimal string")
        if (self.amount is None) != (self.currency_code is None):
            raise ValueError("money amount and currency_code must be provided together")
        if self.currency_code is not None and not re.fullmatch(r"[A-Z]{3}", self.currency_code):
            raise ValueError("money currency_code must be a three-letter uppercase code")

    def as_dict(self) -> dict[str, str | None]:
        return {"amount": self.amount, "currency_code": self.currency_code}


__all__ = ["MoneyDTO"]

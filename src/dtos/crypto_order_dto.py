from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class CryptoOrderSide(str, Enum):
    """Order side for Coinbase Advanced Trade orders."""

    BUY = "BUY"
    SELL = "SELL"


class MarketIOCConfig(BaseModel):
    """Configuration for a market IOC order.

    Exactly one of `base_size` or `quote_size` must be provided.
    """

    base_size: Optional[Decimal] = Field(
        default=None,
        gt=Decimal("0"),
        description="Amount in base currency to buy/sell.",
    )
    quote_size: Optional[Decimal] = Field(
        default=None,
        gt=Decimal("0"),
        description="Amount in quote currency to spend/receive.",
    )

    @model_validator(mode="after")
    def validate_exactly_one_size(self) -> "MarketIOCConfig":
        provided = [self.base_size is not None, self.quote_size is not None]
        if sum(provided) != 1:
            raise ValueError(
                "Exactly one of 'base_size' or 'quote_size' must be provided."
            )
        return self


class LimitGTCConfig(BaseModel):
    """Configuration for a limit GTC order."""

    base_size: Decimal = Field(gt=Decimal("0"), description="Base currency size.")
    limit_price: Decimal = Field(gt=Decimal("0"), description="Limit price.")
    post_only: bool = Field(
        default=False,
        description=(
            "If true, the order will only make liquidity. "
            "Coinbase may reject if it would take."
        ),
    )


class LimitGTDConfig(BaseModel):
    """Configuration for a limit GTD order (expires at end_time)."""

    base_size: Decimal = Field(gt=Decimal("0"), description="Base currency size.")
    limit_price: Decimal = Field(gt=Decimal("0"), description="Limit price.")
    end_time: datetime = Field(
        description="Expiration time in UTC. Will be serialized as RFC3339.",
    )
    post_only: bool = Field(default=False, description="Post-only flag.")

    @model_validator(mode="after")
    def coerce_timezone(self) -> "LimitGTDConfig":
        if self.end_time.tzinfo is None:
            # Assume naive datetimes are in UTC
            self.end_time = self.end_time.replace(tzinfo=timezone.utc)
        else:
            self.end_time = self.end_time.astimezone(timezone.utc)
        return self


class OrderConfiguration(BaseModel):
    """One-of order configuration for Coinbase Advanced Trade orders.

    Exactly one of the supported configs must be provided.
    """

    market_market_ioc: Optional[MarketIOCConfig] = None
    limit_limit_gtc: Optional[LimitGTCConfig] = None
    limit_limit_gtd: Optional[LimitGTDConfig] = None

    @model_validator(mode="after")
    def validate_one_of(self) -> "OrderConfiguration":
        provided = [
            self.market_market_ioc is not None,
            self.limit_limit_gtc is not None,
            self.limit_limit_gtd is not None,
        ]
        if sum(provided) != 1:
            raise ValueError(
                """Provide exactly one of: market_market_ioc,
                limit_limit_gtc, or limit_limit_gtd."""
            )
        return self


class ExecuteCryptoTradeParams(BaseModel):
    """Parameters for executing a Coinbase Advanced Trade order.

    This schema mirrors the Coinbase Advanced Trade create-order payload while
    enforcing strict typing and validation.
    """

    product_id: str = Field(
        description="Trading pair identifier, e.g., 'BTC-USD'.",
        min_length=3,
    )
    side: CryptoOrderSide = Field(description="Order side: BUY or SELL.")
    order_configuration: OrderConfiguration = Field(
        description="One-of order configuration block.",
    )
    client_order_id: Optional[str] = Field(
        default=None, description="Optional client-supplied unique order id."
    )
    dry_run: bool = Field(
        default=True,
        description=(
            "If true, do not submit the order; return the payload that would be sent."
        ),
    )

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": False,
    }

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class BuyDeliveryOrderParams(BaseModel):
    """Parameters for placing a DELIVERY (CNC) MARKET BUY order.

    Required fields: `tradingsymbol`, `quantity`.
    All other fields have sensible defaults aligned with a CNC market BUY.
    """

    variety: str = Field(
        default="NORMAL",
        description="Order variety; typically 'NORMAL' for standard orders.",
    )
    tradingsymbol: str = Field(
        description="Exchange trading symbol, e.g., 'RELIANCE-EQ'.",
    )
    symboltoken: Optional[str] = Field(
        default=None,
        description=(
            "AngelOne symbol token. If omitted, it will be looked up via searchScrip"
            " using the provided tradingsymbol and exchange."
        ),
    )
    transactiontype: str = Field(
        default="BUY",
        description="Transaction side; for this tool the default is 'BUY'.",
    )
    exchange: str = Field(
        default="NSE",
        description="Exchange on which to place the order (e.g., NSE, BSE).",
    )
    ordertype: str = Field(
        default="MARKET",
        description="Order type; 'MARKET' implies price is ignored/None.",
    )
    producttype: str = Field(
        default="DELIVERY",
        description="Product type; 'DELIVERY' (CNC) for cash-and-carry.",
    )
    duration: str = Field(
        default="DAY",
        description="Order validity duration (e.g., DAY).",
    )
    price: Optional[float] = Field(
        default=None,
        description="Limit price; ignored for MARKET orders (kept as None).",
    )
    squareoff: str = Field(
        default="0",
        description="Square-off value; '0' for non-bracket orders.",
    )
    stoploss: str = Field(
        default="0",
        description="Stop-loss value; '0' when not applicable.",
    )
    quantity: int = Field(
        description="Whole number of shares to buy (>= 1).",
        ge=1,
    )

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
    }

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TransactionType(Enum):
    BUY = "BUY"
    SELL = "SELL"


class Variety(Enum):
    NORMAL = "NORMAL"
    STOPLOSS = "STOPLOSS"
    AMO = "AMO"
    ROBO = "ROBO"


class Exchange(Enum):
    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"
    MCX = "MCX"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOPLOSS_LIMIT = "STOPLOSS_LIMIT"
    STOPLOSS_MARKET = "STOPLOSS_MARKET"


class ProductType(Enum):
    DELIVERY = "DELIVERY"
    INTRADAY = "INTRADAY"
    MARGIN = "MARGIN"
    CARRYFORWARD = "CARRYFORWARD"
    BO = "BO"  # Bracket Order


class Duration(Enum):
    DAY = "DAY"
    IOC = "IOC"  # Immediate or Cancel


class DeliveryTradeParams(BaseModel):
    """Parameters for placing a DELIVERY (CNC) MARKET BUY order.

    Required fields: `tradingsymbol`, `quantity`, `transactiontype`
    All other fields have sensible defaults aligned with a CNC market BUY.
    """

    variety: Variety = Field(
        default=Variety.NORMAL,
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
    transactiontype: TransactionType = Field(
        description="Transaction side; for this tool the default is 'BUY'.",
    )
    exchange: Exchange = Field(
        default=Exchange.NSE,
        description="Exchange on which to place the order (e.g., NSE, BSE).",
    )
    ordertype: OrderType = Field(
        default=OrderType.MARKET,
        description="Order type; 'MARKET' implies price is ignored/None.",
    )
    producttype: ProductType = Field(
        default=ProductType.DELIVERY,
        description="Product type; 'DELIVERY' (CNC) for cash-and-carry.",
    )
    duration: Duration = Field(
        default=Duration.DAY,
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

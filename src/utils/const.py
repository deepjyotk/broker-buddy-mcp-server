from enum import Enum


class AuthHeadersConstants(Enum):
    USER_ID = "x-user-id"
    SCOPES = "x-scopes"


class MCPToolsTags(Enum):
    INDIAN_EXCHANGE = "INDIAN_EXCHANGE"
    ANGELONE_BROKER = "ANGELONE_BROKER"

    CRYPTO_EXCHANGE = "CRYPTO_EXCHANGE"
    COINBASE_BROKER = "COINBASE_BROKER"

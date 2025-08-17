import sys
from typing import Optional

from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class AngelOneSettings(BaseSettings):
    """Loads ANGELONE_* from env/.env"""

    model_config = SettingsConfigDict(
        env_prefix="ANGELONE_",  # <-- IMPORTANT
        env_file=".env",
        env_file_encoding="utf-8",
        # Use case-insensitive matching so typical UPPERCASE env vars work
        case_sensitive=False,
        extra="ignore",  # Ignore unrelated env vars (e.g., ANGELONE_DP_ID)
    )

    history_api_key: str = Field(..., description="Angel One history API key")
    history_secret_key: str = Field(..., description="Angel One history secret key")
    trading_api_key: str = Field(..., description="Angel One trading API key")
    trading_secret_key: str = Field(..., description="Angel One trading secret key")
    totp_secret: str = Field(..., description="Angel One TOTP secret")
    client_code: str = Field(..., description="Angel One client code")
    pin: str = Field(..., description="Angel One PIN")

    # Optional: present for eDIS but not required for core trading session
    dp_id: Optional[str] = Field(
        default=None, description="CDSL/NSDL DP ID for eDIS (optional)"
    )
    bo_id: Optional[str] = Field(
        default=None, description="CDSL/NSDL BO/Client ID for eDIS (optional)"
    )


class CoinbaseSettings(BaseSettings):
    """Loads COINBASE_* from env/.env"""

    model_config = SettingsConfigDict(
        env_prefix="COINBASE_",  # <-- IMPORTANT
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    api_key: str = Field(..., description="Coinbase API key")
    api_secret: str = Field(..., description="Coinbase API secret")


class UserSecret(BaseModel):
    share_credentials_angel_one: Optional[AngelOneSettings] = None
    share_credentials_coinbase: Optional[CoinbaseSettings] = None


def main():
    """Main method to test get_secret."""
    # Normally you'd pass in a real user_id from your system
    user_id = "test-user-123"

    def get_angel_one_secrets(user_id: str) -> UserSecret:
        try:
            settings = AngelOneSettings()  # Reads ANGELONE_* from env/.env
            return UserSecret(share_credentials_angel_one=settings)
        except ValidationError as e:
            missing = [
                err["loc"][0] for err in e.errors() if err["type"].startswith("missing")
            ]
            details = (
                f"Missing: {', '.join(missing)}"
                if missing
                else "Invalid configuration."
            )
            message = f"Angel One credentials not configured correctly. {details}"
            raise ToolError(message)

    def get_coinbase_secrets(user_id: str) -> UserSecret:
        try:
            settings = CoinbaseSettings()  # Reads COINBASE_* from env/.env
            return UserSecret(share_credentials_coinbase=settings)
        except ValidationError as e:
            missing = [
                err["loc"][0] for err in e.errors() if err["type"].startswith("missing")
            ]
            details = (
                f"Missing: {', '.join(missing)}"
                if missing
                else "Invalid configuration."
            )
            message = f"Coinbase credentials not configured correctly. {details}"
            raise ToolError(message)

    try:
        secret = get_angel_one_secrets(user_id)
        secret_coinbase = get_coinbase_secrets(user_id)
        print("✅ Loaded Angel One credentials successfully!")
        print(secret.model_dump())  # Pretty-print loaded credentials
        print("✅ Loaded Coinbase credentials successfully!")
        print(secret_coinbase.model_dump())  # Pretty-print loaded credentials
    except ToolError as te:
        print(f"❌ ToolError [{te.code}]: {te.message}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

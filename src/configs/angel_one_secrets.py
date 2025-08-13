import sys
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from fastmcp.exceptions import ToolError
from pydantic import BaseModel


class AngelOneSettings(BaseSettings):
    """Loads ANGELONE_* from env/.env"""
    model_config = SettingsConfigDict(
        env_prefix="ANGELONE_",     # <-- IMPORTANT
        env_file=".env",
        env_file_encoding="utf-8",
        # Use case-insensitive matching so typical UPPERCASE env vars work
        case_sensitive=False,
    )

    history_api_key: str = Field(..., description="Angel One history API key")
    history_secret_key: str = Field(..., description="Angel One history secret key")
    trading_api_key: str = Field(..., description="Angel One trading API key")
    trading_secret_key: str = Field(..., description="Angel One trading secret key")
    totp_secret: str = Field(..., description="Angel One TOTP secret")
    client_code: str = Field(..., description="Angel One client code")
    pin: str = Field(..., description="Angel One PIN")


class UserSecret(BaseModel):
    share_credentials: AngelOneSettings


def get_secret(user_id: str) -> UserSecret:
    try:
        settings = AngelOneSettings()  # Reads ANGELONE_* from env/.env
        return UserSecret(share_credentials=settings)
    except ValidationError as e:
        missing = [err["loc"][0] for err in e.errors() if err["type"].startswith("missing")]
        details = f"Missing: {', '.join(missing)}" if missing else "Invalid configuration."
        raise ToolError(
            code="invalid_config",
            message=f"Angel One credentials not configured correctly. {details}"
        )


def main():
    """Main method to test get_secret."""
    # Normally you'd pass in a real user_id from your system
    user_id = "test-user-123"
    try:
        secret = get_secret(user_id)
        print("✅ Loaded Angel One credentials successfully!")
        print(secret.model_dump())  # Pretty-print loaded credentials
    except ToolError as te:
        print(f"❌ ToolError [{te.code}]: {te.message}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

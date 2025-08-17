from dotenv import load_dotenv

from configs.angel_one_secrets import AngelOneSettings, CoinbaseSettings, UserSecret

load_dotenv()


def get_angel_one_secrets(user_id: str, scopes: list[str]) -> UserSecret:

    angel_one_secrets = AngelOneSettings()

    return UserSecret(share_credentials_angel_one=angel_one_secrets)


def get_coinbase_secrets(user_id: str, scopes: list[str]) -> UserSecret:
    coinbase_secrets = CoinbaseSettings()

    return UserSecret(share_credentials_coinbase=coinbase_secrets)

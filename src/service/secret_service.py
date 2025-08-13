from dotenv import load_dotenv

from configs.angel_one_secrets import AngelOneSettings, UserSecret

load_dotenv()


def get_secret(user_id: str, scopes: list[str]) -> UserSecret:

    angel_one_secrets = AngelOneSettings()

    return UserSecret(share_credentials=angel_one_secrets)

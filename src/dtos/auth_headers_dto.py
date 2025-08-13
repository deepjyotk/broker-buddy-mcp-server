from pydantic import BaseModel


class AuthHeadersDto(BaseModel):
    user_id: str
    scopes: list[str]

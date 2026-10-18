from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    access_token_minutes: int = 60
    cookie_secure: bool = False  # True behind HTTPS (production)


settings = Settings()

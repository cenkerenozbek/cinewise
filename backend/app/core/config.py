from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MONGO_URI: str = "mongodb://localhost:27017"
    DB_NAME: str = "movie_mrs"
    TMDB_API_KEY: str = ""
    JWT_SECRET: str = "change_me_in_production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24
    CF_THRESHOLD: int = 3
    CF_ALPHA: float = 0.35
    ADMIN_SECRET: str = ""

    model_config = {
        "env_file": "../.env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()

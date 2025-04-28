import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import ClassVar


class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_HOST: str = "postgres"
    DB_PORT: int = 5432

    base_dir: ClassVar[str] = os.path.dirname(os.path.abspath(__file__))
    secrets_dir: ClassVar[str] = os.path.join(base_dir, "secrets")
    DB_HOST: str = "postgres"
    DB_PORT: int = 5432
    
    # model_config = SettingsConfigDict(
    #     env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    # )
    model_config = SettingsConfigDict(env_file=None)
    
    def get_db_url(self):
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


def load_secrets_from_files():
    secrets_path = Settings.secrets_dir
    return dict(
        DB_USER=open(os.path.join(secrets_path, "db_user.secret")).read().strip(),
        DB_PASSWORD=open(os.path.join(secrets_path, "db_password.secret")).read().strip(),
        DB_NAME=open(os.path.join(secrets_path, "db_name.secret")).read().strip(),
    )

        
settings = Settings(**load_secrets_from_files())
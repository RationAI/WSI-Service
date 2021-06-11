from pydantic import BaseSettings


class TestSettings(BaseSettings):
    data_dir: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = "pytest_"

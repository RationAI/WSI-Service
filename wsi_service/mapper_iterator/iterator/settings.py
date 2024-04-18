from pydantic_settings import BaseSettings, SettingsConfigDict

class SettingsIterator(BaseSettings):
    institution_pattern: str = None
    project_pattern: str = None
    source_path: str = "/"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="wsit_"
    )


from pydantic_settings import BaseSettings, SettingsConfigDict



class Settings(BaseSettings):

    MODEL_NAME: str = "gpt-4.1-mini"

    LLM_API_BASE: str = "https://api.openai.com/v1"

    OPENAI_API_KEY: str = ""

    SYSTEM_PROMPT: str = "You are a helpful, concise assistant. If unsure, say you don't know."

    MAX_TURNS: int = 8

    TIMEOUT_S: int = 30

    REDIS_URL: str = "redis://localhost:6379/0"

    EMBED_MODEL: str = "text-embedding-3-small"  # cheap & good; or text-embedding-3-large

    CHROMA_DIR: str = "./vectorstore"

    DATA_DIR: str = "./data"



    # Pydantic v2 config (replaces Config class)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")



settings = Settings()


from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"


class ServerConfig(BaseModel):
    port: int = 8000


class RabbitMqConfig(BaseModel):
    host: str = "localhost"
    port: int = 5672
    user: str = "admin"
    password: str = "admin"
    rag_queue: str = "rag.queue"
    chat_queue: str = "chat.queue"


class MysqlConfig(BaseModel):
    host: str = "localhost"
    port: int = 3306
    user: str = "root"
    password: str = "root123"
    database: str = "FoxChat"

    @property
    def url(self) -> str:
        return f"mysql+aiomysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}?charset=utf8mb4"


class RedisConfig(BaseModel):
    host: str = "localhost"
    port: int = 6379
    user: str = "default"
    password: str = ""
    db: int = 0


class OllamaConfig(BaseModel):
    """Ollama 本地模型配置"""
    base_url: str = "http://localhost:11434"  # 默认本地，无需配置
    embedding_model: str = "bge-small-zh-v1.5"


class ChromaConfig(BaseModel):
    host: str = "localhost"
    port: int = 18000


class ModelApiKey(BaseModel):
    ds_model: str = ""
    kimi_model: str = ""
    qwen_model: str = ""
    minimax_model: str = ""
    claude_model: str = ""
    glm_model: str = ""
    astron_model: str = ""


class ModelConfig(BaseModel):
    default_llm: str = "astron_model"
    default_json_llm: str = "astron_json_model"
    default_embedding: str = "dashscope"
    emotion_llm: str = "astron_json_model"


class ModelByScenario(BaseModel):
    chat_llm: str = "default"
    chat_json_llm: str = "default_json"
    memory_llm: str = "default"
    memory_json_llm: str = "astron_json_model"
    summary_llm: str = "default"
    extraction_llm: str = "astron_json_model"


class LangSmithConfig(BaseModel):
    tracing_enabled: bool = False
    api_key: str = ""
    project: str = "fox-chat-rag"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__",
    )

    rabbitmq: RabbitMqConfig = RabbitMqConfig()
    mysql: MysqlConfig = MysqlConfig()
    server: ServerConfig = ServerConfig()
    redis: RedisConfig = RedisConfig()
    chroma: ChromaConfig = ChromaConfig()
    ollama: OllamaConfig = OllamaConfig()
    key: ModelApiKey = ModelApiKey()
    model: ModelConfig = ModelConfig()
    model_by_scenario: ModelByScenario = ModelByScenario()
    langsmith: LangSmithConfig = LangSmithConfig()


global_settings = Settings()

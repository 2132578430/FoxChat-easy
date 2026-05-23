from sqlalchemy import VARCHAR, Column, DECIMAL, INT, TIMESTAMP, BOOLEAN
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class LlmConfig(Base):
    __tablename__ = "llm_config"

    id = Column(VARCHAR(64), primary_key=True)
    llm_id = Column(VARCHAR(64), nullable=False)
    scenario = Column(VARCHAR(32), nullable=False)
    model_name = Column(VARCHAR(64), nullable=False)
    model_api_key = Column(VARCHAR(255), nullable=False)
    model_base_url = Column(VARCHAR(255), nullable=False)
    model_temperature = Column(DECIMAL(3, 2), nullable=True)
    model_max_tokens = Column(INT, nullable=True)
    model_response_format = Column(VARCHAR(64), nullable=True)
    is_default = Column(BOOLEAN, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
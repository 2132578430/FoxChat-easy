from sqlalchemy import VARCHAR, Column
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class LlmUser(Base):
    __tablename__ = "llm_user"
    id = Column(VARCHAR, primary_key=True)
    user_id = Column(VARCHAR)
    llm_name = Column(VARCHAR)
    face_image = Column(VARCHAR)
    memory_content = Column(VARCHAR)

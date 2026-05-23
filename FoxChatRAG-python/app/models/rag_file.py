from sqlalchemy import Column, VARCHAR, DATE
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class RagFile(Base):
    __tablename__ = 'rag_file'
    id = Column(VARCHAR, primary_key=True)
    file_name = Column(VARCHAR)
    file_path = Column(VARCHAR)
    user_id = Column(VARCHAR)
    status = Column(TINYINT)
    create_time = Column(DATE)

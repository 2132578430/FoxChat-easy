import chromadb
from langchain_chroma import Chroma

from app.common.constant import ChromaTypeConstant
from app.core.llm_model import model
from app.core.settings import global_settings

# 远程 Chroma 客户端
chroma_client = chromadb.HttpClient(
    host=global_settings.chroma.host,
    port=global_settings.chroma.port,
)

rag_chroma = Chroma(
    collection_name="rag_collection",
    embedding_function=model.chroma_model,
    client=chroma_client,
)

chat_chroma = Chroma(
    collection_name="chat_collection",
    embedding_function=model.chroma_model,
    client=chroma_client,
)

CHROMA_MAP = {
    ChromaTypeConstant.RAG: rag_chroma,
    ChromaTypeConstant.CHAT: chat_chroma,
}
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


def ensure_collection_dimensions():
    """
    启动时校验 ChromaDB 集合维度是否与当前 embedding 模型匹配。
    不匹配则删除重建（切换 embedding 模型时自动迁移）。
    """
    import numpy as np
    from loguru import logger

    # 用一条短文本测出当前模型输出维度
    test_embedding = model.chroma_model.embed_query("test")
    expected_dim = len(test_embedding)

    for name, chroma in [("rag_collection", rag_chroma), ("chat_collection", chat_chroma)]:
        try:
            count = chroma._collection.count()
            if count == 0:
                continue  # 空集合，无所谓维度
            # 取第一条记录的 embedding 比对维度
            sample = chroma._collection.get(limit=1, include=["embeddings"])
            if sample and sample.get("embeddings") and sample["embeddings"][0]:
                actual_dim = len(sample["embeddings"][0])
                if actual_dim != expected_dim:
                    logger.warning(
                        f"[ChromaDB] {name} 维度不匹配: 现有={actual_dim}, 期望={expected_dim}，重建集合"
                    )
                    chroma.delete_collection()
                    # 用当前 embedding_function 重建集合（刷新 _collection 引用）
                    chroma._collection = chroma_client.get_or_create_collection(
                        name=name,
                        embedding_function=model.chroma_model,
                    )
                    logger.info(f"[ChromaDB] {name} 集合已重建（{actual_dim}→{expected_dim}维）")
        except Exception as e:
            logger.warning(f"[ChromaDB] {name} 维度校验跳过: {e}")
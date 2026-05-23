import jieba
from langchain_chroma import Chroma
from langchain_classic.retrievers import EnsembleRetriever, ContextualCompressionRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

def chinese_tokenizer(text: str) -> list[str]:
    return list(jieba.cut(text))

def get_bm25_retriever(documents: list[Document]) -> BM25Retriever:
    # bm25分词器
    bm25_retriever = BM25Retriever.from_documents(
        documents=documents,
    )

    # bm25中文分词方法指定
    bm25_retriever.preprocess_func = chinese_tokenizer

    # bm25分词检索出来的个数
    bm25_retriever.k = 20

    return bm25_retriever

def get_vector_retriever(chroma: Chroma, metadata: dict | None = None):
    vector_retriever = chroma.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": 20,
            "filter": metadata
        }
    )

    return vector_retriever

def search_vector_score(chroma: Chroma, msg: str, metadata: dict | None = None):
    return chroma.similarity_search_with_score(
        query=msg,
        k=20,
        filter={"user_id": metadata.get("user_id")},
    )


def get_ensemble_retriever(documents: list[Document], chroma: Chroma, metadata: dict | None = None) -> EnsembleRetriever:
    bm25 = get_bm25_retriever(documents)
    vector = get_vector_retriever(chroma, metadata)

    ensemble_retriever = EnsembleRetriever(
        retrievers=[bm25, vector],
        weights=[0.4, 0.6]
    )

    return ensemble_retriever

"""
LLM 模型配置模块

职责划分：
- Embed 单例：服务端控制，用于向量化和语义分割
- LLM_MAP + _resolve_model_name：后台任务接口（无用户配置场景）
- 聊天场景：已迁移到策略层 app/service/chat/strategy/

聊天场景迁移说明：
- 所有聊天相关 LLM 调用应使用策略层
- 策略层支持用户自定义模型配置
- 参考：app/service/chat/llm_invoke_service.py
"""

from typing import List

import dashscope
from dashscope import TextEmbedding
from flashrank import Ranker
from langchain_community.document_compressors import FlashrankRerank
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_openai import ChatOpenAI
from loguru import logger
from pydantic import SecretStr

from app.core.settings import global_settings

# ============================================================
# Embed 单例（服务端控制）
# ============================================================

bge_m3_embed = OllamaEmbeddings(
    model="bge-m3",
)

qwen3_embed = OllamaEmbeddings(
    model = "qwen3-embedding:0.6b"
)

class DashScopeEmbeddings:
    """
    自定义向量类--封装阿里云向量模型
    由于封装的向量类都是会自动进行分词器分词，因此需要我们手写一个向量类
    同时，传入的文本和集合可以进行一次清洗然后转化为向量
    本质其实是写一个OpenAiEmbeddings类，来实现我们后面的类需求
    DashScopeEmbeddings是通义封装的类
    """
    def __init__(self):
        self.model_name = "text-embedding-v4"
        dashscope.api_key = global_settings.key.qwen_model

    def _embed_single(self, text: str) -> List[float]:
        clean_text = text.strip()
        if not clean_text:
            return []

        res = TextEmbedding.call(
            model=self.model_name,
            input=clean_text,
        )

        if res.status_code != 200:
            return []

        embeddings = res.output.get("embeddings", [])
        if not embeddings:
            return []

        return embeddings[0].get("embedding", [])

    def embed_documents(self, text: list[str]) -> List[List[float]]:
        clean_list = [t.strip() for t in text if isinstance(t, str) and t.strip()]

        if not clean_list:
            return []

        res = TextEmbedding.call(
            model = self.model_name,
            input=clean_list,
        )

        if res.status_code != 200:
            return []

        embeddings = res.output.get("embeddings", [])
        return [item.get("embedding", []) for item in embeddings]

    def embed_query(self, text: str):
        return self._embed_single(text)

class ChromaModel:
    """
    可配置的向量模型容器

    根据 MODEL__DEFAULT_EMBEDDING 配置选择:
    - dashscope: 阿里云 DashScope API
    - ollama: 本地 Ollama 模型
    """
    def __init__(self):
        embedding_type = global_settings.model.default_embedding

        if embedding_type == "ollama":
            self.embed_model = OllamaEmbeddings(
                model=global_settings.ollama.embedding_model,
                base_url=global_settings.ollama.base_url,
            )
            logger.info(f"【向量模型】使用 Ollama 本地模型: {global_settings.ollama.embedding_model}")
        elif embedding_type == "dashscope":
            self.embed_model = DashScopeEmbeddings()
            logger.info(f"【向量模型】使用 DashScope 云端模型: text-embedding-v4")
        else:
            # 默认回退到 ollama
            self.embed_model = OllamaEmbeddings(
                model=global_settings.ollama.embedding_model,
                base_url=global_settings.ollama.base_url,
            )
            logger.warning(f"【向量模型】未知配置 '{embedding_type}'，回退到 Ollama: {global_settings.ollama.embedding_model}")

    def embed(self, text: str | list):
        if isinstance(text, str):
            return self.embed_model.embed_query(text)
        elif isinstance(text, list):
            return self.embed_model.embed_documents(text)
        else:
            print("文档加载失败，非str与list")
            return []

    def embed_query(self, text: str):
        return self.embed(text)

    def embed_documents(self, text: list):
        return self.embed(text)

chroma_model = ChromaModel()

nomic_embed = OllamaEmbeddings(
    model="nomic-embed-text",
)

rerank_model = FlashrankRerank(model="ms-marco-MiniLM-L-12-v2",
                               top_n=20,
                               client=Ranker(model_name="ms-marco-MiniLM-L-12-v2",
                                             cache_dir="/app/models/flashrank"))

# ============================================================
# 注意：聊天场景已迁移到策略层 app/service/chat/strategy/
# 用户自定义模型配置，不再依赖服务器端 API Key
# ============================================================
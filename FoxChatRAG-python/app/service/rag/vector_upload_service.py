"""
向量上传服务

职责：
- 接收文件上传请求
- 下载文件到本地
- 加载文件内容
- LLM 总结文件内容
- 上传到向量数据库
- 更新数据库状态
"""

import asyncio
import json
import mimetypes
import os

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common import FileTypeConstant
from app.common.constant.ChromaTypeConstant import ChromaTypeConstant
from app.common.constant.LLMChatConstant import LLMChatConstant
from app.core.db.redis_client import redis_client
from app.core.llm_model.model import LLM_MAP, _resolve_model_name
from app.core.net import download_file
from app.models.rag_file import RagFile
from app.util import loader_util, chroma_util


async def _update_file_status(file_path: str, db: AsyncSession):
    """
    修改数据库文件状态为向量成功
    """
    sql = select(RagFile).where(RagFile.file_path == file_path)

    result = await db.execute(sql)

    rag_file = result.scalars().first()

    rag_file.status = 2

    await db.commit()


async def _summary_file_content(documents: list[Document]) -> dict:
    str_parser = StrOutputParser()
    upload_str = "\n\n".join([doc.page_content for doc in documents])

    template = ChatPromptTemplate(
        [
            ("system", "你是文档分析助手。请用JSON格式输出，不要有任何多余的字段，包含：summary（简要总结，200字内）、keywords（1-5个关键词）"),
            ("user", f"用户发送信息为：{upload_str}")
        ]
    )

    # 使用配置的 default_json 模型
    model_name = _resolve_model_name("default_json")
    llm = LLM_MAP.get(model_name)
    chain = template | llm | str_parser

    res = chain.invoke(input={"upload_str": upload_str})

    return json.loads(res)


async def upload_file(body, db: AsyncSession):
    """
    rag文件上传处理逻辑
    :return:
    """
    body = body.decode('utf-8')

    data_json: dict = json.loads(body)

    file_json: dict = data_json.get("data")

    file_path = file_json.get("filePath")
    user_id = file_json.get("userId")

    file_type, _ = mimetypes.guess_type(file_path)

    if file_path:
        try:
            # 将文件从网络加载到本地
            local_file_path = await download_file(file_path)
            logger.info("下载文件完成:" + local_file_path)

            # 利用加载器加载成documents
            documents: list[Document] = await asyncio.to_thread(
                loader_util.load_file,
                local_file_path,
                FileTypeConstant(file_type)
            )
            logger.info("加载文件完成")

            # 将Document传入llm总结
            summary_json = await _summary_file_content(documents)

            summary = summary_json.get("summary")
            keywords = summary_json.get("keywords")

            upload_document = Document(
                page_content=f"关键词：{keywords}\n内容摘要:{summary}",
                metadata={
                    "user_id": user_id,
                    "file_path": file_path,
                    "keywords": keywords,
                    "file_type": file_type,
                }
            )

            # 上传到向量库
            await chroma_util.upload(
                ChromaTypeConstant.RAG,
                [upload_document],
                file_path,
            )

            # 修改数据库状态
            await _update_file_status(file_path, db)
            logger.info("向量化文件完成:" + file_path)

        finally:
            # 清除文件
            if os.path.exists(local_file_path):
                os.remove(local_file_path)
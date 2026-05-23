"""
RAG 文件检索服务

职责：
- 根据用户消息检索相关文件
- 向量相似度搜索
- 文件路径归纳
"""

import os
from collections import defaultdict
from langchain_core.documents import Document

from app.retriever import project_retriever
from app.chroma import rag_chroma
from app.schemas.M import M
from app.schemas.rag_search_file_msg import RagSearchFileMsg


def search_file(msg: M[RagSearchFileMsg]):
    """
    文件搜索主逻辑
    :param msg:
    :return:
    """
    search_data: RagSearchFileMsg = msg.data
    search_msg = search_data.msg
    user_id = search_data.userId

    # 向量数据库操作件
    docs_with_scores = project_retriever.search_vector_score(
        rag_chroma,
        search_msg,
        {"user_id": user_id}
    )

    # 文件路径归纳
    file_path_group = file_group_path(docs_with_scores)

    return file_path_group


def file_group_path(docs_with_scores: list[tuple[Document, float]]):
    """
    文档路径归纳
    :param docs_with_scores: 文档及其相似度分数的列表
    :return:
    """
    file_group = defaultdict(list)
    file_max_score = defaultdict(float)
    file_group_names = {}

    for doc, score in docs_with_scores:
        file_path = doc.metadata.get("file_path")
        file_name = doc.metadata.get("file_name", os.path.basename(file_path))

        file_group[file_path].append(doc.page_content)
        file_group_names[file_path] = file_name

        if score > file_max_score[file_path]:
            file_max_score[file_path] = score

    file_group_arr = []

    for file_path, page_content in file_group.items():
        file_group_arr.append(
            {
                "filePath": file_path,
                "fileName": file_group_names[file_path],
                "score": file_max_score[file_path],
            }
        )

    file_group_arr.sort(key=lambda x: x["score"], reverse=False)

    return file_group_arr
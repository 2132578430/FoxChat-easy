"""
文件加载器(loader_util)

负责将整个文件路径加载成一个List[Document]
- 操作核心函数load_file(local_file_path: str, file_type: FileTypeConstant)

该文件全部为非异步，加载文件为CPU/IO密集型任务，因此不适合使用异步
调用时请使用asyncio.to_thread调用
"""

from typing import List

from langchain_community.document_loaders import UnstructuredWordDocumentLoader, TextLoader, CSVLoader, PyPDFLoader, \
    UnstructuredMarkdownLoader, PyMuPDFLoader
from langchain_core.documents import Document

from app.common import FileTypeConstant


def txt_loader(file_path: str):
    loader = TextLoader(
        file_path,
        encoding="utf-8",
    )

    documents = loader.load()

    return documents

def csv_loader(file_path: str):
    loader = CSVLoader(
        file_path,
        encoding="utf-8",
    )

    documents = loader.load()

    return documents

def pdf_loader(file_path: str):
    loader = PyMuPDFLoader(
        file_path = file_path,
        encodings = "utf-8",
    )

    documents = loader.load()

    return documents

def docx_loader(file_path: str):
    loader = UnstructuredWordDocumentLoader(
        file_path,
        mode="elements",
    )

    documents = loader.load()

    return documents

def md_loader(file_path: str):
    loader = UnstructuredMarkdownLoader(
        file_path=file_path,
        mode="elements",
        strategy="fast",
    )

    documents = loader.load()

    return documents

def _enhance_metadata(documents: List[Document]):
    """
    对md文档metadata加入标题
    """
    current_header = ["", "", ""]

    for doc in documents:
        meta = doc.metadata

        if _is_title_element(category=meta.get("category")):
            depth = _get_title_depth(category=meta.get("category").lower(), metadata=meta)
            title = doc.page_content

            for i in range(depth, 3):
                current_header[i] = ""
            current_header[depth - 1] = title

        doc.metadata["header1"] = current_header[0]
        doc.metadata["header2"] = current_header[1]
        doc.metadata["header3"] = current_header[2]

    return documents

def _is_title_element(category: str) -> bool:
    """
    判断是否是标题
    """
    title = {"title", "heading", "heading1", "heading2", "heading3", "sectionheader"}

    return category in title

def _get_title_depth(category: str, metadata: dict) -> int:
    """
    获取标题对应的数字
    """
    level = metadata.get("level", 0)
    if level:
        return level

    import re
    match = re.search(r"(\d+)", category)
    if match:
        return min(int(match.group()), 3)
    return 1

def str_loader(content: str):
    documents:list = [Document(page_content=content)]

    return documents

# 文件类型对应文件加载器
LOADER_MAP = {
        FileTypeConstant.CSV: csv_loader,
        FileTypeConstant.TXT: txt_loader,
        FileTypeConstant.DOCX: docx_loader,
        FileTypeConstant.PDF: pdf_loader,
        FileTypeConstant.MD: md_loader,
        FileTypeConstant.STR: str_loader,
}

def load_file(local_file_path: str, file_type: FileTypeConstant) -> list[Document]:
    """
    根据文件类型进行加载
    """
    loader = LOADER_MAP[file_type]

    # 文档利用加载器加载,并进行粗划分
    documents: List[Document] = loader(local_file_path)

    return documents
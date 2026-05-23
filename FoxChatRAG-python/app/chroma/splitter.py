from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.llm_model import model

easy_txt_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ".", " ", "!", "，", "。", "！", ""],    # 需要换段落的分隔符号
        chunk_size=1000,     # 分段的最大字符数
        chunk_overlap=100,       # 分段之后允许的最大重叠字符数（为了保证上下文连贯）
        length_function=len,        # 统计字符的依赖函数
    )

semantic_txt_splitter = SemanticChunker(
    embeddings=model.nomic_embed,
    sentence_split_regex=r"(?<=[。！？])",  # 按中文句子结束符分割
    # 最小分段字符数
    min_chunk_size=50,
    breakpoint_threshold_type="percentile",
    breakpoint_threshold_amount=90,
)
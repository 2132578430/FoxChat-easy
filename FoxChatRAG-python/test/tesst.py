import requests
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.core import llm_model


def main():
    ds_model = ChatOpenAI(
        model="deepseek-reasoner",
        api_key= SecretStr("sk-fd578da1a6084663b15bbde5c57b2d20"),
        base_url="https://api.deepseek.com"
    )

    ds_model.invoke("你好")
    return

if __name__ == '__main__':
    main()
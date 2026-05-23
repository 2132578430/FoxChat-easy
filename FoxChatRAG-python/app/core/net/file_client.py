import tempfile

import requests

async def download_file(file_path: str) -> str:
    """
    下载临时文件，返回临时文件路径
    """
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        response = requests.get(file_path, stream=True)

        tmp_file.write(response.content)

        local_file_path = tmp_file.name

        return local_file_path
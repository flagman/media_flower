import os
import aiofiles
import asyncio
from app.core.abstract_storage_service import StorageService


class LocalFilesystemStorageService(StorageService):
    def __init__(self):
        self.base_path = "local_storage"

    async def upload(
        self, bucket: str, key: str, data: bytes, content_type: str = None
    ):
        local_path = os.path.join(self.base_path, bucket, key)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        async with aiofiles.open(local_path, "wb") as f:
            await f.write(data)

    async def download(self, bucket: str, key: str) -> bytes:
        local_path = os.path.join(self.base_path, bucket, key)
        async with aiofiles.open(local_path, "rb") as f:
            return await f.read()

    async def delete(self, bucket: str, key: str):
        local_path = os.path.join(self.base_path, bucket, key)
        if os.path.exists(local_path):
            os.remove(local_path)

    async def cleanup(self, bucket: str, path: str, variants: list):
        delete_tasks = [
            self.delete(bucket, f"{path}/{variant.name}")
            for variant in variants
        ]
        await asyncio.gather(*delete_tasks)

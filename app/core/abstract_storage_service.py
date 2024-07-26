from abc import ABC, abstractmethod


class StorageService(ABC):
    @abstractmethod
    async def upload(
        self, bucket: str, key: str, data: bytes, content_type: str = None
    ):
        pass

    @abstractmethod
    async def download(self, bucket: str, key: str) -> bytes:
        pass

    @abstractmethod
    async def delete(self, bucket: str, key: str):
        pass

    @abstractmethod
    async def cleanup(self, bucket: str, path: str, variants: list):
        pass

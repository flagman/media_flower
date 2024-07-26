import random
import string
from nanoid import generate
from app.core.storage_factory import get_storage_service
from app.models.data_models import ImageVariant
from typing import List
from app.helpers.file_utils import content_type_from_extension

storage_service = get_storage_service()


def _generate_unique_nanoid(size=16):
    return generate(size=size)


def _generate_random_folder_name():
    return "".join(random.choice(string.ascii_lowercase) for _ in range(2))


async def upload_to_s3(
    bucket: str,
    image_type: str,
    extension: str,
    data: bytes,
    path_hierarchy: List = [],
):
    folder_name = _generate_random_folder_name()
    nanoid = _generate_unique_nanoid()

    if path_hierarchy:
        key = f"{folder_name}/{image_type}/{'/'.join(path_hierarchy)}/{nanoid}.{extension}"  # noqa
    else:
        key = f"{folder_name}/{image_type}/{nanoid}.{extension}"
    content_type = content_type_from_extension(extension)
    await storage_service.upload(bucket, key, data, content_type)
    return key


async def download_image_from_s3(bucket: str, key: str) -> bytes:
    return await storage_service.download(bucket, key)


async def cleanup_s3_uploads(
    bucket: str, path: str, variants: list[ImageVariant]
):
    await storage_service.cleanup(bucket, path, variants)


async def delete_object_safe(bucket: str, key: str):
    await storage_service.delete(bucket, key)

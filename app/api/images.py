from fastapi import APIRouter, Query, Depends

from typing import Optional
from app.core.db_init import db
from app.models.image_metadata import ImageMetadata
from app.api.auth import authorize

router = APIRouter()


@router.get(
    "/images",
    summary="Get Images",
    description="Retrieve a list of images with optional filtering by project name and image name.",
    response_description="A list of images with pagination details.",
)
async def get_images(
    project_name: Optional[str] = None,
    image_name: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    _: str = Depends(authorize),
):
    query = {}
    if project_name:
        query["project_name"] = project_name
    if image_name:
        query["image_name"] = image_name

    skip = (page - 1) * limit
    cursor = db.images.find(query).skip(skip).limit(limit)
    total_count = await db.images.count_documents(query)
    images = await cursor.to_list(length=limit)
    images = [ImageMetadata(**image) for image in images]
    return {
        "page": page,
        "limit": limit,
        "total_count": total_count,
        "images": images,
    }

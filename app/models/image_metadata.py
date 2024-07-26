from app.models.py_object import PyObjectId
from pydantic import BaseModel
from typing import Dict
from pydantic import Field as PydanticField


class Asset(BaseModel):
    url: str
    width: int
    height: int
    size: int
    format: str


class ImageMetadata(BaseModel):
    id: PyObjectId = PydanticField(default_factory=PyObjectId, alias="_id")
    version: int
    project_name: str
    image_name: str
    source: Asset
    variants: Dict[str, Asset]

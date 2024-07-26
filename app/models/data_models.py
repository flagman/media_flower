from pydantic import BaseModel, Field
from typing import List, Optional


class ImageVariant(BaseModel):
    name: str
    path: str
    imgproxy_params: str
    format: Optional[str] = Field(default="webp")


class Image(BaseModel):
    name: str
    path: str
    image_variants: List[ImageVariant]


class Manifest(BaseModel):
    version: int
    name: str
    source_bucket: str
    derived_bucket: str
    images: List[Image]

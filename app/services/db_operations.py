from app.core.db_init import db
from app.models.data_models import Image


# Save image metadata
async def save_image_metadata(metadata: Image):
    await db.images.insert_one(metadata.model_dump())

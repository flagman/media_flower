from app.services.imgproxy_service import ImgproxyService
from app.services.s3_operations import (
    upload_to_s3,
    cleanup_s3_uploads,
    delete_object_safe,
)
from app.services.db_operations import save_image_metadata
from app.models.image_metadata import ImageMetadata, Asset
from app.core.manifest_loader import manifests
from fastapi import HTTPException
from app.helpers.file_utils import (
    detect_extension_from_bytes,
    detect_dims_from_bytes,
)
import asyncio


async def handle_image_processing(
    project_name: str, image_type: str, src_data: bytes
):
    if project_name not in manifests:
        raise HTTPException(status_code=404, detail="Project not found")
    project_manifest = manifests[project_name]
    image_info = next(
        image for image in project_manifest.images if image.name == image_type
    )

    src_extension = detect_extension_from_bytes(src_data)
    src_size = detect_dims_from_bytes(src_data)

    imgproxy_service = ImgproxyService(image_info, src_data)

    try:
        await imgproxy_service.save_image_to_filesystem(src_data)

        processed_variants = await imgproxy_service.create_variants()

        variant_dims = [
            detect_dims_from_bytes(data) for data in processed_variants
        ]

        source_key = await upload_to_s3(
            project_manifest.source_bucket, image_type, src_extension, src_data
        )

        variant_keys = await upload_variants_to_s3(
            project_manifest.derived_bucket,
            image_type,
            image_info.image_variants,
            processed_variants,
        )

        metadata = ImageMetadata(
            version=project_manifest.version,
            project_name=project_name,
            image_name=image_type,
            source=Asset(
                url=f"s3://{project_manifest.source_bucket}/{source_key}",
                width=src_size[0],
                height=src_size[1],
                size=len(src_data),
                format=src_extension,
            ),
            source_url=f"s3://{project_manifest.source_bucket}/{source_key}",
            variants={
                variant.name: Asset(
                    url=f"s3://{project_manifest.derived_bucket}/{key}",
                    width=dims[0],
                    height=dims[1],
                    size=len(data),
                    format=variant.format,
                )
                for variant, key, data, dims in zip(
                    image_info.image_variants,
                    variant_keys,
                    processed_variants,
                    variant_dims,
                )
            },
        )
        await save_image_metadata(metadata)

        return metadata
    except Exception as e:
        # Cleanup S3 uploads
        await cleanup_s3_uploads(
            project_manifest.derived_bucket,
            image_info.path,
            image_info.image_variants,
        )

        # Cleanup source image from S3
        source_key = f"{image_info.path}/{image_type}"
        await delete_object_safe(project_manifest.source_bucket, source_key)

        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Ensure filesystem cleanup
        await imgproxy_service.cleanup()


async def upload_variants_to_s3(
    bucket: str, image_type: str, variants, data_list
):

    upload_tasks = [
        upload_to_s3(
            bucket=bucket,
            image_type=image_type,
            extension=variant.format,
            data=data,
            path_hierarchy=[variant.name],
        )
        for variant, data in zip(variants, data_list)
    ]
    return await asyncio.gather(*upload_tasks)

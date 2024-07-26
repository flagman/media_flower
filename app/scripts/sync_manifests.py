import asyncio
from pymongo import UpdateOne
from app.services.s3_operations import (
    delete_object_safe,
    upload_to_s3,
    download_image_from_s3,
)
from app.core.manifest_loader import load_all_manifests
from app.core.db_init import db
from app.services.imgproxy_service import ImgproxyService
from app.models.data_models import Image, Manifest
from app.models.image_metadata import ImageMetadata, Asset
from app.helpers.file_utils import detect_dims_from_bytes
from typing import List


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


async def get_images_needing_update(
    project_name: str, current_version: int
) -> List[ImageMetadata]:
    filter_query = {
        "project_name": project_name,
        "version": {"$lt": current_version},
    }
    images = []
    async for image_metadata in db.images.find(filter_query):
        images.append(ImageMetadata(**image_metadata))
    return images


# Create new variants and delete old ones
async def update_image_variants(
    project_manifest: Manifest,
    image_info: Image,
    existing_metadata: ImageMetadata,
):

    existing_variant_names = set(existing_metadata.variants.keys())
    new_variant_names = set(
        variant.name for variant in image_info.image_variants
    )

    variants_to_delete = existing_variant_names - new_variant_names
    variants_to_add = new_variant_names - existing_variant_names

    new_variants = {}
    # Delete old variants from S3
    for variant_name in variants_to_delete:
        variant_url = existing_metadata.variants[variant_name].url
        variant_key = variant_url.replace(
            f"s3://{project_manifest.derived_bucket}/", ""
        )
        await delete_object_safe(project_manifest.derived_bucket, variant_key)
        print(f"Deleted variant: {variant_name}")

    if not variants_to_add:
        return {
            name: asset
            for name, asset in existing_metadata.variants.items()
            if name not in variants_to_delete
        }

    # Download source image from S3
    source_key = existing_metadata.source.url.replace(
        f"s3://{project_manifest.source_bucket}/", ""
    )
    source_data = await download_image_from_s3(
        project_manifest.source_bucket, source_key
    )

    # Initialize ImgproxyService
    imgproxy_service = ImgproxyService(image_info, source_data)
    await imgproxy_service.save_image_to_filesystem(source_data)

    # Create new variants
    processed_variants = await imgproxy_service.create_variants()

    # Upload new variants to S3
    variant_keys = await upload_variants_to_s3(
        project_manifest.derived_bucket,
        image_info.name,
        image_info.image_variants,
        processed_variants,
    )

    # Prepare new variants metadata
    new_variants.update(
        {
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
                [detect_dims_from_bytes(data) for data in processed_variants],
            )
            if variant.name in variants_to_add
        }
    )

    # Include unchanged variants from existing metadata
    new_variants.update(
        {
            name: asset
            for name, asset in existing_metadata.variants.items()
            if name not in variants_to_delete
        }
    )

    return new_variants


# Update ImageMetadata with new manifest version and new variants
async def update_image_metadata(project_name: str, project_manifest: Manifest):
    manifest_version = project_manifest.version

    images_to_update = await get_images_needing_update(
        project_name, manifest_version
    )

    update_requests = []
    for image_metadata in images_to_update:

        image_type = image_metadata.image_name
        image_info = next(
            (
                image
                for image in project_manifest.images
                if image.name == image_type
            ),
            None,
        )

        if not image_info:
            continue

        new_variants = await update_image_variants(
            project_manifest, image_info, image_metadata
        )

        new_variants = {
            name: asset.model_dump() for name, asset in new_variants.items()
        }

        update_requests.append(
            UpdateOne(
                {"_id": image_metadata.id},
                {
                    "$set": {
                        "version": manifest_version,
                        "variants": new_variants,
                    }
                },
            )
        )
    if update_requests:
        result = await db.images.bulk_write(update_requests)
        print(
            f"Updated {result.modified_count} documents for project '{project_name}'."  # noqa
        )


async def main():
    manifest_directory = "./manifests"  # Replace with your manifests directory
    all_manifests = load_all_manifests(manifest_directory)

    for project_name, versions in all_manifests.items():
        versions.sort(key=lambda x: x["version"])
        if len(versions) < 2:
            continue

        for version in versions[1:]:
            project_manifest = Manifest(**version["manifest"])
            print(
                f"Updating project '{project_name}' to version {version['version']}'"  # noqa
            )
            await update_image_metadata(project_name, project_manifest)


if __name__ == "__main__":
    asyncio.run(main())

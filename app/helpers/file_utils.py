import filetype
from PIL import Image
from io import BytesIO
import xml.etree.ElementTree as ET


def detect_extension_from_bytes(byte_data):
    if is_svg(byte_data):
        return "svg"
    fileinfo = filetype.guess(byte_data)
    if fileinfo is None:
        raise ValueError("Cannot determine file type")

    return fileinfo.extension


def detect_dims_from_bytes(byte_data):
    if is_svg(byte_data):
        return svg_dims(byte_data)

    with Image.open(BytesIO(byte_data)) as image:
        return image.size


def is_svg(byte_data):
    return "<svg" in str(byte_data[0:100])


def svg_dims(byte_data):

    try:
        svg_string = byte_data.decode("utf-8")
        root = ET.fromstring(svg_string)

        width = root.attrib.get("width")
        height = root.attrib.get("height")

        width = int(round(float(width))) if width is not None else None
        height = int(round(float(height))) if height is not None else None

        return width, height
    except (ET.ParseError, ValueError) as e:
        # Handle parsing errors or invalid float conversion
        raise ValueError("Invalid SVG byte data or attributes.") from e


def content_type_from_extension(extension):
    if extension == "svg":
        return "image/svg+xml"
    return f"image/{extension}"

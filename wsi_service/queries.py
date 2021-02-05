from fastapi import Query

ImageFormatsQuery = Query(
    "jpeg", description="Image format (e.g. bmp, gif, jpeg, png, tiff). For raw image data choose tiff."
)

ImageQualityQuery = Query(
    90,
    ge=0,
    le=100,
    description="Image quality (Only for specific formats. For Jpeg files compression is always lossy. For tiff files 'deflate' compression is used by default. Set to 0 to compress lossy with 'jpeg')",
)

ImageChannelQuery = Query(None, description="List of requested image channels. By default all channels are returned.")

ZStackQuery = Query(0, description="Z-Stack layer index z")

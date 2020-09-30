from fastapi import Query

ImageFormatsQuery = Query(
    "jpeg", description="Image format (e.g. bmp, gif, jpeg, png, tiff)"
)

ImageQualityQuery = Query(
    90, ge=0, le=100, description="Image quality (only considered for specific formats)"
)

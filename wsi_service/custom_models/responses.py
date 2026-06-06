ImageResponses = {
    200: {
        "content": {
            "image/*": {},
            "application/octet-stream": {},
            "application/json": {},
            "application/geo+json": {},
            "application/vnd.mapbox-vector-tile": {},
        }
    }
}

ImageRegionResponse = {200: {"content": dict(ImageResponses[200]["content"])}}
ImageRegionResponse[413] = {"detail": "Requested region is too large"}

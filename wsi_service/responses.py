ImageResponses = {
    200: {
        "content": {"image/*": {}}
    }
}

ImageRegionResponse = ImageResponses
ImageRegionResponse[413] = {
    'detail': 'Requested region is too large'
}
ImageResponses = {
    200: {
        "content": {"image/*": {}}
    },
    404: {
        'detail': 'Invalid global_slide_id'
    }
}

ImageRegionResponse = ImageResponses
ImageRegionResponse[413] = {
    'detail': 'Requested region is too large'
}
from fastapi import Query


SlideListQuery = Query(
    ...,
    alias="slides",
    example="b10648a7-340d-43fc-a2d9-4d91cc86f33f,b10648a7-340d-43fc-a2d9-4d91cc86f33f",
    description="""Provide slide list to access simultaneously via batch queries.""",
)

TileXListQuery = Query(
    ...,
    example="8,6,45,0",
    description="""Provide x-coord list to access tiles at. The size must match the number of files requested.""",
)
TileYListQuery = Query(
    ...,
    example="1,58,6,2",
    description="""Provide y-coord list to access tiles at. The size must match the number of files requested.""",
)
TileLevelListQuery = Query(
    ...,
    example="0,5,1,2",
    description="""Provide level list to access tiles at. The size must match the number of files requested.""",
)

from fastapi import Query


FileListQuery = Query(
    "",
    example="path/to/file1.ext,path/to/another/scan.ext2",
    description="""Provide file list to access simultanously via batch queries.""",
)

TileXListQuery = Query(
    None,
    example="8,6,45,0",
    description="""Provide x-coord list to access tiles at. The size must match the number of files requested.""",
)
TileYListQuery = Query(
    None,
    example="1,58,6,2",
    description="""Provide y-coord list to access tiles at. The size must match the number of files requested.""",
)
TileLevelListQuery = Query(
    None,
    example="0,5,1,2",
    description="""Provide level list to access tiles at. The size must match the number of files requested.""",
)

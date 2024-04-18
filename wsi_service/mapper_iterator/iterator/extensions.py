class Extensions:
    @staticmethod
    def get_allowed_extensions():
        return [
            ".bif",
            ".dcm",
            ".isyntax",
            ".mrxs",
            ".ndpi",
            ".ome.btf",
            ".ome.tf2",
            ".ome.tf8",
            ".ome.tif",
            ".ome.tiff",
            ".scn",
            ".svs",
            ".tif",
            ".tiff",
            ".vsf",
            ".img",
            ".jpg",
        ]

    @staticmethod
    def get_multi_extensions():
        return [".mrxs", ".dcm", ".vsf", ".img", ".jpg"]

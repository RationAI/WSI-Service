import gzip
import json
import re
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from fastapi import HTTPException

from wsi_service.models.v3.slide import SlideExtent, SlideInfo, SlideLevel, SlidePixelSizeNm
from wsi_service.slide import Slide as BaseSlide

SUPPORTED_TILE_SUFFIXES = (
    ".mvt",
    ".pbf",
    ".json",
    ".geojson",
    ".mvt.gz",
    ".pbf.gz",
    ".json.gz",
    ".geojson.gz",
)
MANIFEST_HINT_KEYS = {
    "root",
    "tile_root",
    "tile_size",
    "max_zoom",
    "min_zoom",
    "tile_suffix",
    "tile_suffixes",
    "scheme",
    "zoom_levels",
    "levels",
    "bounds_by_zoom",
    "tiles",
}
_TILE_Y_RE = re.compile(r"^(?P<y>\d+)(?:\.(?:mvt|pbf|json|geojson))?(?:\.gz)?$")


class Slide(BaseSlide):
    async def open(self, filepath):
        self.source = Path(filepath)
        self.tile_size = 256
        self.scheme = "xyz"
        self.root: Optional[Path] = None
        self._single_tile_bytes: Optional[bytes] = None
        self._single_tile_suffix: Optional[str] = None
        self._mbtiles_conn: Optional[sqlite3.Connection] = None
        self._mbtiles_metadata: Dict[str, str] = {}
        self._tile_suffixes = list(SUPPORTED_TILE_SUFFIXES)
        self._zoom_ranges: Dict[int, Dict[str, int]] = {}
        self._level_to_zoom: List[int] = []

        if self.source.is_dir():
            self.root = self.source.resolve()
            self._open_directory_dataset()
        elif self._matches_suffix(self.source.name, ".mbtiles"):
            self._open_mbtiles_dataset()
        else:
            self._open_file_dataset()

        self._build_slide_info()

    async def close(self):
        if self._mbtiles_conn is not None:
            self._mbtiles_conn.close()
            self._mbtiles_conn = None

    async def get_info(self):
        return self.slide_info

    async def get_thumbnail(self, max_x, max_y, icc_profile_intent=None, icc_profile_strict=False):
        raise HTTPException(status_code=501, detail="Thumbnail is not supported for vector tile datasets.")

    async def get_label(self):
        raise HTTPException(status_code=404, detail="Associated image label does not exist.")

    async def get_macro(self, icc_profile_intent=None, icc_profile_strict=False):
        raise HTTPException(status_code=404, detail="Associated image macro does not exist.")

    async def get_region(
        self,
        level,
        start_x,
        start_y,
        size_x,
        size_y,
        padding_color=None,
        z=0,
        icc_profile_intent=None,
        icc_profile_strict=False,
    ):
        raise HTTPException(status_code=501, detail="Region access is not supported for vector tile datasets.")

    async def get_tile(self, level, tile_x, tile_y, padding_color=None, z=0, icc_profile_intent=None, icc_profile_strict=False):
        try:
            zoom = self._level_to_zoom[level]
        except IndexError as exc:
            raise HTTPException(status_code=404, detail="Requested level does not exist.") from exc

        if self._single_tile_bytes is not None:
            if level == 0 and tile_x == 0 and tile_y == 0:
                return self._single_tile_bytes
            raise HTTPException(status_code=404, detail="Tile does not exist.")

        if self._mbtiles_conn is not None:
            data = self._get_tile_from_mbtiles(zoom, tile_x, tile_y)
            if data[:2] == b"\x1f\x8b":
                try:
                    data = gzip.decompress(data)
                except (OSError, gzip.BadGzipFile) as exc:
                    raise HTTPException(status_code=500, detail=f"Failed to decompress tile: {exc}") from exc
            return data

        if self.root is None:
            raise HTTPException(status_code=500, detail="Tile dataset is not initialized correctly.")

        lookup_tile_y = self._to_storage_tile_y(zoom, tile_y)
        for suffix in self._tile_suffixes:
            candidate = self.root / str(zoom) / str(tile_x) / f"{lookup_tile_y}{suffix}"
            if candidate.exists() and candidate.is_file():
                data = candidate.read_bytes()
                if data[:2] == b"\x1f\x8b":
                    data = gzip.decompress(data)
                return data

        raise HTTPException(status_code=404, detail="Tile does not exist.")

    async def get_icc_profile(self):
        return b""

    # dataset opening -------------------------------------------------------

    def _open_directory_dataset(self):
        self._zoom_ranges = self._scan_zoom_ranges(self.root)
        if not self._zoom_ranges:
            raise HTTPException(status_code=400, detail=f"No tile zoom directories found in {self.root}.")

    def _open_mbtiles_dataset(self):
        try:
            self._mbtiles_conn = sqlite3.connect(str(self.source))
        except sqlite3.Error as exc:
            raise HTTPException(status_code=400, detail=f"Failed to open MBTiles file: {exc}") from exc

        self._mbtiles_conn.row_factory = sqlite3.Row
        self.scheme = "tms"
        self._mbtiles_metadata = self._read_mbtiles_metadata()
        self.tile_size = int(self._mbtiles_metadata.get("tile_size", 256))
        scheme = self._mbtiles_metadata.get("scheme")
        if scheme:
            self.scheme = scheme.lower()

        available_zooms = self._fetch_mbtiles_zooms()
        if not available_zooms:
            raise HTTPException(status_code=400, detail="MBTiles file does not contain any tiles.")

        self._zoom_ranges = {
            zoom: {"max_x": (2 ** zoom) - 1, "max_y": (2 ** zoom) - 1}
            for zoom in available_zooms
        }

    def _open_file_dataset(self):
        if not self.source.exists() or not self.source.is_file():
            raise HTTPException(status_code=404, detail=f"Tile dataset does not exist: {self.source}")

        if self._is_single_tile_path(self.source):
            if self._matches_suffix(self.source.name, ".json") or self._matches_suffix(self.source.name, ".geojson"):
                raw = self.source.read_bytes()
                manifest = self._try_parse_manifest(raw)
                if manifest is not None:
                    self._open_manifest_dataset(manifest)
                    return
                self._set_single_tile(raw)
                return

            self._set_single_tile(self.source.read_bytes())
            return

        try:
            manifest = json.loads(self.source.read_text())
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=400, detail=f"Unsupported tile dataset file: {self.source.name}") from exc

        if not self._is_manifest_object(manifest):
            raise HTTPException(
                status_code=400,
                detail=(
                    "JSON input is not recognized as a manifest. "
                    "Expected keys like root, tile_suffixes, max_zoom, min_zoom, scheme, zoom_levels, or levels."
                ),
            )
        self._open_manifest_dataset(manifest)

    def _open_manifest_dataset(self, manifest: dict):
        root_value = manifest.get("root", manifest.get("tile_root", "."))
        self.root = (self.source.parent / root_value).resolve()
        if not self.root.exists() or not self.root.is_dir():
            raise HTTPException(status_code=400, detail=f"Manifest root does not exist or is not a directory: {self.root}")

        self.tile_size = int(manifest.get("tile_size", 256))
        self.scheme = str(manifest.get("scheme", "xyz")).lower()

        tile_suffixes = manifest.get("tile_suffixes")
        if tile_suffixes is None and manifest.get("tile_suffix") is not None:
            tile_suffixes = [manifest["tile_suffix"]]
        if tile_suffixes is not None:
            normalized = []
            for suffix in tile_suffixes:
                suffix = suffix if str(suffix).startswith(".") else f".{suffix}"
                normalized.append(str(suffix))
            self._tile_suffixes = normalized

        zoom_ranges = self._zoom_ranges_from_manifest(manifest)
        if zoom_ranges:
            self._zoom_ranges = zoom_ranges
        else:
            self._zoom_ranges = self._scan_zoom_ranges(self.root)

        if not self._zoom_ranges:
            raise HTTPException(status_code=400, detail="Manifest did not resolve to any readable tile zoom levels.")

    # tile lookup -----------------------------------------------------------

    def _get_tile_from_mbtiles(self, zoom: int, tile_x: int, tile_y: int) -> bytes:
        if self._mbtiles_conn is None:
            raise HTTPException(status_code=500, detail="MBTiles connection is not initialized.")

        storage_y = self._to_storage_tile_y(zoom, tile_y)
        cursor = self._mbtiles_conn.execute(
            "SELECT tile_data FROM tiles WHERE zoom_level = ? AND tile_column = ? AND tile_row = ?",
            (zoom, tile_x, storage_y),
        )
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Tile does not exist.")
        return bytes(row[0])

    # metadata / extent helpers --------------------------------------------

    def _build_slide_info(self):
        if not self._zoom_ranges:
            self._zoom_ranges = {0: {"max_x": 0, "max_y": 0}}

        self._level_to_zoom = sorted(self._zoom_ranges.keys(), reverse=True)
        max_zoom = self._level_to_zoom[0]
        levels: List[SlideLevel] = []
        for zoom in self._level_to_zoom:
            zoom_range = self._zoom_ranges[zoom]
            levels.append(
                SlideLevel(
                    extent=SlideExtent(
                        x=(zoom_range["max_x"] + 1) * self.tile_size,
                        y=(zoom_range["max_y"] + 1) * self.tile_size,
                        z=1,
                    ),
                    downsample_factor=float(2 ** (max_zoom - zoom)),
                )
            )

        self.slide_info = SlideInfo(
            id="",
            channels=[],
            channel_depth=8,
            extent=levels[0].extent,
            num_levels=len(levels),
            pixel_size_nm=SlidePixelSizeNm(x=-1, y=-1),
            tile_extent=SlideExtent(x=self.tile_size, y=self.tile_size, z=1),
            levels=levels,
        )

    def _zoom_ranges_from_manifest(self, manifest: dict) -> Dict[int, Dict[str, int]]:
        result: Dict[int, Dict[str, int]] = {}

        for zoom_key, dims in (manifest.get("bounds_by_zoom") or {}).items():
            zoom = int(zoom_key)
            if isinstance(dims, dict):
                max_x = int(dims.get("max_x", dims.get("x_tiles", 1) - 1))
                max_y = int(dims.get("max_y", dims.get("y_tiles", 1) - 1))
            else:
                max_x = int(dims[0])
                max_y = int(dims[1])
            result[zoom] = {"max_x": max_x, "max_y": max_y}

        levels = manifest.get("levels")
        if isinstance(levels, list):
            for item in levels:
                if isinstance(item, dict):
                    zoom = int(item["zoom"])
                    if "max_x" in item and "max_y" in item:
                        result[zoom] = {"max_x": int(item["max_x"]), "max_y": int(item["max_y"])}
                    elif "x_tiles" in item and "y_tiles" in item:
                        result[zoom] = {"max_x": int(item["x_tiles"]) - 1, "max_y": int(item["y_tiles"]) - 1}
                elif isinstance(item, int):
                    result.setdefault(item, {"max_x": (2 ** item) - 1, "max_y": (2 ** item) - 1})

        zoom_levels = manifest.get("zoom_levels")
        if isinstance(zoom_levels, list):
            for zoom in zoom_levels:
                result.setdefault(int(zoom), {"max_x": (2 ** int(zoom)) - 1, "max_y": (2 ** int(zoom)) - 1})

        min_zoom = manifest.get("min_zoom")
        max_zoom = manifest.get("max_zoom")
        if min_zoom is not None and max_zoom is not None:
            for zoom in range(int(min_zoom), int(max_zoom) + 1):
                result.setdefault(zoom, {"max_x": (2 ** zoom) - 1, "max_y": (2 ** zoom) - 1})

        return result

    def _scan_zoom_ranges(self, root: Path) -> Dict[int, Dict[str, int]]:
        zoom_ranges: Dict[int, Dict[str, int]] = {}
        for zoom_dir in sorted(root.iterdir(), key=lambda p: p.name):
            if not zoom_dir.is_dir() or not zoom_dir.name.isdigit():
                continue
            zoom = int(zoom_dir.name)
            max_x = -1
            max_y = -1
            for x_dir in zoom_dir.iterdir():
                if not x_dir.is_dir() or not x_dir.name.isdigit():
                    continue
                x_value = int(x_dir.name)
                max_x = max(max_x, x_value)
                for tile_file in x_dir.iterdir():
                    if not tile_file.is_file() or not self._matches_supported_tile_suffix(tile_file.name):
                        continue
                    y_value = self._parse_tile_y(tile_file.name)
                    if y_value is not None:
                        max_y = max(max_y, y_value)
            if max_x >= 0 and max_y >= 0:
                zoom_ranges[zoom] = {"max_x": max_x, "max_y": max_y}
        return zoom_ranges

    def _read_mbtiles_metadata(self) -> Dict[str, str]:
        if self._mbtiles_conn is None:
            return {}
        try:
            cursor = self._mbtiles_conn.execute("SELECT name, value FROM metadata")
            return {str(row[0]): str(row[1]) for row in cursor.fetchall()}
        except sqlite3.Error:
            return {}

    def _fetch_mbtiles_zooms(self) -> List[int]:
        if self._mbtiles_conn is None:
            return []
        cursor = self._mbtiles_conn.execute("SELECT DISTINCT zoom_level FROM tiles ORDER BY zoom_level")
        return [int(row[0]) for row in cursor.fetchall()]

    def _to_storage_tile_y(self, zoom: int, tile_y: int) -> int:
        if self.scheme != "tms":
            return tile_y
        max_y = self._zoom_ranges.get(zoom, {}).get("max_y", (2 ** zoom) - 1)
        return max_y - tile_y

    # parsing helpers -------------------------------------------------------

    def _set_single_tile(self, raw: bytes):
        self._single_tile_bytes = raw
        self._zoom_ranges = {0: {"max_x": 0, "max_y": 0}}

    def _is_single_tile_path(self, path: Path) -> bool:
        return self._matches_supported_tile_suffix(path.name)

    def _matches_supported_tile_suffix(self, name: str) -> bool:
        return any(name.endswith(suffix) for suffix in self._tile_suffixes)

    def _matches_suffix(self, name: str, suffix: str) -> bool:
        return name.endswith(suffix)

    def _parse_tile_y(self, filename: str) -> Optional[int]:
        match = _TILE_Y_RE.match(filename)
        if match is None:
            return None
        return int(match.group("y"))

    def _try_parse_manifest(self, raw: bytes) -> Optional[dict]:
        payload = raw
        if self._matches_suffix(self.source.name, ".gz"):
            try:
                payload = gzip.decompress(raw)
            except OSError:
                return None
        try:
            obj = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not self._is_manifest_object(obj):
            return None
        return obj

    def _is_manifest_object(self, obj) -> bool:
        return isinstance(obj, dict) and any(key in obj for key in MANIFEST_HINT_KEYS)

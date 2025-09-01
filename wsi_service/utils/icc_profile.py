import gzip
import io
from http.client import HTTPException
from typing import Optional

from PIL import Image, ImageCms


def get_error_response(status_code: int, detail: str):
    return {
        "rep": "error",
        "status_code": status_code,
        "detail": detail,
    }


class ICCProfileError(Exception):
    """Custom exception for ICC Profile errors."""

    def __init__(self, payload):
        super().__init__(payload["detail"])
        self.payload = payload

    def get_error_response(self):
        return self.payload, None


class ICCProfile(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def process_pil_image(self, image: Image, profile_data: Optional[bytes | ImageCms.ImageCmsProfile],
                          strict: bool = False, intent: str = "perceptual", cache: bool = False):
        """
        Process a PIL image with an ICC profile provided. This method caches icc transform if `cache` is True.
        Also, the cached transform is used only if `cache` is True. This should be used for region/tile queries,
        where we expect the same profile. For macros and other operations, the profile could differ, and cache
        might not be desirable.
        """
        try:
            if profile_data:
                transform = self.get(intent) if cache else None
                if not transform:
                    mode = image.mode
                    if isinstance(profile_data, bytes):
                        profile_data = ImageCms.ImageCmsProfile(io.BytesIO(profile_data))
                    transform = ImageCms.buildTransform(
                        profile_data, ImageCms.createProfile("sRGB"), mode, mode,
                        renderingIntent=self._get_intent(intent)
                    )
                    if cache:
                        self[intent] = transform
                return ImageCms.applyTransform(image, transform)
            elif strict:
                raise ICCProfileError(get_error_response(412, "ICC Profile not available."))

        except Exception as ex:
            if strict:

                if "ICC Profile not available" in str(ex):
                    raise ICCProfileError(get_error_response(412, "Error: ICC Profile not available."))
                import traceback
                print(traceback.format_exc())

                raise ICCProfileError(get_error_response(500, f"Error: {ex}"))
        # if no data profile and strict is False, no-op
        return image

    def get_for_payload(self, profile_data: Optional[bytes | ImageCms.ImageCmsProfile]):
        if profile_data:
            if isinstance(profile_data, ImageCms.ImageCmsProfile):
                profile_data = profile_data.tobytes()
            return profile_data
        raise HTTPException(404, "ICC Profile not available.")

    def _get_intent(self, intent: str):
        match intent:
            case "perceptual" | None:
                return ImageCms.Intent.PERCEPTUAL
            case "relative_colorimetric":
                return ImageCms.Intent.RELATIVE_COLORIMETRIC
            case "saturation":
                return ImageCms.Intent.SATURATION
            case "absolute_colorimetric":
                return ImageCms.Intent.ABSOLUTE_COLORIMETRIC
        raise ValueError(f"Invalid intent {intent}!")

    def free_cache(self):
        self.clear()

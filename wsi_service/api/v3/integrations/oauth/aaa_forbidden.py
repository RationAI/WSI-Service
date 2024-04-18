from fastapi import Depends, HTTPException, status


def _forbidden():
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="This API is not allowed for use.",
    )


class Forbidden:
    def __init__(self, settings, logger, http_client):
        self.settings = settings
        self.logger = logger
        self.http_client = http_client

    def global_depends(self):
        return Depends(_forbidden)

from fastapi import Depends


def _dummy():
    pass


# Note: Documentation is provided in default.py
class DisableAuth:
    def __init__(self, settings, logger, http_client):
        self.settings = settings
        self.logger = logger
        self.http_client = http_client

    def global_depends(self):
        return Depends(_dummy)

    async def allow_access_slide(self, auth_payload, slide_id, manager, plugin, slide=None):
        ...

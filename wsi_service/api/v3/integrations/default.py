from fastapi import Depends, HTTPException, status


def _unauthorized():
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Integration not configured",
    )


class Default:
    """
    Authentication class should provide:
    global_depends - method that returns a callback wrapped in Depends (fastapi deps injection)
    user_*_hook - methods that receive output of the above callback together with relevant data and
        should raise HTTPException with status 401 in case user has no access to particular data item
    """

    def __init__(self, settings, logger, http_client):
        self.settings = settings
        self.logger = logger
        self.http_client = http_client

    def global_depends(self):
        """Basic authentication by (callback) dependency injection. Callback should return auth payload if any."""
        return Depends(_unauthorized)

    async def allow_access_slide(self, auth_payload, slide):
        ...

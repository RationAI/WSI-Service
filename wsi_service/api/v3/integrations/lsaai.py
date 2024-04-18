from fastapi import HTTPException

from .oauth.aaa_oauth import OAuthSettings, OAuthIntegration


class LSAAIIntegration(OAuthIntegration):
    def __init__(self, settings, logger):
        super().__init__(settings, logger, OAuthSettings, {'Content-Type': 'application/json'})

    async def allow_access_slide(self, auth_payload, slide):
        try:
            user_data = await self.get_user_info(auth_payload)
            print("WOULD RESOLVE AUTH ACCESS", user_data)
            print("WOULD RESOLVE SLIDE", slide)

        except Exception as e:
            raise HTTPException(401, "Token or user info endpoint data is invalid!") from e

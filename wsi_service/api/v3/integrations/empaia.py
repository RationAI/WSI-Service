from typing import Any

from fastapi import Depends, HTTPException, Request
from fastapi.openapi.models import OAuthFlowAuthorizationCode, OAuthFlows
from fastapi.security import OAuth2
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from ....empaia_receiver_auth import Auth


class AuthSettings(BaseSettings):
    idp_url: str
    audience: str
    refresh_interval: int = 300  # seconds
    openapi_token_url: str = ""
    openapi_auth_url: str = ""
    rewrite_url_in_wellknown: str = ""

    model_config = SettingsConfigDict(env_prefix="ws_", env_file=".env", extra="ignore")


class Payload(BaseModel):
    token: dict
    request: Any = None


def make_oauth2_wrapper(auth: Auth, auth_settings: AuthSettings):
    oauth2_scheme = OAuth2(
        flows=OAuthFlows(
            authorizationCode=OAuthFlowAuthorizationCode(
                tokenUrl=auth_settings.openapi_token_url, authorizationUrl=auth_settings.openapi_auth_url
            )
        )
    )

    # Dependency wrapper takes slide_id from path information (passed automatically)
    def oauth2_wrapper(request: Request, token=Depends(oauth2_scheme)):
        decoded_token = auth.decode_token(token)
        return Payload(token=decoded_token, request=request)

    return oauth2_wrapper


# Note: Documentation is provided in default.py
class EmpaiaApiIntegration:
    def __init__(self, settings, logger, http_client):
        self.settings = settings
        self.logger = logger
        self.http_client = http_client

        self.auth_settings = AuthSettings()

        self.auth = Auth(
            idp_url=self.auth_settings.idp_url.rstrip("/"),
            refresh_interval=self.auth_settings.refresh_interval,
            audience=self.auth_settings.audience,
            logger=self.logger,
            rewrite_url_in_wellknown=self.auth_settings.rewrite_url_in_wellknown,
        )
        self.oauth2_wrapper = make_oauth2_wrapper(auth=self.auth, auth_settings=self.auth_settings)

    def global_depends(self):
        return Depends(self.oauth2_wrapper)

    async def allow_access_slide(self, auth_payload, slide_id, manager, plugin, slide=None):
        ...

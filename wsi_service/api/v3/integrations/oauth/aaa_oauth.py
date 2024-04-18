import copy

import aiohttp
from typing import Any

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2
from fastapi.openapi.models import OAuthFlowAuthorizationCode, OAuthFlows

from . import Auth
from .lru_timeout_cache import LRUTimeoutCache

class OAuthSettings(BaseSettings):
    idp_url: str
    audience: str
    refresh_interval: int = 300  # seconds
    openapi_token_url: str = ""
    openapi_auth_url: str = ""
    rewrite_url_in_wellknown: str = ""

    # Authorization Data Caching
    user_cache_timeout: int = 1800
    user_cache_size: int = 999
    user_info_endpoint: str = ""  # Url to the user info data, e.g. 'https://login.bbmri-eric.eu/oidc/userinfo'

    model_config = SettingsConfigDict(env_prefix="wbs_", env_file=".env")


class BaseJwtTokenModel(BaseModel):
    sub: str
    exp: str


class TokenPayload(BaseModel):
    payload: str
    data: BaseJwtTokenModel


class Payload(BaseModel):
    token: TokenPayload
    request: Any = None


def make_oauth2_wrapper(auth: Auth, auth_settings: OAuthSettings):
    oauth2_scheme = OAuth2(
        flows=OAuthFlows(
            authorizationCode=OAuthFlowAuthorizationCode(
                tokenUrl=auth_settings.openapi_token_url, authorizationUrl=auth_settings.openapi_auth_url
            )
        )
    )

    def oauth2_wrapper(request: Request, token=Depends(oauth2_scheme)):
        decoded_token = auth.decode_token(token)
        token_payload = TokenPayload(payload=token, data=decoded_token)
        return Payload(token=token_payload, request=request)

    return oauth2_wrapper


class LoggerNoLog:
    def error(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass

    def debug(self, *args, **kwargs):
        pass


class OAuthIntegration:
    """
    OAuth Integration:
     - provide global app settings to store in the integration for internal use
     - provide logger for issue logging
     - provide auth_settings class to instantiate for oauth flow (note: must inherit from AuthSettings)

     If no user_info_endpoint endpoint is configured, the module returns the auth payload.
     Otherwise, user info is retrieved and cached from the given url using the token payload (method GET).
     The data can be simply retrieved as await get_user_info(auth_payload)
    """
    def __init__(self, settings, logger=None, auth_settings=OAuthSettings, headers=None):
        self.headers = {} if headers is None else headers
        self.settings = settings
        self.logger = logger if logger is not None else LoggerNoLog()
        self.auth_settings = auth_settings()

        self.auth = Auth(
            idp_url=self.auth_settings.idp_url.rstrip("/"),
            refresh_interval=self.auth_settings.refresh_interval,
            audience=self.auth_settings.audience,
            logger=self.logger,
            rewrite_url_in_wellknown=self.auth_settings.rewrite_url_in_wellknown,
        )
        self.oauth2_wrapper = make_oauth2_wrapper(auth=self.auth, auth_settings=self.auth_settings)
        if self.auth_settings.user_cache_size:
            self.user_cache = LRUTimeoutCache(self.auth_settings.user_cache_size, self.auth_settings.user_cache_timeout)

    def global_depends(self):
        return Depends(self.oauth2_wrapper)

    async def get_user_info(self, auth_payload: TokenPayload):
        if not auth_payload.data.sub:
            raise HTTPException(status_code=401, detail="Auth payload does not contain 'sub' subject ID!")
        if not self.auth_settings.user_info_endpoint:
            return auth_payload

        user_info = self.user_cache.get_item(auth_payload.data.sub)
        if not user_info:
            headers = copy.copy(self.headers)
            headers['Authorization'] = f"Bearer {auth_payload.payload}"
            async with aiohttp.ClientSession() as session:
                async with session.get(self.auth_settings.user_info_endpoint, headers=headers) as response:
                    user_info = await response.text()
                    self.user_cache.put_item(auth_payload.data.sub, user_info)
        return user_info

# Vendored from https://gitlab.com/empaia/integration/empaia-sender-auth
# (commit 481620e), MIT License, Copyright (c) 2021 EMPAIA.
# Formerly a git submodule; only the parts used by WSI-Service are kept.

import asyncio
import datetime
from copy import deepcopy
from json import JSONEncoder, dumps
from logging import Logger
from typing import Optional
from urllib.parse import urlparse
from urllib.request import getproxies_environment, proxy_bypass_environment
from uuid import UUID

import aiohttp
import jwt
from aiohttp import ClientResponse
from pydantic import BaseModel

UNAUTHORIZED_CODES = [401, 403]


class CustomHTTPException(Exception):
    def __init__(self, status_code, detail=None, headers=None):
        self.status_code = status_code
        self.detail = detail
        self.headers = headers
        super().__init__(status_code)


class CustomStreamingResponse:
    def __init__(self, content, status_code=200, headers=None, media_type=None, background=None):
        self.content = content
        self.status_code = status_code
        self.headers = headers
        self.media_type = media_type
        self.background = background


class AuthSettings(BaseModel):
    idp_url: str
    client_id: str
    client_secret: str


class ResponseMetaData(BaseModel):
    status_code: Optional[int] = None
    media_type: Optional[str] = None
    content_encoding: Optional[str] = None


class CustomEncoder(JSONEncoder):
    def default(self, o) -> str:
        if isinstance(o, UUID):
            return str(o)

        return super(CustomEncoder, self).default(o)


def custom_dumps(o):
    return dumps(o, cls=CustomEncoder)


class LoggerNoLog:
    def error(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass

    def debug(self, *args, **kwargs):
        pass


class AioHttpClient:
    def __init__(
        self,
        logger: Logger = None,
        auth_settings: AuthSettings = None,
        chunk_size: int = None,
        timeout: int = None,
        connection_limit_per_host: int = None,
        enable_custom_mode: bool = False,
        token_check_interval: int = None,
        request_timeout: int = None,
    ):
        self.logger = logger if logger is not None else LoggerNoLog()
        self.auth_settings = auth_settings
        self.chunk_size = chunk_size if chunk_size is not None else 10240  # 10KB
        self.timeout = timeout if timeout is not None else 300
        self.request_timeout = request_timeout if request_timeout is not None else 300
        self.connection_limit_per_host = connection_limit_per_host if connection_limit_per_host is not None else 100
        self.enable_custom_mode = enable_custom_mode
        self.token_check_interval = token_check_interval if token_check_interval is not None else 5  # seconds

        self.idp_url = None
        self.well_known_url = None
        if self.auth_settings is not None:
            self.idp_url = auth_settings.idp_url.rstrip("/")
            self.well_known_url = f"{self.idp_url}/.well-known/openid-configuration"

        self.well_known = None
        self.token = None
        self.token_best_before = datetime.datetime.now()

        if self.enable_custom_mode:
            self.HTTPException = CustomHTTPException
            self.StreamingResponse = CustomStreamingResponse
        else:
            from fastapi import HTTPException
            from fastapi.responses import StreamingResponse

            self.HTTPException = HTTPException
            self.StreamingResponse = StreamingResponse

    async def update_token_routine(self):
        if self.auth_settings is None:
            return

        self.logger.debug("Starting update token routine.")

        while True:
            if datetime.datetime.now() > self.token_best_before:
                try:
                    await self._update_token()
                except Exception as e:  # pylint: disable=W0718
                    self.logger.error("Could not retrieve new access token. Unexpected error: %s", e)

            await asyncio.sleep(self.token_check_interval)

    @property
    def client(self):
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        connector = aiohttp.TCPConnector(limit_per_host=self.connection_limit_per_host, force_close=True)
        return aiohttp.ClientSession(timeout=timeout, connector=connector, json_serialize=custom_dumps)

    @staticmethod
    def _bool_to_str(val):
        if isinstance(val, bool):
            return str(val)
        return val

    @staticmethod
    def _params(params):
        if params is None:
            return
        return {key: AioHttpClient._bool_to_str(val) for key, val in params.items() if val is not None}

    @staticmethod
    def _proxy(url):
        parsed_url = urlparse(url)
        host = parsed_url.netloc.split(":")[0]
        proxies = getproxies_environment()
        if parsed_url.scheme not in proxies:
            return None
        if proxy_bypass_environment(host=host, proxies=proxies):
            return None
        return proxies[parsed_url.scheme]

    async def _json_or_content(self, response: ClientResponse):
        status = response.status
        content_type = response.content_type
        if content_type == "application/json":
            content = await response.json()
        else:
            content = await response.text()
        if not 200 <= status < 300:
            raise self.HTTPException(status_code=status, detail=content)
        return content

    def _headers(self, headers: dict = None):
        if headers is None and self.token is None:
            return None

        result = {}

        if headers is not None:
            result = {key: val for key, val in headers.items() if val is not None}

        if self.token is not None:
            result["Authorization"] = f"Bearer {self.token}"

        return result

    async def _update_token(self):
        async with self.client as client:
            if not self.well_known:
                proxy = self._proxy(self.well_known_url)
                async with client.get(self.well_known_url, proxy=proxy) as response:
                    status = response.status
                    content_type = response.content_type
                    if content_type == "application/json":
                        content = await response.json()
                    else:
                        content = await response.text()

                if not 200 <= status < 300:
                    self.logger.error("Could not retrieve new access token: %s %s", status, content)
                    return

                self.well_known = await response.json()

            token_url = self.well_known["token_endpoint"]
            data = {
                "grant_type": "client_credentials",
                "client_id": self.auth_settings.client_id,
                "client_secret": self.auth_settings.client_secret,
            }
            self._log(method="post", url=token_url, params=None, data=data, json=None, headers=None, is_stream=False)
            proxy = self._proxy(token_url)
            async with client.post(token_url, data=data, raise_for_status=False, proxy=proxy) as response:
                status = response.status
                content_type = response.content_type
                if content_type == "application/json":
                    content = await response.json()
                else:
                    content = await response.text()

            if not 200 <= status < 300:
                self.logger.error("Could not retrieve new access token: %s %s", status, content)
                return

            token = content["access_token"]
            decoded_token = jwt.decode(token, options={"verify_signature": False})

            exp = datetime.datetime.fromtimestamp(decoded_token["exp"])
            iat = datetime.datetime.fromtimestamp(decoded_token["iat"])
            token_valid_for = exp - iat
            token_valid_for = max(token_valid_for, datetime.timedelta(0))  # protect against negative timedelta
            token_refresh_in = token_valid_for / 2
            token_best_before = datetime.datetime.now() + token_refresh_in
            self.logger.info(
                "Token retrieved: valid for %s, next refresh attempt in %s", token_valid_for, token_refresh_in
            )

            self.token = token
            self.token_best_before = token_best_before

    def _log(self, method, url, params=None, data=None, json=None, headers=None, is_stream=False):
        self.logger.debug(
            "ESA: method='%s' url='%s' has_params=%r has_body=%r has_headers=%r is_stream=%r",
            method,
            url,
            params is not None,
            data is not None or json is not None,
            headers is not None,
            is_stream,
        )

    async def get(self, url: str, params=None, data=None, json=None, headers=None, return_status=False):
        params = self._params(params)
        headers = self._headers(headers)
        self._log(method="get", url=url, params=params, data=data, json=json, headers=headers, is_stream=False)
        async with self.client as client:
            async with client.get(
                url,
                params=params,
                data=data,
                json=json,
                raise_for_status=False,
                headers=headers,
                proxy=self._proxy(url),
                timeout=self.request_timeout,
            ) as response:
                content = await self._json_or_content(response)
                if return_status:
                    return response.status, content
                else:
                    return content

    async def delete(self, url: str, params=None, data=None, json=None, headers=None, return_status=False):
        params = self._params(params)
        headers = self._headers(headers)
        self._log(method="delete", url=url, params=params, data=data, json=json, headers=headers, is_stream=False)
        async with self.client as client:
            async with client.delete(
                url,
                params=params,
                data=data,
                json=json,
                raise_for_status=False,
                headers=headers,
                proxy=self._proxy(url),
                timeout=self.request_timeout,
            ) as response:
                content = await self._json_or_content(response)
                if return_status:
                    return response.status, content
                else:
                    return content

    async def post(self, url: str, params=None, data=None, json=None, headers=None, return_status=False):
        params = self._params(params)
        headers = self._headers(headers)
        self._log(method="post", url=url, params=params, data=data, json=json, headers=headers, is_stream=False)
        async with self.client as client:
            async with client.post(
                url,
                params=params,
                data=data,
                json=json,
                raise_for_status=False,
                headers=headers,
                proxy=self._proxy(url),
                timeout=self.request_timeout,
            ) as response:
                content = await self._json_or_content(response)
                if return_status:
                    return response.status, content
                else:
                    return content

    async def put(self, url: str, params=None, data=None, json=None, headers=None, return_status=False):
        params = self._params(params)
        headers = self._headers(headers)
        self._log(method="put", url=url, params=params, data=data, json=json, headers=headers, is_stream=False)
        async with self.client as client:
            async with client.put(
                url,
                params=params,
                data=data,
                json=json,
                raise_for_status=False,
                headers=headers,
                proxy=self._proxy(url),
                timeout=self.request_timeout,
            ) as response:
                content = await self._json_or_content(response)
                if return_status:
                    return response.status, content
                else:
                    return content

    async def raw_stream(
        self, request_type: str, url: str, params=None, data=None, json=None, headers=None, chunk_size=None
    ):
        params = self._params(params)
        headers = self._headers(headers)
        chunk_size = chunk_size if chunk_size is not None else self.chunk_size
        self._log(method=request_type, url=url, params=params, data=data, json=json, headers=headers, is_stream=True)
        async with self.client as client:
            request_funcs = {
                "get": client.get,
                "put": client.put,
                "post": client.post,
                "delete": client.delete,
            }
            func = request_funcs[request_type]
            proxy = self._proxy(url)
            async with func(
                url,
                data=data,
                json=json,
                params=params,
                raise_for_status=False,
                headers=headers,
                proxy=proxy,
                auto_decompress=False,
            ) as response:
                status = response.status
                media_type = response.content_type
                content_encoding = response.headers.get("Content-Encoding")
                yield ResponseMetaData(status_code=status, media_type=media_type, content_encoding=content_encoding)
                async for chunk in response.content.iter_chunked(chunk_size):
                    yield chunk

    async def get_stream(self, url: str, params=None, data=None, json=None, headers=None, chunk_size=None):
        async for chunk in self.raw_stream(
            request_type="get",
            url=url,
            params=params,
            data=data,
            json=json,
            headers=headers,
            chunk_size=chunk_size,
        ):
            yield chunk

    async def put_stream(self, url: str, params=None, data=None, json=None, headers=None, chunk_size=None):
        async for chunk in self.raw_stream(
            request_type="put",
            url=url,
            params=params,
            data=data,
            json=json,
            headers=headers,
            chunk_size=chunk_size,
        ):
            yield chunk

    async def post_stream(self, url: str, params=None, data=None, json=None, headers=None, chunk_size=None):
        async for chunk in self.raw_stream(
            request_type="post",
            url=url,
            params=params,
            data=data,
            json=json,
            headers=headers,
            chunk_size=chunk_size,
        ):
            yield chunk

    async def delete_stream(self, url: str, params=None, data=None, json=None, headers=None, chunk_size=None):
        async for chunk in self.raw_stream(
            request_type="delete",
            url=url,
            params=params,
            data=data,
            json=json,
            headers=headers,
            chunk_size=chunk_size,
        ):
            yield chunk

    async def get_stream_response(self, url: str, params=None, data=None, json=None, headers=None, chunk_size=None):
        stream = self.get_stream(url=url, params=params, data=data, json=json, headers=headers, chunk_size=chunk_size)
        rmd = await stream.__anext__()
        response_headers = None
        if rmd.content_encoding:
            response_headers = {"Content-Encoding": rmd.content_encoding}

        return self.StreamingResponse(
            content=stream, status_code=rmd.status_code, media_type=rmd.media_type, headers=response_headers
        )

    async def put_stream_response(self, url: str, params=None, data=None, json=None, headers=None, chunk_size=None):
        stream = self.put_stream(url=url, params=params, data=data, json=json, headers=headers, chunk_size=chunk_size)
        rmd = await stream.__anext__()
        return self.StreamingResponse(content=stream, status_code=rmd.status_code, media_type=rmd.media_type)

    async def post_stream_response(self, url: str, params=None, data=None, json=None, headers=None, chunk_size=None):
        stream = self.post_stream(url=url, params=params, data=data, json=json, headers=headers, chunk_size=chunk_size)
        rmd = await stream.__anext__()
        return self.StreamingResponse(content=stream, status_code=rmd.status_code, media_type=rmd.media_type)

    async def delete_stream_response(self, url: str, params=None, data=None, json=None, headers=None, chunk_size=None):
        stream = self.delete_stream(
            url=url, params=params, data=data, json=json, headers=headers, chunk_size=chunk_size
        )
        rmd = await stream.__anext__()
        return self.StreamingResponse(content=stream, status_code=rmd.status_code, media_type=rmd.media_type)

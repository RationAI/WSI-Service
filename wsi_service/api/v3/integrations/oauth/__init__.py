import json
from logging import Logger
from time import time

import jwt
import requests

from jwt.algorithms import RSAAlgorithm
from fastapi import Depends, HTTPException, Request, status


class Auth:
    def __init__(
        self, idp_url: str, refresh_interval: int, audience: str, logger: Logger, rewrite_url_in_wellknown: str = None
    ):
        self.idp_url = idp_url.rstrip("/")
        self.refresh_interval = refresh_interval
        self.audience = audience
        self.logger = logger
        self.rewrite_url_in_wellknown = (
            rewrite_url_in_wellknown.rstrip("/") if rewrite_url_in_wellknown is not None else rewrite_url_in_wellknown
        )
        self.well_known_url = f"{self.idp_url}/.well-known/openid-configuration"

        self._public_keys = {}
        self._supported_algorithms = None
        self._issuer = None
        self._last_time_updated = None

        self._ensure_updated_internal()

    def _ensure_updated_internal(self):
        if self._last_time_updated is None:
            self._update_internal_values()
        elif (time().real - self._last_time_updated) > self.refresh_interval:
            self._update_internal_values()

    def _rewrite_url(self, url):
        if self.rewrite_url_in_wellknown is None or self.rewrite_url_in_wellknown == "":
            return url
        if not url.startswith(self.rewrite_url_in_wellknown):
            self.logger.error(
                "Could not rewrite URL in wellknown, because URL %s does not start with rewrite_url_in_wellknown %s"
                % (url, self.rewrite_url_in_wellknown)
            )
            return url
        len_url = len(self.rewrite_url_in_wellknown)
        url_path = url[len_url:].lstrip("/")
        return f"{self.idp_url}/{url_path}"

    def _update_internal_values(self):
        try:
            r = requests.get(self.well_known_url, timeout=8)
            r.raise_for_status()
            well_known = r.json()
        except Exception as e:
            self.logger.error(f"Could not retrieve well-known data: {e}")
            return

        if not isinstance(well_known, dict):
            self.logger.error("Well-known data is not a dict.")
            return

        supported_algorithms = well_known.get("id_token_signing_alg_values_supported")
        if not supported_algorithms:
            self.logger.error("Well-known data does not contain supported algorithms.")
            return

        issuer = well_known.get("issuer")
        if not issuer:
            self.logger.error("Well-known data does not contain issuer.")
            return

        certs_url = well_known.get("jwks_uri")
        if not certs_url:
            self.logger.error("Well-known data does not contain certs url")
            return
        certs_url = self._rewrite_url(url=certs_url)

        try:
            r = requests.get(certs_url, timeout=8)
            r.raise_for_status()
            certs = r.json()
        except Exception as e:
            self.logger.error(f"Could not retrieve certs data: {e}")
            return

        keys = certs.get("keys")
        if not keys:
            self.logger.error("Certs data does not contain keys")
            return

        public_keys = {}
        try:
            for key in keys:
                kid = key["kid"]
                key = RSAAlgorithm.from_jwk(json.dumps(key))
                public_keys[kid] = key
        except Exception as e:
            self.logger.error(f"Could not convert public keys from certs data: {e}")
            return

        self._public_keys = public_keys
        self._supported_algorithms = supported_algorithms
        self._issuer = issuer
        self._last_time_updated = time().real

    def decode_token(self, token):
        self._ensure_updated_internal()

        if self._last_time_updated is None:
            raise HTTPException(
                status_code=401,
                detail="Auth not initialized on server.",
            )

        if token.lower().startswith("bearer "):
            token = token[7:]

        try:
            unverified = jwt.get_unverified_header(token)

            alg = unverified.get("alg")
            kid = unverified.get("kid")

            if alg not in self._supported_algorithms:
                raise HTTPException(
                    status_code=401,
                    detail="Algorithm required for token decoding not found.",
                )

            if kid not in self._public_keys:
                raise HTTPException(
                    status_code=401,
                    detail="Public key required for token decoding not found.",
                )

            options = None
            if self.audience is None:
                options = {"verify_aud": False}

            decoded_token = jwt.decode(
                token,
                self._public_keys.get(kid),
                algorithms=alg,
                audience=self.audience,
                issuer=self._issuer,
                options=options,
            )
            return decoded_token
        except jwt.exceptions.ExpiredSignatureError as e:
            raise HTTPException(status_code=401, detail="Access Token expired.") from e
        except jwt.exceptions.DecodeError as e:
            raise HTTPException(status_code=401, detail="Error decoding Token.") from e
        except jwt.exceptions.InvalidTokenError as e:
            parsed_token = jwt.decode(token, options={"verify_signature": False})
            if "aud" not in parsed_token or parsed_token["aud"] != self.audience:
                raise HTTPException(status_code=401, detail="API access denied.") from e
            raise HTTPException(status_code=401, detail="Invalid Token.") from e

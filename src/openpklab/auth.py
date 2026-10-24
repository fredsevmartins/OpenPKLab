"""Single-workspace access: private bearer or external OAuth JWT resource server."""
from __future__ import annotations
import asyncio
import os
import secrets
from urllib.parse import urlsplit

import jwt
from mcp.server.auth.provider import AccessToken
from starlette.responses import JSONResponse


class OwnerVerifier:
    def __init__(self):
        self.token = os.getenv("OPENPKLAB_TOKEN", "")
        self.issuer = os.getenv("OPENPKLAB_OAUTH_ISSUER", "")
        self.audience = os.getenv("OPENPKLAB_OAUTH_AUDIENCE", "")
        self.subject = os.getenv("OPENPKLAB_OWNER_SUB", "")
        self.jwks_url = os.getenv("OPENPKLAB_OAUTH_JWKS_URL", "")
        self.resource_url = os.getenv("OPENPKLAB_PUBLIC_URL", "")
        self.jwks = None
        if self.issuer:
            if not all((self.audience, self.subject, self.jwks_url, self.resource_url)):
                raise ValueError("OAuth requires issuer, audience, owner subject, JWKS URL and public URL")
            for value in (self.issuer, self.jwks_url, self.resource_url):
                parsed = urlsplit(value)
                if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
                    raise ValueError("OAuth URLs must be HTTPS URLs without credentials, query or fragment")
            if urlsplit(self.resource_url).path != "/mcp":
                raise ValueError("OPENPKLAB_PUBLIC_URL must end in /mcp")
            self.jwks = jwt.PyJWKClient(self.jwks_url, cache_jwk_set=True, lifespan=300, timeout=10)
        elif len(self.token) < 32:
            raise ValueError("HTTP requires OPENPKLAB_TOKEN (at least 32 characters) or complete OAuth configuration")

    def _verify_jwt(self, token):
        try:
            key = self.jwks.get_signing_key_from_jwt(token)
            claims = jwt.decode(token, key.key, algorithms=["RS256", "ES256"], audience=self.audience, issuer=self.issuer, options={"require": ["exp", "iat", "sub", "iss", "aud"]})
            scopes = claims.get("scope", "").split()
            if claims["sub"] != self.subject or "notebook" not in scopes:
                return None
            return AccessToken(token=token, client_id=str(claims.get("azp", "owner")), scopes=scopes, expires_at=int(claims["exp"]), subject=claims["sub"], resource=self.resource_url)
        except (jwt.PyJWTError, ValueError, TypeError, KeyError):
            return None

    async def verify_token(self, token: str):
        if self.issuer:
            return await asyncio.to_thread(self._verify_jwt, token)
        if secrets.compare_digest(token, self.token):
            return AccessToken(token=token, client_id="workspace_owner", scopes=["notebook"], subject="workspace_owner")
        return None


class ProtectHTTP:
    def __init__(self, app, verifier: OwnerVerifier):
        self.app = app
        self.verifier = verifier

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope["path"]
        if path == "/healthz" or path in {"/.well-known/oauth-protected-resource", "/.well-known/oauth-protected-resource/mcp"}:
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        auth = headers.get(b"authorization", b"").decode("latin1")
        scheme, _, token = auth.partition(" ")
        identity = await self.verifier.verify_token(token) if scheme.lower() == "bearer" and len(token) <= 16000 else None
        if identity is None:
            challenge = "Bearer"
            if self.verifier.issuer:
                parsed = urlsplit(self.verifier.resource_url)
                challenge += f' resource_metadata="{parsed.scheme}://{parsed.netloc}/.well-known/oauth-protected-resource/mcp"'
            return await JSONResponse({"error": "Authentication required"}, status_code=401, headers={"WWW-Authenticate": challenge, "Cache-Control": "no-store"})(scope, receive, send)
        return await self.app(scope, receive, send)

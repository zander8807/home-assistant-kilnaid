"""Async client for the private KilnAid cloud API."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from aiohttp import ClientError, ClientResponse, ClientSession

from .const import API_URL, CLIENT_HEADERS, LOGIN_URL
from .models import KilnData


class KilnAidError(Exception):
    """Base KilnAid client error."""


class KilnAidAuthenticationError(KilnAidError):
    """Raised when KilnAid rejects the account credentials."""


class KilnAidConnectionError(KilnAidError):
    """Raised when KilnAid cannot be reached or returns invalid data."""


class KilnAidApi:
    """Small client for the endpoints used by the KilnAid web application."""

    def __init__(self, session: ClientSession, email: str, password: str) -> None:
        self._session = session
        self._email = email.strip().lower()
        self._password = password
        self._token: str | None = None

    @property
    def email(self) -> str:
        """Return the normalized account email."""
        return self._email

    async def async_login(self) -> None:
        """Authenticate and retain the opaque token in memory."""
        try:
            response = await self._session.post(
                LOGIN_URL,
                headers={
                    "Content-Type": CLIENT_HEADERS["Content-Type"],
                    "kaid-version": CLIENT_HEADERS["kaid-version"],
                },
                json={"email": self._email, "password": self._password},
            )
        except ClientError as err:
            raise KilnAidConnectionError("Unable to connect to KilnAid") from err

        if response.status in (401, 403):
            response.release()
            raise KilnAidAuthenticationError("Invalid KilnAid credentials")

        payload = await self._read_json(response)
        token = payload.get("authentication_token")
        if not isinstance(token, str) or not token:
            raise KilnAidAuthenticationError("KilnAid did not return an authentication token")
        self._token = token

    async def async_get_kilns(self) -> list[KilnData]:
        """Fetch all claimed kilns and their current detailed status."""
        settings = await self._async_request("POST", "/kilns/settings", json={})
        if not isinstance(settings, list):
            raise KilnAidConnectionError("Unexpected kiln settings response")

        kiln_names: dict[str, str] = {}
        identifiers: list[str] = []
        for item in settings:
            if not isinstance(item, Mapping):
                continue
            serial = item.get("serial_number")
            if not isinstance(serial, str) or not serial:
                continue
            identifiers.append(serial)
            name = item.get("name")
            kiln_names[serial] = name if isinstance(name, str) and name else f"Kiln {serial}"

        if not identifiers:
            return []

        detail = await self._async_request("POST", "/kilns/view", json={"ids": identifiers})
        raw_kilns = detail.get("kilns") if isinstance(detail, Mapping) else None
        if isinstance(raw_kilns, Mapping):
            raw_kilns = list(raw_kilns.values())
        if not isinstance(raw_kilns, list):
            raise KilnAidConnectionError("Unexpected kiln status response")

        result: list[KilnData] = []
        for raw in raw_kilns:
            if not isinstance(raw, Mapping):
                continue
            kiln = KilnData.from_api(dict(raw), kiln_names)
            if kiln is not None:
                result.append(kiln)
        return result

    async def _async_request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Perform one request, re-authenticating once if the token is rejected."""
        if self._token is None:
            await self.async_login()

        for attempt in range(2):
            headers = {
                **CLIENT_HEADERS,
                "email": self._email,
                "auth-token": f"binst-cookie={self._token}",
            }
            try:
                response = await self._session.request(
                    method, f"{API_URL}{path}", headers=headers, **kwargs
                )
            except ClientError as err:
                raise KilnAidConnectionError("Unable to connect to KilnAid") from err

            if response.status not in (401, 403):
                return await self._read_json(response)

            response.release()
            self._token = None
            if attempt == 0:
                await self.async_login()

        raise KilnAidAuthenticationError("KilnAid authentication expired")

    @staticmethod
    async def _read_json(response: ClientResponse) -> Any:
        """Validate a response and decode JSON without exposing response contents."""
        try:
            response.raise_for_status()
            return await response.json(content_type=None)
        except (ClientError, ValueError) as err:
            raise KilnAidConnectionError(
                f"KilnAid returned HTTP {response.status} or invalid JSON"
            ) from err

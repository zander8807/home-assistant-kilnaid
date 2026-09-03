"""Tests for KilnAid cloud client recovery."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, Mock

PACKAGE_DIR = Path(__file__).parents[1] / "custom_components" / "kilnaid"


class ClientError(Exception):
    """Minimal aiohttp error stand-in for isolated unit tests."""


class ClientConnectionError(ClientError):
    """Minimal connection error stand-in."""


AIOHTTP = types.ModuleType("aiohttp")
AIOHTTP.ClientError = ClientError
AIOHTTP.ClientConnectionError = ClientConnectionError
AIOHTTP.ClientResponse = object
AIOHTTP.ClientSession = object
sys.modules.setdefault("aiohttp", AIOHTTP)

PACKAGE = types.ModuleType("kilnaid")
PACKAGE.__path__ = [str(PACKAGE_DIR)]
sys.modules.setdefault("kilnaid", PACKAGE)


def _load_module(name: str):
    spec = importlib.util.spec_from_file_location(f"kilnaid.{name}", PACKAGE_DIR / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_load_module("const")
_load_module("models")
API = _load_module("api")


class KilnAidApiRecoveryTest(unittest.IsolatedAsyncioTestCase):
    """Verify failures cannot leave a stale token permanently in use."""

    async def test_connection_failure_invalidates_token(self) -> None:
        session = AsyncMock()
        session.request.side_effect = ClientConnectionError("offline")
        api = API.KilnAidApi(session, "person@example.com", "secret")
        api._token = "stale-token"

        with self.assertRaises(API.KilnAidConnectionError):
            await api._async_request("POST", "/kilns/settings", json={})

        self.assertIsNone(api._token)

    async def test_bad_response_invalidates_token(self) -> None:
        response = AsyncMock()
        response.status = 500
        response.raise_for_status = Mock(side_effect=ClientConnectionError("bad response"))
        session = AsyncMock()
        session.request.return_value = response
        api = API.KilnAidApi(session, "person@example.com", "secret")
        api._token = "stale-token"

        with self.assertRaises(API.KilnAidConnectionError):
            await api._async_request("POST", "/kilns/settings", json={})

        self.assertIsNone(api._token)


if __name__ == "__main__":
    unittest.main()

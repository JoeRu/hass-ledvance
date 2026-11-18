"""Security and authentication regression tests for the Tuya API."""

from unittest.mock import MagicMock, patch

import pytest

from custom_components.hass_ledvance.api import TuyaAPI
from custom_components.hass_ledvance.exceptions import CannotConnect, InvalidAuthentication


def make_api():
    api = TuyaAPI("user@example.com", "password", "https://example.com/api", 1)
    api.sid = "session-id"
    return api


@pytest.mark.parametrize("status", [301, 302, 307, 308])
def test_rejects_redirect_without_forwarding_secret(status):
    api = make_api()
    response = MagicMock(status_code=status)
    with patch.object(api.session, "post", return_value=response) as post:
        with pytest.raises(CannotConnect, match="redirect"):
            api._api({"action": "test"}, {"key": "sensitive"})
    assert post.call_args.kwargs["allow_redirects"] is False
    response.json.assert_not_called()


def test_rejects_unexpected_json_shape():
    api = make_api()
    response = MagicMock(status_code=200)
    response.json.return_value = []
    with patch.object(api.session, "post", return_value=response):
        with pytest.raises(CannotConnect, match="payload"):
            api._api({"action": "test"})


def test_rejects_invalid_json():
    api = make_api()
    response = MagicMock(status_code=200)
    response.json.side_effect = ValueError("invalid")
    with patch.object(api.session, "post", return_value=response):
        with pytest.raises(CannotConnect, match="JSON"):
            api._api({"action": "test"})


def test_device_auth_failure_propagates():
    api = make_api()
    api.rooms = MagicMock(return_value={})
    api._api = MagicMock(return_value=[{"devId": "dev1"}])
    api._device_info = MagicMock(side_effect=InvalidAuthentication())
    with pytest.raises(InvalidAuthentication):
        api.devices("group1")

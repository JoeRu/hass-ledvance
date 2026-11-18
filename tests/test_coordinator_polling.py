"""Cloud discovery runs on its own schedule; regular polls stay cheap."""

import time
from dataclasses import replace
from unittest.mock import MagicMock, patch

import pytest

from custom_components.hass_ledvance.api import DeviceInfo, TuyaAPI
from custom_components.hass_ledvance.const import CLOUD_DISCOVERY_INTERVAL, CLOUD_DISCOVERY_RETRY
from custom_components.hass_ledvance.coordinator import LedvanceTuyaCoordinator
from custom_components.hass_ledvance.exceptions import (
    CannotConnect,
    InvalidAuthentication,
    TooManyRequests,
)

SCHEMA = [{"id": 1, "code": "switch_led"}]
LAN = {"Lan": {"ip": "192.168.1.10", "version": "3.3"}}


def _info(dev_id: str, dps: dict | None = None, *, online: bool = True, key: str = "key") -> DeviceInfo:
    return DeviceInfo(dev_id, dev_id, dev_id, "", online, key, "", SCHEMA, dps or {"1": True}, room_name="Office")


def _api(cloud: dict[str, DeviceInfo]) -> MagicMock:
    """Mock API serving copies of ``cloud`` (mutate it to change what the cloud reports)."""
    api = MagicMock(spec=TuyaAPI)
    api.sid = "session"
    api.groups.return_value = [{"groupId": "home"}]
    api.devices.side_effect = lambda _gid: [replace(dev) for dev in cloud.values()]
    api.device.side_effect = lambda dev_id: replace(cloud[dev_id], room_name="")
    return api


def _lan_poll(dev_id, ip, _key, _version):
    """Only the device found by the LAN scan answers locally."""
    return {"1": False} if ip else None


@pytest.fixture
def lan_poll():
    with patch.object(LedvanceTuyaCoordinator, "_poll_dps_local", side_effect=_lan_poll) as mock:
        yield mock


def _coordinator(hass, api) -> LedvanceTuyaCoordinator:
    coordinator = LedvanceTuyaCoordinator(hass, api)
    coordinator._lan_cache = dict(LAN)
    return coordinator


def test_first_poll_discovers_without_a_second_device_get(hass, lan_poll):
    cloud = {"Lan": _info("Lan"), "Cloud": _info("Cloud", {"1": True})}
    api = _api(cloud)
    coordinator = _coordinator(hass, api)

    data = coordinator._fetch_all_devices()

    assert set(data) == {"Lan", "Cloud"}
    api.groups.assert_called_once()
    api.devices.assert_called_once_with("home")
    api.device.assert_not_called()  # the discovery snapshot is fresh this cycle
    assert data["Lan"].dps == {"1": False} and data["Lan"].lan_reachable
    assert data["Cloud"].dps == {"1": True} and not data["Cloud"].lan_reachable


def test_regular_poll_skips_discovery_and_lan_devices_cost_nothing(hass, lan_poll):
    cloud = {"Lan": _info("Lan"), "Cloud": _info("Cloud")}
    api = _api(cloud)
    coordinator = _coordinator(hass, api)
    coordinator.data = coordinator._fetch_all_devices()
    api.reset_mock()

    cloud["Cloud"] = _info("Cloud", {"1": False}, online=False)
    data = coordinator._fetch_all_devices()

    api.groups.assert_not_called()
    api.devices.assert_not_called()
    api.device.assert_called_once_with("Cloud")  # one call, only for the non-LAN device
    assert data["Cloud"].dps == {"1": False}
    assert data["Cloud"].is_online is False  # cloud offline status still tracked every poll
    assert data["Cloud"].room_name == "Office"  # device.get has no room; keep discovery's


def test_discovery_reruns_when_due_and_tracks_device_list(hass, lan_poll):
    cloud = {"Lan": _info("Lan"), "Old": _info("Old")}
    api = _api(cloud)
    coordinator = _coordinator(hass, api)
    before = time.monotonic()
    coordinator._fetch_all_devices()
    assert coordinator._next_discovery >= before + CLOUD_DISCOVERY_INTERVAL

    del cloud["Old"]
    cloud["New"] = _info("New")
    coordinator._next_discovery = 0.0  # interval elapsed
    data = coordinator._fetch_all_devices()

    assert api.groups.call_count == 2
    assert set(data) == {"Lan", "New"}


async def test_refresh_discovery_forces_a_discovery(hass, lan_poll):
    api = _api({"Lan": _info("Lan")})
    coordinator = _coordinator(hass, api)
    await coordinator.async_refresh()
    await coordinator.async_refresh()
    assert api.groups.call_count == 1

    await coordinator.async_refresh_discovery()
    assert api.groups.call_count == 2


@pytest.mark.parametrize("exc", [CannotConnect("down"), TooManyRequests("limit")])
def test_cloud_outage_keeps_known_devices_and_retries_sooner(hass, lan_poll, exc):
    cloud = {"Lan": _info("Lan"), "Cloud": _info("Cloud")}
    api = _api(cloud)
    coordinator = _coordinator(hass, api)
    coordinator.data = coordinator._fetch_all_devices()

    api.groups.side_effect = exc
    api.device.side_effect = CannotConnect("down")
    coordinator._next_discovery = 0.0
    before = time.monotonic()
    data = coordinator._fetch_all_devices()

    assert set(data) == {"Lan", "Cloud"}
    assert data["Lan"].dps == {"1": False}  # LAN keeps working without the cloud
    assert before + CLOUD_DISCOVERY_RETRY <= coordinator._next_discovery
    assert coordinator._next_discovery < before + CLOUD_DISCOVERY_INTERVAL


def test_first_discovery_failure_still_raises(hass, lan_poll):
    api = _api({})
    api.groups.side_effect = CannotConnect("down")
    coordinator = _coordinator(hass, api)
    with pytest.raises(CannotConnect):
        coordinator._fetch_all_devices()
    assert coordinator._next_discovery is None


def test_auth_failure_during_rediscovery_is_not_masked(hass, lan_poll):
    api = _api({"Lan": _info("Lan")})
    coordinator = _coordinator(hass, api)
    coordinator._fetch_all_devices()

    api.groups.side_effect = InvalidAuthentication()
    coordinator._next_discovery = 0.0
    with pytest.raises(InvalidAuthentication):
        coordinator._fetch_all_devices()


def test_cloud_poll_refreshes_cached_metadata(hass, lan_poll):
    """A new local key (e.g. after a factory reset) is picked up without rediscovery."""
    cloud = {"Cloud": _info("Cloud", key="old-key")}
    api = _api(cloud)
    coordinator = _coordinator(hass, api)
    coordinator._fetch_all_devices()

    cloud["Cloud"] = _info("Cloud", key="new-key")
    data = coordinator._fetch_all_devices()

    assert data["Cloud"].local_key == "new-key"
    assert coordinator._metadata["Cloud"].local_key == "new-key"
    assert coordinator._metadata["Cloud"].room_name == "Office"


def test_cloud_backoff_keeps_newest_known_state(hass, lan_poll):
    cloud = {"Cloud": _info("Cloud", {"1": True})}
    api = _api(cloud)
    coordinator = _coordinator(hass, api)
    coordinator.data = coordinator._fetch_all_devices()
    # e.g. an optimistic update after a command, newer than the discovery snapshot
    coordinator.data["Cloud"] = replace(coordinator.data["Cloud"], dps={"1": False})

    api.device.side_effect = CannotConnect("down")
    data = coordinator._fetch_all_devices()

    assert data["Cloud"].dps == {"1": False}
    assert coordinator._cloud_retry_after["Cloud"] > time.monotonic()

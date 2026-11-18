"""Never overwrite device areas chosen by Home Assistant users."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from custom_components.hass_ledvance.__init__ import _async_assign_areas


@pytest.mark.parametrize("current,assigned,should_update", [
    ("manual", None, False),
    (None, None, True),
    ("manual", "kitchen", False),
    (None, "kitchen", False),  # user manually cleared a previous automatic area
    ("kitchen", "kitchen", True),
])
async def test_preserves_manual_assignments(hass, current, assigned, should_update):
    dev = SimpleNamespace(room_name="Office", name="Light")
    coordinator = MagicMock()
    coordinator.data = {"dev": dev}
    coordinator._auto_area_assignments = {}
    if assigned is not None:
        coordinator._auto_area_assignments["dev"] = assigned
    areas = SimpleNamespace(areas={"office": SimpleNamespace(name="Office", id="office")})
    device = SimpleNamespace(id="device_id", area_id=current)
    device_registry = MagicMock()
    device_registry.async_get_device.return_value = device
    with patch("custom_components.hass_ledvance.__init__.ar.async_get", return_value=areas), patch(
        "custom_components.hass_ledvance.__init__.dr.async_get", return_value=device_registry
    ):
        await _async_assign_areas(hass, coordinator)
    assert device_registry.async_update_device.called == should_update
    if should_update:
        device_registry.async_update_device.assert_called_once_with("device_id", area_id="office")

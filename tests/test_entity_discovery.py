"""Newly discovered devices must be registered exactly once."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from custom_components.hass_ledvance.entity_discovery import register_discovered_entities


def test_entity_discovery_adds_late_devices_once():
    first = SimpleNamespace(name="first")
    second = SimpleNamespace(name="second")
    coordinator = MagicMock()
    coordinator.data = {"one": first}
    callbacks = []
    coordinator.async_add_listener.side_effect = callbacks.append
    entry = MagicMock()
    add_entities = MagicMock()
    build_entities = MagicMock(side_effect=lambda device_id, dev: [device_id])

    register_discovered_entities(coordinator, entry, add_entities, build_entities)
    add_entities.assert_called_once_with(["one"])
    coordinator.data["two"] = second
    callbacks[0]()
    assert add_entities.call_count == 2
    add_entities.assert_called_with(["two"])
    callbacks[0]()
    assert add_entities.call_count == 2
    assert build_entities.call_count == 2

"""Register entities added by cloud discovery without reloading the config entry."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import CoordinatorDeviceData, LedvanceTuyaCoordinator


def register_discovered_entities(
    coordinator: LedvanceTuyaCoordinator,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
    create_for_device: Callable[[str, CoordinatorDeviceData], Iterable[Entity]],
) -> None:
    """Add each discovered device once per platform, including during initial setup.

    A platform can create multiple entities for one device. Existing entity IDs
    are stable because the same platform factories are used for initial and late
    discovery. Devices that disappear temporarily are not re-registered.
    """
    seen_devices: set[str] = set()

    def add_new_devices() -> None:
        if not coordinator.data:
            return
        new_devices = [
            (dev_id, dev)
            for dev_id, dev in coordinator.data.items()
            if dev_id not in seen_devices
        ]
        entities: list[Entity] = []
        for dev_id, dev in new_devices:
            entities.extend(create_for_device(dev_id, dev))
            seen_devices.add(dev_id)
        if entities:
            async_add_entities(entities)

    add_new_devices()
    entry.async_on_unload(coordinator.async_add_listener(add_new_devices))

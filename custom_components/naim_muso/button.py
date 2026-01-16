"""Naim Mu-so Button Platform."""

from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import BaseEntity
from .const import LOGGER as _LOGGER


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Naim Mu-so button entities from a config entry."""
    _LOGGER.info(
        "button.async_setup_entry called for %s (%s)", entry.entry_id, entry.title
    )

    coordinator = entry.runtime_data.coordinator
    _LOGGER.info("Coordinator: %s, Device: %s", coordinator, coordinator._device)

    # Wait for the coordinator to have device data
    if not coordinator._device:
        _LOGGER.warning("Device not ready, skipping button setup")
        return

    # Get the available inputs from the device
    inputs = coordinator._device.inputs
    _LOGGER.info("Available inputs: %s", inputs)

    if not inputs:
        _LOGGER.warning("No inputs available, skipping button setup")
        return

    # Create a button for each available input source
    buttons = []
    for input_index, input_name in inputs.items():
        _LOGGER.info("Creating button for input %s: %s", input_index, input_name)
        buttons.append(
            NaimSourceButton(
                coordinator=coordinator,
                input_index=input_index,
                input_name=input_name,
            )
        )

    _LOGGER.info("Adding %d button entities", len(buttons))
    async_add_entities(buttons)


class NaimSourceButton(BaseEntity, ButtonEntity):
    """Button entity to select a specific input source on Naim Mu-so."""

    def __init__(self, coordinator, input_index: str, input_name: str) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator, parameter=f"source_{input_index}")
        self._input_index = input_index
        self._input_name = input_name
        self._attr_name = f"{input_name}"
        self._attr_translation_key = None  # Use the actual input name

    @property
    def icon(self) -> str:
        """Return the icon for this button."""
        # Map common source names to icons
        icon_map = {
            "spotify": "mdi:spotify",
            "tidal": "mdi:music-circle",
            "iradio": "mdi:radio",
            "upnp": "mdi:server-network",
            "airplay": "mdi:cast-audio",
            "bluetooth": "mdi:bluetooth-audio",
            "usb": "mdi:usb",
            "optical": "mdi:optical-fiber",
            "coaxial": "mdi:cable-data",
            "analog": "mdi:audio-input-rca",
        }

        # Try to match the input name (case-insensitive) to an icon
        input_lower = self._input_name.lower()
        for key, icon in icon_map.items():
            if key in input_lower:
                return icon

        # Default icon for unknown sources
        return "mdi:import"

    @property
    def available(self) -> bool:
        """Return if the button is available."""
        return self.coordinator.device is not None

    async def async_press(self) -> None:
        """Handle the button press to select this input source."""
        _LOGGER.debug(
            "Selecting input %s (%s) on %s",
            self._input_name,
            self._input_index,
            self.coordinator.attr_name,
        )
        await self.coordinator.device.select_input(self._input_index)

        # Request an immediate update after changing source
        await self.coordinator.async_request_refresh()

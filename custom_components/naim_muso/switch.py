"""Naim Mu-so Switch Platform."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import BaseEntity
from . import MusoCoordinator
from .const import LOGGER as _LOGGER


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Naim Mu-so switch entities from a config entry."""
    _LOGGER.debug(
        "switch.async_setup_entry called for %s (%s)", entry.entry_id, entry.title
    )

    coordinator: MusoCoordinator = entry.runtime_data.coordinator

    if not coordinator._device:
        _LOGGER.warning("Device not ready, skipping switch setup")
        return

    async_add_entities([NaimCleaningModeSwitch(coordinator=coordinator)])


class NaimCleaningModeSwitch(BaseEntity, SwitchEntity):
    """Switch entity to toggle cleaning mode on Naim Mu-so."""

    _attr_icon = "mdi:spray-bottle"
    _attr_translation_key = "cleaning_mode"

    def __init__(self, coordinator: MusoCoordinator) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator, parameter="cleaning_mode")
        self._attr_name = "Cleaning Mode"
        self._is_on: bool = False

    @property
    def available(self) -> bool:
        """Return if the switch is available."""
        return self.coordinator.device is not None

    @property
    def is_on(self) -> bool:
        """Return True if cleaning mode is on."""
        return self._device.state.cleaningmode

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on cleaning mode."""
        _LOGGER.debug("Turning on cleaning mode")
        await self._device.set_cleaningmode(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off cleaning mode."""
        _LOGGER.debug("Turning off cleaning mode")
        await self._device.set_cleaningmode(False)

    # async def async_added_to_hass(self) -> None:
    #     """Run when entity is added to hass."""
    #     await super().async_added_to_hass()
    #     # Query initial state
    #     await self._async_update_state()

    # async def _async_update_state(self) -> None:
    #     """Query the current cleaning mode state from the device."""
    #     if not self.coordinator.device:
    #         return

    #     try:
    #         response = await self.coordinator.device.controller.nvm.send_command(
    #             "GETCLEANINGMODE"
    #         )
    #         _LOGGER.debug("GETCLEANINGMODE response: %s", response)
    #         # Response format: "#NVM GETCLEANINGMODE ON " or "#NVM GETCLEANINGMODE OFF "
    #         if response:
    #             self._is_on = "ON" in response.upper()
    #             self.async_write_ha_state()
    #     except Exception as ex:
    #         _LOGGER.warning("Failed to get cleaning mode state: %s", ex)

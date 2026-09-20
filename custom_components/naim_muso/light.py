import math
from typing import ClassVar

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.color import brightness_to_value, value_to_brightness

from . import MusoCoordinator
from .base_entity import BaseEntity

BRIGHTNESS_SCALE = (1, 3)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the Sensors."""
    # This gets the data update coordinator from the config entry runtime data as specified in your __init__.py
    coordinator: MusoCoordinator = config_entry.runtime_data.coordinator

    light = MusoIllumination(coordinator, "illum")

    async_add_entities([light])


class MusoIllumination(BaseEntity, LightEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes: ClassVar[set[ColorMode]] = {ColorMode.BRIGHTNESS}
    _attr_translation_key = "illum"

    @property
    def brightness(self) -> int | None:
        """Return the current brightness."""
        assert self._device and self._device.state.illum is not None
        # _LOGGER.debug("MusoIllumination.brightness %s", self._device.state.illum)
        return value_to_brightness(BRIGHTNESS_SCALE, self._device.state.illum)

    @property
    def is_on(self) -> bool:
        """Return the current illumination state."""
        if not self._device or self._device.state.illum is None:
            return False
        return self._device.state.illum > 0

    @property
    def translation_key(self) -> str:
        """Return the translation key."""
        return "illum"

    async def async_turn_on(self, **kwargs) -> None:
        """Turn illuminatio on."""

        if not self._device:
            return
        if ATTR_BRIGHTNESS in kwargs:
            value_in_range = math.ceil(
                brightness_to_value(BRIGHTNESS_SCALE, kwargs[ATTR_BRIGHTNESS])
            )
            await self._device.set_illum(value_in_range)
        else:
            await self._device.set_illum(3)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn illumination off."""
        assert self._device
        await self._device.set_illum(0)

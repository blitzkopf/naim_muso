from typing import Optional
import math
from homeassistant.components.light import LightEntity, ColorMode, ATTR_BRIGHTNESS
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util.color import value_to_brightness, brightness_to_value

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .base_entity import BaseEntity
from . import MusoCoordinator
from .const import LOGGER as _LOGGER

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
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_translation_key = "illum"

    @property
    def brightness(self) -> Optional[int]:
        """Return the current brightness."""
        _LOGGER.debug("MusoIllumination.brightness %s", self._device.state.illum)
        return value_to_brightness(BRIGHTNESS_SCALE, self._device.state.illum)

    @property
    def is_on(self) -> bool:
        """Return the current illumination state."""
        return self._device.state.illum and self._device.state.illum > 0

    @property
    def translation_key(self) -> str:
        """Return the translation key."""
        return "illum"

    async def async_turn_on(self, **kwargs) -> None:
        """Turn illuminatio on."""
        if ATTR_BRIGHTNESS in kwargs:
            value_in_range = int(
                math.ceil(
                    brightness_to_value(BRIGHTNESS_SCALE, kwargs[ATTR_BRIGHTNESS])
                )
            )
            await self._device.set_illum(value_in_range)
        else:
            await self._device.set_illum(3)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn illumination off."""
        await self._device.set_illum(0)

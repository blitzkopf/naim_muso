from typing import Optional
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import callback
from naimco import NaimCo
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN
from .coordinator import MusoCoordinator


class BaseEntity(CoordinatorEntity):
    """Base Entity Class.

    This inherits a CoordinatorEntity class to register your entites to be updated
    by your DataUpdateCoordinator when async_update_data is called, either on the scheduled
    interval or by forcing an update.
    """

    # ----------------------------------------------------------------------------
    # Using attr_has_entity_name = True causes HA to name your entities with the
    # device name and entity name.  Ie if your name property of your entity is
    # Voltage and this entity belongs to a device, Lounge Socket, this will name
    # your entity to be sensor.lounge_socket_voltage
    #
    # It is highly recommended (by me) to use this to give a good name structure
    # to your entities.  However, totally optional.
    # ----------------------------------------------------------------------------
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: MusoCoordinator, parameter: str, translation_key: str = None
    ) -> None:
        """Initialise entity."""
        super().__init__(coordinator)
        self.udn = coordinator.udn
        self.device_type = coordinator.device_type
        # self._attr_name = coordinator.name
        self._attr_translation_key = translation_key or parameter
        # self._attr_translation_key = "illum"

        # self._attr_unique_id = coordinator.unique_id
        self.device_id = coordinator.unique_id
        self.parameter = parameter

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        # This method is called by your DataUpdateCoordinator when a successful update runs.
        # self.device = self.coordinator.get_device(self.device_id)
        # _LOGGER.debug(
        #     "Updating device: %s, %s",
        #     self.device_id,
        #     self.coordinator.get_device_parameter(
        #         self.device_id, "device_name"),
        # )
        # This is probably wasteful as it will update all sensors on every update
        # but it is simple and works for now.
        self.async_write_ha_state()

    @property
    def _device(self) -> Optional[NaimCo]:
        return self.coordinator._device

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return self.coordinator.device_info

    # @property
    # def name(self) -> str:
    #     """Return the name of the sensor."""
    #     return self.parameter.replace("_", " ").title()

    @property
    def unique_id(self) -> str:
        """Return unique id."""

        # ----------------------------------------------------------------------------
        # All entities must have a unique id across your whole Home Assistant server -
        # and that also goes for anyone using your integration who may have many other
        # integrations loaded.
        #
        # Think carefully what you want this to be as changing it later will cause HA
        # to create new entities.
        #
        # It is recommended to have your integration name (DOMAIN), some unique id
        # from your device such as a UUID, MAC address etc (not IP address) and then
        # something unique to your entity (like name - as this would be unique on a
        # device)
        #
        # If in your situation you have some hub that connects to devices which then
        # you want to create multiple sensors for each device, you would do something
        # like.
        #
        # f"{DOMAIN}-{HUB_MAC_ADDRESS}-{DEVICE_UID}-{ENTITY_NAME}""
        #
        # This is even more important if your integration supports multiple instances.
        # ----------------------------------------------------------------------------
        return f"{DOMAIN}-{self.device_id}-{self.parameter}"

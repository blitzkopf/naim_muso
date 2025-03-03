from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.core import callback
from .coordinator import MusoCoordinator
from homeassistant.const import UnitOfTemperature, UnitOfElectricPotential
from typing import Any, Optional
from dataclasses import dataclass
from .const import LOGGER as _LOGGER, DOMAIN
from naimco import NaimCo


@dataclass
class SensorTypeClass:
    """Class for holding sensor type to sensor class."""

    type: str
    sensor_class: object


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the Sensors."""
    # This gets the data update coordinator from the config entry runtime data as specified in your __init__.py
    coordinator: MusoCoordinator = config_entry.runtime_data.coordinator

    # ----------------------------------------------------------------------------
    # Here we enumerate the sensors in your data value from your
    # DataUpdateCoordinator and add an instance of your sensor class to a list
    # for each one.
    # This maybe different in your specific case, depending on how your data is
    # structured
    # ----------------------------------------------------------------------------
    # TODO: make this dynamic, other players might have different sensors
    sensor_types = [
        SensorTypeClass("Psu", MusoTemperatureSensor),
        SensorTypeClass("MAIN", MusoTemperatureSensor),
        SensorTypeClass("1V2", MusoVoltageSensor),
        SensorTypeClass("1V9", MusoVoltageSensor),
        SensorTypeClass("3V3", MusoVoltageSensor),
        SensorTypeClass("5V", MusoVoltageSensor),
        SensorTypeClass("1V85", MusoVoltageSensor),
        SensorTypeClass("36V", MusoVoltageSensor),
    ]
    _LOGGER.debug("media_player.async_setup_entry %s (%s)",
                  config_entry.entry_id, config_entry.title)
    sensors = []

    for sensor_type in sensor_types:
        sensors.append(
            sensor_type.sensor_class(coordinator, sensor_type.type)
        )
        # sensors.extend(
        #     [
        #         sensor_type.sensor_class(coordinator, device, sensor_type.type)
        #         for device in coordinator.data
        #         if device.get(sensor_type.type)
        #     ]
        # )

    # Now create the sensors.
    async_add_entities(sensors)


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
        self, coordinator: MusoCoordinator, parameter: str
    ) -> None:
        """Initialise entity."""
        super().__init__(coordinator)
        self.udn = coordinator.udn
        self.device_type = coordinator.device_type
        self._attr_name = coordinator.name
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

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self.parameter.replace("_", " ").title()

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


class BaseSensor(BaseEntity, SensorEntity):
    """Implementation of a sensor.

    This inherits our ExampleBaseEntity to set common properties.
    See base.py for this class.

    https://developers.home-assistant.io/docs/core/entity/sensor
    """
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self) -> int | float:
        """Return the state of the entity."""
        # Using native value and native unit of measurement, allows you to change units
        # in Lovelace and HA will automatically calculate the correct value.
        return self.coordinator.get_device_parameter(self.device_id, self.parameter)


class MusoTemperatureSensor(BaseSensor):
    """Class to handle temperature sensors.

    This inherits the ExampleBaseSensor and so uses all the properties and methods
    from that class and then overrides specific attributes relevant to this sensor type.
    """
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_suggested_display_precision = 0

    @property
    def native_value(self) -> int | float:
        """Return the state of the entity."""
        # Using native value and native unit of measurement, allows you to change units
        # in Lovelace and HA will automatically calculate the correct value.
        try:
            return self.coordinator.device.state._unit_temps[self.parameter].get(
                "temp", None)
        except KeyError:
            return None


class MusoVoltageSensor(BaseSensor):
    """Class to handle temperature sensors.

    This inherits the ExampleBaseSensor and so uses all the properties and methods
    from that class and then overrides specific attributes relevant to this sensor type.
    """
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.MILLIVOLT
    _attr_suggested_display_precision = 0

    @property
    def native_value(self) -> int | float:
        """Return the state of the entity."""
        # Using native value and native unit of measurement, allows you to change units
        # in Lovelace and HA will automatically calculate the correct value.
        try:
            return self.coordinator.device.state._voltages.get(self.parameter, None)
        except KeyError:
            return None

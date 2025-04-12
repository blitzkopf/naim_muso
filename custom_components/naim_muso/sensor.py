from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.entity import EntityCategory
from .coordinator import MusoCoordinator
from homeassistant.const import UnitOfTemperature, UnitOfElectricPotential
from dataclasses import dataclass
from .const import LOGGER as _LOGGER
from .base_entity import BaseEntity


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

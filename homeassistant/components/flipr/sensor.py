"""Sensor platform for the Flipr's pool_sensor."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import ELECTRIC_POTENTIAL_MILLIVOLT, TEMP_CELSIUS

from . import FliprEntity
from .const import DOMAIN

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="chlorine",
        name="Chlorine",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_MILLIVOLT,
        icon="mdi:pool",
    ),
    SensorEntityDescription(
        key="ph",
        name="pH",
        icon="mdi:pool",
    ),
    SensorEntityDescription(
        key="temperature",
        name="Water Temp",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=TEMP_CELSIUS,
    ),
    SensorEntityDescription(
        key="date_time",
        name="Last Measured",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
    SensorEntityDescription(
        key="red_ox",
        name="Red OX",
        native_unit_of_measurement=ELECTRIC_POTENTIAL_MILLIVOLT,
        icon="mdi:pool",
    ),
)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Defer sensor setup to the shared sensor module."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    sensors = [FliprSensor(coordinator, description) for description in SENSOR_TYPES]
    async_add_entities(sensors)


class FliprSensor(FliprEntity, SensorEntity):
    """Sensor representing FliprSensor data."""

    @property
    def native_value(self):
        """State of the sensor."""
        return self.coordinator.data[self.entity_description.key]

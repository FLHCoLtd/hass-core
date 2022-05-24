"""Class to hold all thermostat accessories."""
import logging

from pyhap.const import CATEGORY_HUMIDIFIER

from homeassistant.components.humidifier.const import (
    ATTR_HUMIDITY,
    ATTR_MAX_HUMIDITY,
    ATTR_MIN_HUMIDITY,
    DEFAULT_MAX_HUMIDITY,
    DEFAULT_MIN_HUMIDITY,
    DEVICE_CLASS_DEHUMIDIFIER,
    DEVICE_CLASS_HUMIDIFIER,
    DOMAIN,
    SERVICE_SET_HUMIDITY,
)
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    PERCENTAGE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
)
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change_event

from .accessories import TYPES, HomeAccessory
from .const import (
    CHAR_ACTIVE,
    CHAR_CURRENT_HUMIDIFIER_DEHUMIDIFIER,
    CHAR_CURRENT_HUMIDITY,
    CHAR_DEHUMIDIFIER_THRESHOLD_HUMIDITY,
    CHAR_HUMIDIFIER_THRESHOLD_HUMIDITY,
    CHAR_LOCK_PHYSICAL_CONTROLS,
    CHAR_ROTATION_SPEED,
    CHAR_SWING_MODE,
    CHAR_TARGET_HUMIDIFIER_DEHUMIDIFIER,
    CONF_LINKED_HUMIDITY_SENSOR,
    PROP_LOCK_PHYSICAL_VALID_VALUES,
    PROP_MAX_VALUE,
    PROP_MIN_STEP,
    PROP_MIN_VALUE,
    PROP_SWING_MODE_VALID_VALUES,
    SERV_HUMIDIFIER_DEHUMIDIFIER
)

_LOGGER = logging.getLogger(__name__)

HC_HUMIDIFIER = 1
HC_DEHUMIDIFIER = 2

HC_HASS_TO_HOMEKIT_DEVICE_CLASS = {
    DEVICE_CLASS_HUMIDIFIER: HC_HUMIDIFIER,
    DEVICE_CLASS_DEHUMIDIFIER: HC_DEHUMIDIFIER,
}

HC_HASS_TO_HOMEKIT_DEVICE_CLASS_NAME = {
    DEVICE_CLASS_HUMIDIFIER: "Humidifier",
    DEVICE_CLASS_DEHUMIDIFIER: "Dehumidifier",
}

HC_DEVICE_CLASS_TO_TARGET_CHAR = {
    HC_HUMIDIFIER: CHAR_HUMIDIFIER_THRESHOLD_HUMIDITY,
    HC_DEHUMIDIFIER: CHAR_DEHUMIDIFIER_THRESHOLD_HUMIDITY,
}

HC_STATE_INACTIVE = 0
HC_STATE_IDLE = 1
HC_STATE_HUMIDIFYING = 2
HC_STATE_DEHUMIDIFYING = 3


@TYPES.register("HumidifierDehumidifier")
class HumidifierDehumidifier(HomeAccessory):
    """Generate a HumidifierDehumidifier accessory for a humidifier."""

    def __init__(self, *args):
        """Initialize a HumidifierDehumidifier accessory object."""
        super().__init__(*args, category=CATEGORY_HUMIDIFIER)
        self.chars = []

        print("self.hass.keys::::", self.hass.__dict__.keys())

        print("self.hass.states::::", self.hass.states.__dict__)
        print(self.hass.states)

        state = self.hass.states.get(self.entity_id)

        device_class = state.attributes.get(ATTR_DEVICE_CLASS, DEVICE_CLASS_HUMIDIFIER)
        print("device_class::: ", device_class)
        self._hk_device_class = HC_HASS_TO_HOMEKIT_DEVICE_CLASS[device_class]
        print("self._hk_device_class::::", self._hk_device_class)
        self._target_humidity_char_name = HC_DEVICE_CLASS_TO_TARGET_CHAR[
            self._hk_device_class
        ]
        print("_target_humidity_char_name:::::", self._target_humidity_char_name)
        self.chars.append(self._target_humidity_char_name)

        if device_class == DEVICE_CLASS_DEHUMIDIFIER:
            print("add chars")

            self.chars.append(CHAR_HUMIDIFIER_THRESHOLD_HUMIDITY)
            print(f"add {CHAR_HUMIDIFIER_THRESHOLD_HUMIDITY}")

            # self.chars.append(CHAR_ROTATION_SPEED)
            # print(f"add {CHAR_ROTATION_SPEED}")

            # self.chars.append(CHAR_SWING_MODE)
            # print(f"add {CHAR_SWING_MODE}")

            # self.chars.append(CHAR_LOCK_PHYSICAL_CONTROLS)
            # print(f"add {CHAR_LOCK_PHYSICAL_CONTROLS}")

            print("add chars end")

        print("self.chars::::", self.chars)

        serv_humidifier_dehumidifier = self.add_preload_service(
            SERV_HUMIDIFIER_DEHUMIDIFIER, self.chars
        )

        # Current and target mode characteristics
        self.char_current_humidifier_dehumidifier = (
            serv_humidifier_dehumidifier.configure_char(
                    CHAR_CURRENT_HUMIDIFIER_DEHUMIDIFIER, value=0, valid_values={
                        "Dehumidifying": 3,
                        "Humidifying": 2,
                        "Idle": 1,
                        "Inactive": 0
                    }
            )
        )

        if device_class == DEVICE_CLASS_DEHUMIDIFIER:
            # char_valid_values = {'Dehumidifier': 2}
            char_valid_values = {
                'Dehumidifier': 2,
                'Humidifier': 1,
                'HumidifierorDehumidifier': 0
            }
        else:
            char_valid_values = {
                'Dehumidifier': 2,
                'Humidifier': 1,
                'HumidifierorDehumidifier': 0
            }

        print("char_valid_values::::", char_valid_values)
        self.char_target_humidifier_dehumidifier = (serv_humidifier_dehumidifier.configure_char(
                CHAR_TARGET_HUMIDIFIER_DEHUMIDIFIER,
                value=self._hk_device_class,
                valid_values=char_valid_values
        ))

        # Current and target humidity characteristics
        self.char_current_humidity = serv_humidifier_dehumidifier.configure_char(
            CHAR_CURRENT_HUMIDITY, value=0
        )

        max_humidity = state.attributes.get(ATTR_MAX_HUMIDITY, DEFAULT_MAX_HUMIDITY)
        max_humidity = round(max_humidity)
        max_humidity = min(max_humidity, 100)

        min_humidity = state.attributes.get(ATTR_MIN_HUMIDITY, DEFAULT_MIN_HUMIDITY)
        min_humidity = round(min_humidity)
        min_humidity = max(min_humidity, 0)

        char_property = {
            PROP_MIN_VALUE: min_humidity,
            PROP_MAX_VALUE: max_humidity,
            PROP_MIN_STEP: 1,
            "unit": "percentage"
        }
        print("char_property::::::::", char_property)

        self.char_target_humidity = serv_humidifier_dehumidifier.configure_char(
            self._target_humidity_char_name,
            value=45,
            properties=char_property
        )

        # Active/inactive characteristics
        self.char_active = serv_humidifier_dehumidifier.configure_char(
            CHAR_ACTIVE, value=False
        )

        if device_class == DEVICE_CLASS_DEHUMIDIFIER:
            if CHAR_HUMIDIFIER_THRESHOLD_HUMIDITY in self.chars:
                self.char_humidifier_threshold_humidity = serv_humidifier_dehumidifier.configure_char(
                        CHAR_HUMIDIFIER_THRESHOLD_HUMIDITY,
                        properties=char_property
                )

            if CHAR_ROTATION_SPEED in self.chars:
                self.char_rotationspeed = serv_humidifier_dehumidifier.configure_char(
                        CHAR_ROTATION_SPEED,
                        properties={"minValue": 0.0, "maxValue": 100.0, "minStep": 33.3}
                )

            if CHAR_SWING_MODE in self.chars:
                self.char_swing_mode = serv_humidifier_dehumidifier.configure_char(
                        CHAR_SWING_MODE,
                        valid_values=PROP_SWING_MODE_VALID_VALUES
                )

            if CHAR_LOCK_PHYSICAL_CONTROLS in self.chars:
                self.char_lockphysicalcontrols = serv_humidifier_dehumidifier.configure_char(
                        CHAR_LOCK_PHYSICAL_CONTROLS,
                        valid_values=PROP_LOCK_PHYSICAL_VALID_VALUES
                )

        self.async_update_state(state)

        serv_humidifier_dehumidifier.setter_callback = self._set_chars

        print("self.config:::::")
        print(self.config)
        """
        {
            'manufacturer': 'Panasonic',
            'model': 'FYTW-05760121',
            'platform': 'taiseia_serial',
            'linked_humidity_sensor': 'sensor.taiseia_serial_totalwatt'
        }
        {
            'manufacturer': 'Panasonic',
            'model': 'FYTW-05760121',
            'platform': 'taiseia_serial',
            'linked_humidity_sensor': 'sensor.taiseia_serial_humidity'
        }
        """

        self.linked_humidity_sensor = self.config.get(CONF_LINKED_HUMIDITY_SENSOR)
        if self.linked_humidity_sensor:
            humidity_state = self.hass.states.get(self.linked_humidity_sensor)
            if humidity_state:
                self._async_update_current_humidity(humidity_state)

    async def run(self):
        """Handle accessory driver started event.

        Run inside the Home Assistant event loop.
        """
        if self.linked_humidity_sensor:
            self._subscriptions.append(
                async_track_state_change_event(
                    self.hass,
                    [self.linked_humidity_sensor],
                    self.async_update_current_humidity_event,
                )
            )

        await super().run()

    @callback
    def async_update_current_humidity_event(self, event):
        """Handle state change event listener callback."""
        self._async_update_current_humidity(event.data.get("new_state"))

    @callback
    def _async_update_current_humidity(self, new_state):
        """Handle linked humidity sensor state change to update HomeKit value."""
        if new_state is None:
            _LOGGER.error(
                "%s: Unable to update from linked humidity sensor %s: the entity state is None",
                self.entity_id,
                self.linked_humidity_sensor,
            )
            return
        try:
            current_humidity = float(new_state.state)
            if self.char_current_humidity.value != current_humidity:
                _LOGGER.debug(
                    "%s: Linked humidity sensor %s changed to %d",
                    self.entity_id,
                    self.linked_humidity_sensor,
                    current_humidity,
                )
                self.char_current_humidity.set_value(current_humidity)
        except ValueError as ex:
            _LOGGER.error(
                "%s: Unable to update from linked humidity sensor %s: %s",
                self.entity_id,
                self.linked_humidity_sensor,
                ex,
            )

    def _set_chars(self, char_values):
        _LOGGER.debug("HumidifierDehumidifier _set_chars: %s", char_values)
        print("char_values:::::", char_values)
        """
        {'Active': 0}
        {'Active': 1, 'TargetHumidifierDehumidifierState': 2}
        {'SwingMode': 1}
        {'RotationSpeed': 78}
        {'RotationSpeed': 57, 'Active': 1}
        """
        if self._target_humidity_char_name in char_values:
            humidity = round(char_values[self._target_humidity_char_name])
            self.async_call_service(
                DOMAIN,
                SERVICE_SET_HUMIDITY,
                {ATTR_ENTITY_ID: self.entity_id, ATTR_HUMIDITY: humidity},
                f"{self._target_humidity_char_name} to "
                f"{char_values[self._target_humidity_char_name]}{PERCENTAGE}",
            )

        if CHAR_TARGET_HUMIDIFIER_DEHUMIDIFIER in char_values:
            hk_value = char_values[CHAR_TARGET_HUMIDIFIER_DEHUMIDIFIER]
            print("self._hk_device_class::::::", self._hk_device_class)
            print("hk_value:::::", hk_value)
            if hk_value not in [HC_DEHUMIDIFIER, HC_HUMIDIFIER]:
                _LOGGER.error(
                        "%s is not supported: %s", CHAR_TARGET_HUMIDIFIER_DEHUMIDIFIER, hk_value
                )
            # if self._hk_device_class != hk_value:
            #     _LOGGER.error(
            #         "%s is not supported", CHAR_TARGET_HUMIDIFIER_DEHUMIDIFIER
            #     )

        if CHAR_ACTIVE in char_values:
            self.async_call_service(
                DOMAIN,
                SERVICE_TURN_ON if char_values[CHAR_ACTIVE] else SERVICE_TURN_OFF,
                {ATTR_ENTITY_ID: self.entity_id},
                f"{CHAR_ACTIVE} to {char_values[CHAR_ACTIVE]}",
            )

        if CHAR_SWING_MODE in char_values:
            print(f"do {CHAR_SWING_MODE}")
            # TODO: call custom service
            print(f"do {CHAR_SWING_MODE} end")

        if CHAR_ROTATION_SPEED in char_values:
            print(f"do {CHAR_ROTATION_SPEED}")
            self.async_call_service(
                    DOMAIN,
                    SERVICE_TURN_ON if char_values[CHAR_ACTIVE] else SERVICE_TURN_OFF,
                    {ATTR_ENTITY_ID: self.entity_id},
                    f"{CHAR_ACTIVE} to {char_values[CHAR_ACTIVE]}",
            )
            print(f"do {CHAR_ROTATION_SPEED} end")

        if CHAR_LOCK_PHYSICAL_CONTROLS in char_values:
            print(f"do {CHAR_LOCK_PHYSICAL_CONTROLS}")

    @callback
    def async_update_state(self, new_state):
        """Update state without rechecking the device features."""
        is_active = new_state.state == STATE_ON

        # Update active state
        self.char_active.set_value(is_active)

        # Set current state
        if is_active:
            if self._hk_device_class == HC_HUMIDIFIER:
                current_state = HC_STATE_HUMIDIFYING
            else:
                current_state = HC_STATE_DEHUMIDIFYING
        else:
            current_state = HC_STATE_INACTIVE
        self.char_current_humidifier_dehumidifier.set_value(current_state)

        # Update target humidity
        target_humidity = new_state.attributes.get(ATTR_HUMIDITY)
        if isinstance(target_humidity, (int, float)):
            self.char_target_humidity.set_value(target_humidity)

from .const import DOMAIN
import voluptuous as vol

from contextlib import suppress
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity, SensorDeviceClass
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from datetime import datetime

from .pyCitura.CituraAPI import CituraAPI

CONF_STOP_ID = "stopid"
CONF_NAME = "name"
CONF_ROUTE = "route"
DEFAULT_NAME = "next bus"
CONF_DIRECTION = "direction"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_STOP_ID): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_ROUTE): cv.string,
        vol.Required(CONF_DIRECTION): cv.string
    }
)


def setup_platform(
        hass: HomeAssistant,
        config: ConfigType,
        add_entities: AddEntitiesCallback,
        discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Setup the Citura sensor."""
    name = config[CONF_NAME]
    stop = config[CONF_STOP_ID]
    route = config[CONF_ROUTE]
    direction = config[CONF_DIRECTION]

    data = CituraAPI()
    entities = [CituraSensor(data, name, stop, route, direction)]

    # Return boolean to indicate that initialization was successful.
    add_entities(entities)


class CituraSensor(SensorEntity):
    """Implement the Citura Live sensor"""
    _attr_attribution = "Data provided by catp-reims.airweb.fr"
    _attr_icon = "mdi:bus"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, data, name, stop_name, route, direction) -> None:
        """Initialize the sensor."""
        self._name = name
        self._stop_name = stop_name
        self._route = route
        self._sens = direction
        self._data = data
        self._info = None
        self._state = None
        self._attr_unique_id = f"{self._stop_name}-{self._route}-{self._sens}-{self._name}"
        self._stop = self._data.getStationId(
            self._stop_name, self._route)[str(self._sens)][0]

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def native_value(self):
        """Return the next departure time."""
        return self._state

    def update(self) -> None:
        """Get the latest data and update the state."""
        self._info = self._data.getSIRI(
            line=self._route, stop_point=self._stop, count=3)

        self._state = datetime.fromisoformat(
            self._info['time'][0]['expected_time'])

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if self._info:
            ret = {
                'line': self._info['time'][0]['line'],
                'destination': self._info['time'][0]['destination'],
                'aimed_time': datetime.fromisoformat(self._info['time'][0]['aimed_time']),
                'status': self._info['time'][0]['status'],
                'realtime': self._info['time'][0]['realtime'],
            }
            if len(self._info['time']) > 1:
                ret['next_bus'] = datetime.fromisoformat(
                    self._info['time'][1]['expected_time'])
                ret['next_bus_status'] = self._info['time'][1]['status']
                ret['next_bus_realtime'] = self._info['time'][1]['realtime']
            if len(self._info['time']) > 2:
                ret['later_bus'] = datetime.fromisoformat(
                    self._info['time'][2]['expected_time'])
                ret['later_bus_status'] = self._info['time'][2]['status']
                ret['later_bus_realtime'] = self._info['time'][2]['realtime']
            return ret

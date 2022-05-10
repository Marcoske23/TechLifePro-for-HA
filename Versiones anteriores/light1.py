"""TechLife Pro Home Assistant Intergration"""
import paho.mqtt.client as mqtt
import colorsys
import logging

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
# Import the device class from the component that you want to support
from homeassistant.components.light import (SUPPORT_BRIGHTNESS,
    ATTR_BRIGHTNESS,ATTR_HS_COLOR, SUPPORT_COLOR, PLATFORM_SCHEMA, LightEntity)
from homeassistant.const import  (CONF_NAME)
import homeassistant.util.color as color_util

_LOGGER = logging.getLogger(__name__)

CONF_MAC_ADDRESS = 'mac_address'
CONF_BROKER_URL = 'broker_url'
CONF_BROKER_USERNAME = 'broker_username'
CONF_BROKER_PASSWORD = 'broker_password'
CONF_UNIQUE_ID = 'unique_id' #################################################################
_LOGGER.info('CONF_UNIQUE_ID: {}'.format(CONF_UNIQUE_ID))

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_UNIQUE_ID): cv.string, ###############################################
    vol.Required(CONF_MAC_ADDRESS): cv.string,
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_BROKER_URL): cv.string,
    vol.Required(CONF_BROKER_USERNAME): cv.string,
    vol.Required(CONF_BROKER_PASSWORD): cv.string,
})




async def async_setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Awesome Light platform."""
    # Assign configuration variables.
    # The configuration check takes care they are present.
    mac = config.get(CONF_MAC_ADDRESS)
    name = config.get(CONF_NAME)
    broker_url = config.get(CONF_BROKER_URL)
    broker_username = config.get(CONF_BROKER_USERNAME)
    broker_password = config.get(CONF_BROKER_PASSWORD)
    
    try:
        client = mqtt.Client(name)
        client.username_pw_set(broker_username, broker_password)

        client.connect(broker_url, 1883, 60)

    except:
        _LOGGER.info('No se pudo conectar')
        
        

    
    add_entities([TechlifeControl(mac, client, name,config)])    ##### kle agregué el async_
    client.loop_start()


class TechlifeControl(LightEntity):
    """Representation of an Awesome Light."""

    def __init__(self, mac, client, name, config):
        """Initialize an AwesomeLight."""
        self._unique_id = config.get(CONF_UNIQUE_ID)   #################### agregué esta línea
        _LOGGER.info('self._unique_id: {}'.format(self._unique_id))
        self.mac = mac
        self.client = client
        self._name = name
        self._state = False
        self._brightness = None
        self._color = None
        
    @property   #################### Agregué esta línea
    def unique_id(self): #################### Agregué esta línea
        _LOGGER.info('colocando nombre de uniqie_id')
        _LOGGER.info('unique_id: {}'.format(self._unique_id))
        """Return a unique ID.""" #################### Agregué esta línea
        return self._unique_id #################### Agregué esta línea


    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def brightness(self):
        """Return the brightness of the light.
        This method is optional. Removing it indicates to Home Assistant
        that brightness is not supported for this light.
        """
        return self._brightness
    @property
    def hs_color(self):
        return self._color

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state

    # @property
    # def assumed_state(self):
    #     return True

    @property
    def supported_features(self):
        return SUPPORT_BRIGHTNESS | SUPPORT_COLOR
    @property
    def device_state_attributes(self):
        """Return device attributes."""
        data = {
            'hs_color': self._color,
            'brightness': self._brightness
        }

    def turn_on(self, **kwargs):
        """Instruct the light to turn on.
        You can skip the brightness part if your light does not support
        brightness control.
        """
        if not self._state:
            self.on()
        self._state = True

        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]
        if self._brightness is None:
            self._brightness = 255
        if self._brightness is not None:
            brightness = self._brightness/2.55

        if ATTR_HS_COLOR in kwargs:
            self._color = kwargs[ATTR_HS_COLOR]
        if self._color is not None:
            self.color_hex(brightness)

    def color_hex(self,brightness):
        color = self._color
        brightness=int(brightness)
        rgb_1 = colorsys.hsv_to_rgb(color[0]/360,color[1]/100,1)
        rgb_255= tuple([255*x for x in rgb_1])
        #convierte a rgb 10000 con el valor de brillo
        red=int(rgb_1[0]*10000)
        green=int(rgb_1[1]*10000)
        blue=int(rgb_1[2]*10000)
        brightness_1=brightness/100
        red_br=int(rgb_1[0]*10000*brightness_1)
        green_br=int(rgb_1[1]*10000*brightness_1)
        blue_br=int(rgb_1[2]*10000*brightness_1)
        #Envia los colores RGB 10000 a enviar, pero primero pasa a que se actualice el payload
 
        self.send(self.update_color(red_br,green_br,blue_br,brightness))


    def turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        self.off()
        self._state = False


    def on(self):
        self.send(bytearray.fromhex(
            "fa 23 00 00 00 00 00 00 00 00 00 00 00 00 23 fb"))


    def off(self):
        self.send(bytearray.fromhex(
            "fa 24 00 00 00 00 00 00 00 00 00 00 00 00 24 fb"))

    def calc_checksum(self, stream):
        checksum = 0
        for i in range(1, 14):
            checksum = checksum ^ stream[i]
        stream[14] = checksum & 0xFF
        return bytearray(stream)

    def update_color(self,red,green,blue,brightness):
        _LOGGER.info('rodjo: {} verde: {} azul: {}'.format(red,green,blue,brightness))
        #Convierte los numeros rgb 10000 a hex y despues extrae sus valores
        brightness_hex=hex(brightness)
        payload = bytearray.fromhex("28 00 00 00 00 00 00 00 00 00 00 00 00 0f 00 29")
        payload[1]= red & 0xFF
        payload[2]= red >> 8
        payload[3]= green & 0xFF
        payload[4]= green >> 8
        payload[5]= blue & 0xFF
        payload[6]= blue >> 8       
        payload[11]= brightness & 0xFF
        return payload


    def send(self, cmd):
        command = self.calc_checksum(cmd)
        sub_topic = "dev_sub_%s" % self.mac
        result = self.client.publish(sub_topic, command)
        status= result [0]
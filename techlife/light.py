"""TechLife Pro Home Assistant Intergration"""
from http import client
import json
from typing import Callable
from unicodedata import name
from urllib import response
import logging
import binascii
import voluptuous as vol
import traceback


import homeassistant.helpers.config_validation as cv
# Import the device class from the component that you want to support

from homeassistant.components.light import (SUPPORT_BRIGHTNESS,
ATTR_BRIGHTNESS,
ATTR_HS_COLOR,
ATTR_RGB_COLOR,
SUPPORT_COLOR, 
PLATFORM_SCHEMA, 
LightEntity)


from homeassistant.const import  (CONF_NAME)
import homeassistant.util.color as color_util
_LOGGER = logging.getLogger(__name__)

CONF_MAC_ADDRESS = 'mac_address'
CONF_FRIENDLY_NAME = 'name'
CONF_BROKER_URL = 'broker_url'
CONF_BROKER_USERNAME = 'broker_username'
CONF_BROKER_PASSWORD = 'broker_password'
CONF_UNIQUE_ID = 'unique_id'



# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_UNIQUE_ID): cv.string,
    vol.Required(CONF_MAC_ADDRESS): cv.string,
    vol.Optional(CONF_FRIENDLY_NAME): cv.string,
    vol.Required(CONF_BROKER_URL): cv.string,
    vol.Required(CONF_BROKER_USERNAME): cv.string,
    vol.Required(CONF_BROKER_PASSWORD): cv.string,
})


_LOGGER.info("Iniciando TechLifev2")

def setup_platform(hass, config, add_entities: Callable, discovery_info=None):
    """Set up the Awesome Light platform."""
    # Assign configuration variables.
    # The configuration check takes care they are present.
    mac = config.get(CONF_MAC_ADDRESS)
    name = config.get(CONF_FRIENDLY_NAME)
    broker_url = config.get(CONF_BROKER_URL)
    broker_username = config.get(CONF_BROKER_USERNAME)
    broker_password = config.get(CONF_BROKER_PASSWORD)
    _LOGGER.info("Entrando en async_setup_platform")
    add_entities([TechlifeC(mac, client, name, config,broker_url,broker_password,broker_username)])    ##### Eliminar el True si algo sale mal

class TechlifeC(LightEntity):
    """Representation of an Awesome Light."""

    def __init__(self, mac, client, name, config,broker,password,username):
        """Initialize an AwesomeLight."""
        from .techlife import Techlife
        if config.get(CONF_UNIQUE_ID):
            self._unique_id = config.get(CONF_UNIQUE_ID)
        else:
            self._unique_id = 'tl_{}_{}'.format(broker,mac)   #################### agregué esta línea
        if name:
            self._name = name
        else:
            self._name='light_{}'.format(mac)
        self.hs=None
        self.brn=None
        self.features=None
        self.light=Techlife(
            mac,
            broker,
            username,
            password,
            True)
        self.light.connect_and_wait_until_ready()
    
    async def async_added_to_hass(self) -> None:
        self.light.color_statusEvents.subscribe(lambda _: self.schedule_update_ha_state())
        
    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state."""
        return False        
    @property   #################### Agregué esta línea
    def unique_id(self) -> str: #################### Agregué esta línea
        """Return a unique ID.""" #################### Agregué esta línea
        _LOGGER.info("@ ptopiety unique_id: %s -%s- " %(self._unique_id,self._name))
        return self._unique_id #################### Agregué esta línea
    @property
    def name(self) -> str:
        """Return the display name of this light."""
        _LOGGER.info("@ ptopiety name: %s -%s- " %(self._name,self._name))
        return self._name
    @property
    def is_on(self)-> bool:
        return self.light.is_on
    @property
    def available(self) -> bool:
        return self.light.is_available
    @property
    def color_mode(self) -> str:
        if self.light.type=='rgb':
            _LOGGER.debug('color_mode: hs')
            return 'hs'
        elif self.light.type=='w':
            _LOGGER.debug('color_mode: W')
            return 'brightness'
        else:
            return 'onoff'
    @property
    def supported_color_modes(self):
        if self.light.type=='rgb':
            _LOGGER.debug('SUPPORTED_color_mode: [hs,BRIGHTNESS]')
            return [ "hs", "brightness"]
        elif self.light.type=='w':
            _LOGGER.debug('SUPPORTED_color_mode: BRIGHTNESS')
            return ["brightness"]
        else:
            _LOGGER.debug('SUPPORTED_color_mode: ONOFF')
            return ['onoff']

    @property
    def brightness(self) -> int:
        if not self.light.is_available==True:
            return None
        if self.brn==None:
            if self.light.type=='rgb':
                return self.light.brn
            else:
                return self.light.brnw
        else:
            return self.brn
            
            
    @property
    def hs_color(self):
        if not self.light.is_available==True:
            return None
        if self.hs==None:
            return self.light.hs_color
        else:
            return self.hs

    def turn_on(self, **kwargs):
        _LOGGER.debug('Encendiendo tiras RGB: %s'%self._name)
        """Instruct the light to turn on.
        You can skip the brightness part if your light does not support
        brightness control.
        """
        _LOGGER.debug('kwargs: {}'.format(kwargs))
        if not self.is_on:
            return self.on()
            
        if ATTR_BRIGHTNESS in kwargs:
            self.brn = brightness = kwargs[ATTR_BRIGHTNESS]
        else:
            brightness = self.brightness
        if brightness is not None:
            brightness = brightness 

        if ATTR_HS_COLOR in kwargs:
            self.hs = color = kwargs[ATTR_HS_COLOR]
        else:
            color=self.hs_color
        #self.schedule_update_ha_state()
        _LOGGER.debug('hs_color: {}'.format(self.hs_color))
        _LOGGER.debug('rgb_color: {}'.format(self.rgb_color))
        _LOGGER.debug('color: {}'.format(color))
        rgb=(0,0,0)
        if color is not None:
            rgb=color_util.color_hs_to_RGB(color[0],color[1]) # Entrega el valor en escala de 255
        
        cjson={
            'type':self.light.type,
            'r':rgb[0],
            'g':rgb[1],
            'b':rgb[2],
            'brn':brightness
        }
        try:
            #Enviar color
            _LOGGER.debug('Color enviado desde light.py: {}'.format(cjson))
            self.light.run(color=cjson)
            #Solicitar update
            self.update()
        except Exception as err:
            _LOGGER.debug(traceback.format_exc())
            _LOGGER.debug('No se envió el comando')

    def update(self):
        _LOGGER.debug('Actualizando')
        self.light.run('fcf0000000000000000000000000f0fd')
    def turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        self.off()


    def on(self):
        #Encender
        self.light.run('fa2300000000000000000000000023fb')
        #Solicitar update
        self.update()
    def off(self):
        #Apagar
        self.light.run('fa2400000000000000000000000024fb')
        #Solicitar Update
        self.update()
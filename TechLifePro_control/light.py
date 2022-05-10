"""TechLife Pro Home Assistant Intergration"""
from http import client
from typing import Callable
from unicodedata import name
from urllib import response
import paho.mqtt.client as mqtt
import logging
import binascii
########
import time
from datetime import timedelta
#########
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
# Import the device class from the component that you want to support
from homeassistant.components.light import (SUPPORT_BRIGHTNESS,
    ATTR_BRIGHTNESS,ATTR_HS_COLOR, SUPPORT_COLOR, PLATFORM_SCHEMA, LightEntity)
from homeassistant.const import  (CONF_NAME)
import homeassistant.util.color as color_util
_LOGGER = logging.getLogger(__name__)

CONF_MAC_ADDRESS = 'mac_address'
CONF_FRIENDLY_NAME = 'name'
CONF_BROKER_URL = 'broker_url'
CONF_BROKER_USERNAME = 'broker_username'
CONF_BROKER_PASSWORD = 'broker_password'
CONF_UNIQUE_ID = 'unique_id'


SCAN_INTERVAL = timedelta(seconds=10)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_UNIQUE_ID): cv.string,
    vol.Required(CONF_MAC_ADDRESS): cv.string,
    vol.Required(CONF_FRIENDLY_NAME): cv.string,
    vol.Required(CONF_BROKER_URL): cv.string,
    vol.Required(CONF_BROKER_USERNAME): cv.string,
    vol.Required(CONF_BROKER_PASSWORD): cv.string,
})


_LOGGER.info("Iniciando TechLife")

async def async_setup_platform(hass, config, add_entities: Callable, discovery_info=None):
    """Set up the Awesome Light platform."""
    # Assign configuration variables.
    # The configuration check takes care they are present.
    mac = config.get(CONF_MAC_ADDRESS)
    name = config.get(CONF_FRIENDLY_NAME)
    broker_url = config.get(CONF_BROKER_URL)
    broker_username = config.get(CONF_BROKER_USERNAME)
    broker_password = config.get(CONF_BROKER_PASSWORD)
    _LOGGER.info("Entrando en async_setup_platform")
    try:
        _LOGGER.info("creando cliente")
        client = mqtt.Client(name)
        _LOGGER.info("Colocando cliente con servidor y contraseña")
        client.username_pw_set(broker_username, broker_password)
        _LOGGER.info("conectando")
        client.connect(broker_url, 1883, 30)
    except:
        _LOGGER.info("No se Conectó")

    _LOGGER.info("Creando entidades")
    add_entities([TechlifeControl(mac, client, name, config,broker_url,broker_password,broker_username)])    ##### Eliminar el True si algo sale mal

class TechlifeControl(LightEntity):
    """Representation of an Awesome Light."""

    def __init__(self, mac, client, name, config,broker_url,broker_password,broker_username):
        """Initialize an AwesomeLight."""
        _LOGGER.info("en techlifecontrol(lightentity)%s, %s"%(name,mac))
        #Son parte de propiety
        self._unique_id = config.get(CONF_UNIQUE_ID)   #################### agregué esta línea
        _LOGGER.info("_uniqueid: %s"%self._unique_id)
        self._name = name
        _LOGGER.info("_name: %s"%self._name)
        self._state = None
        _LOGGER.info("_state: %s"%self._state)
        self._brightness = None
        _LOGGER.info("_brightness: %s"%self._brightness)
        self._color = None
        _LOGGER.info("_color: %s"%self._color)
        self._available=False
        _LOGGER.info("_available: %s"%self._available)
        # No son parte de propiety
        self.mac=mac
        self.client = client
        self.broker_url=broker_url
        self.broker_username=broker_username
        self.broker_password=broker_password


        
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
    def brightness(self) -> int:
        """Return the brightness of the light.
        This method is optional. Removing it indicates to Home Assistant
        that brightness is not supported for this light.
        """
        _LOGGER.info("@ ptopiety brightness: %s -%s- " %(self._brightness,self._name))
        return self._brightness
    @property
    def hs_color(self):
        _LOGGER.info("@ ptopiety hs_color: %s -%s- " %(self._color,self._name))
        return self._color

    @property
    def is_on(self)-> bool:
        """Return true if light is on."""
        _LOGGER.info("@ ptopiety state: %s -%s- " %(self._state,self._name))
        return self._state

    @property
    def supported_features(self):
        return SUPPORT_BRIGHTNESS | SUPPORT_COLOR

    @property
    def available(self) -> bool:
        return self._available

    async def async_update(self):
        _LOGGER.info("En sincronizar propieties")
        def on_message(client, userdata, message):
            _LOGGER.info("Entrando a on_message: %s",self._name)
            try:
                msg = binascii.hexlify(message.payload)
                topic = message.topic
                _LOGGER.info("[ON_MESSAGE] Command received in topic %s: %s" %(topic, msg))
                if ((topic == "dev_pub_%s" % self.mac) and message.payload[0] == 0x11 and message.payload[22] == 0x22):
                    message_hex=message.payload.hex()
                    ############ actualizar state ###########
                    state_hex=message_hex[38:40]
                    if state_hex=="23":
                        self._state=True
                    elif state_hex=="24":
                        self._state=False
                    ############ actualizar RGB ###############
                    rgb_hex=(message_hex[4:6],message_hex[6:10],message_hex[10:14])
                    rgb_10k=(int(to_little(rgb_hex[0]),16),int(to_little(rgb_hex[1]),16),int(to_little(rgb_hex[2]),16))
                    rgb_255=tuple(x*255/10000 for x in rgb_10k)
                    hs=color_util.color_RGB_to_hs(rgb_255[0],rgb_255[1],rgb_255[2])
                    self._color=hs
                    ############ Actualizar brillo ###############
                    brightness_hex=message_hex[22:24]
                    brightness_100=int(brightness_hex,16)
                    brightness_255=brightness_100/100*255
                    self._brightness=brightness_255
                    _LOGGER.info("state: %s rgb: %s hs: %s" %(self._state,rgb_255,hs))
                    _LOGGER.info("Leyendo mensaje, terminando loop%s",self._name)
                    client.loop_stop()
                    client.disconnect()
            except Exception as e:
                _LOGGER.info('No se leyó el mensaje')

        def to_little(val):
            little_hex = bytearray.fromhex(val)
            little_hex.reverse()
            print("Byte array format:", little_hex)

            str_little = ''.join(format(x, '02x') for x in little_hex)
            return str_little

        def on_connect(client, obj, flags, rc):
            _LOGGER.info("Entrando a on_connmect %s",self._name)
            if rc==0:
                _LOGGER.info("[ON_CONNECT] Connected OK")
                client.subscribe("dev_pub_%s" % self.mac)
                client.subscribe("dev_sub_%s" % self.mac)
                response=bytearray.fromhex('fcf0000000000000000000000000f0fd')
                client.publish("dev_sub_%s"%self.mac,response)

            else:
                _LOGGER.info("[ON_CONNECT] Bad connection Returned code=%s",rc)

        try:
            _LOGGER.info('Actualizando Techlife: %s'%self._name)
            client = mqtt.Client("TechLife")
            _LOGGER.info('username de: %s'%self._name)
            client.username_pw_set(self.broker_username, self.broker_password)
            _LOGGER.info('on connect de: %s'%self._name)
            client.on_connect=on_connect #attach function to callback
            _LOGGER.info('on_message: %s'%self._name)
            client.on_message= on_message #attach function to callback
            _LOGGER.info('on_connect: %s'%self._name)
            client.connect(self.broker_url, 1883, 60)
            _LOGGER.info('Iniciando loop: %s'%self._name)
            client.on_connect = on_connect
            client.on_message = on_message
            startTime = time.time()
            waitTime = .1
            while True:
                    client.loop_start()
                    elapsedTime = time.time() - startTime
                    if elapsedTime > waitTime:
                        _LOGGER.info('Desconectando porque no hubo respuesta de: %s por %s segundos'%(self._name,elapsedTime))
                        client.loop_stop()
                        client.disconnect()
                        break
            if self._state!=None:
                self._available=True
        except:
            _LOGGER.info('No se pudo conectar')


    def turn_on(self, **kwargs):
        _LOGGER.info('Encendiendo tiras RGB: %s'%self._name)
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
            self.color_hex(brightness,self._color)

    def color_hex(self,brightness,color):
        color = color
        brightness=int(brightness)
        rgb_255 = color_util.color_hs_to_RGB(color[0],color[1])
        rgb_1=(rgb_255[0]/255,rgb_255[1]/255,rgb_255[2]/255)
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
        _LOGGER.info('payload: %s'%(bytearray.hex(payload)))
        return payload


    def send(self, cmd):
        command = self.calc_checksum(cmd)
        sub_topic = "dev_sub_%s" % self.mac
        try:
            _LOGGER.info("creando cliente")
            client = mqtt.Client(self.name)
            _LOGGER.info("Colocando cliente con servidor y contraseña")
            client.username_pw_set(self.broker_username, self.broker_password)
            _LOGGER.info("conectando")
            client.connect(self.broker_url, 1883, 30)
        except:
            _LOGGER.info("No se Conectó")
        #self.client.publish(sub_topic, command)
        client.publish(sub_topic, command)  #########borrar si es necesario
        _LOGGER.info('sub_topic: %s payload: %s'%(sub_topic,bytearray.hex(command)))




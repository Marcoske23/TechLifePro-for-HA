import hashlib
import logging
import time
from base64 import b64decode, b64encode
from collections import OrderedDict
from threading import Event
import threading
import sched
import random
import ssl
import requests
import stringcase
import os
import re
import homeassistant.util.color as color_util
import binascii
import traceback
import asyncio

from paho.mqtt.client import Client  as ClientMQTT
from paho.mqtt import publish as MQTTPublish
from paho.mqtt import subscribe as MQTTSubscribe

_LOGGER = logging.getLogger(__name__)

# These consts define all of the vocabulary used by this library when presenting various states and components.
# Applications implementing this library should import these rather than hard-code the strings, for future-proofing.
KNOW_ACTION = {
    'fcf0000000000000000000000000f0fd':'UPDATE',
    'fa2300000000000000000000000023fb':'ON',
    'fa2400000000000000000000000024fb':'OFF'
    
}

FEATURES ={
    'rgb':'SUPPORT_BRIGHTNESS | SUPPORT_COLOR',
    'w':'SUPPORT_BRIGHTNESS'
}
COLOR_MODE ={
    'rgb':'hs',
    'w':'brightness'
}
#class TechlifeAPI(self, mac=None):


class EventEmitter(object):
    """A very simple event emitting system."""
    def __init__(self):
        self._subscribers = []

    def subscribe(self, callback):
        listener = EventListener(self, callback)
        self._subscribers.append(listener)
        return listener

    def unsubscribe(self, listener):
        self._subscribers.remove(listener)

    def notify(self, event):
        for subscriber in self._subscribers:
            subscriber.callback(event)


class EventListener(object):
    """Object that allows event consumers to easily unsubscribe from events."""
    def __init__(self, emitter, callback):
        self._emitter = emitter
        self.callback = callback

    def unsubscribe(self):
        self._emitter.unsubscribe(self)

class Techlife():
    #def __init__(self, user, domain, resource, secret, vacuum, continent, server_address=None, monitor=False, verify_ssl=True):
    def __init__(self, mac,broker,username,password,monitor=True):

        # If True, the VacBot object will handle keeping track of all statuses,
        # including the initial request for statuses, and new requests after the
        # VacBot returns from being offline. It will also cause it to regularly
        # request component lifespans
        self._monitor = monitor

        self._failed_pings = 0

        # These three are representations of the vacuum state as reported by the API
        self.color_status = None
        self.hs_color=None
        self.rgb_color=None
        self.brn=None
        self.is_on=None
        self.is_available=None
        self.support_features=None
        self.brnw=None
        self.color_mode=None
        self.type=None

        self.broker_status = None
        #maybe i cant recive mode status like ranbow or similar
        self.mode_status=None

        self.color_statusEvents = EventEmitter()
        self.mode_statusEvents= EventEmitter()
        self.broker_statusEvents= EventEmitter()
    

        # Ponerle para que entre como MQTT
        #self.iotmq = EcoVacsIOTMQ(user, domain, resource, secret, continent, vacuum, server_address, verify_ssl=verify_ssl)
        #self.iotmq.subscribe_to_ctls(self._handle_ctl)
        self.iotmq = lightIOTMQ(mac,broker,username,password)
        #Def para decibir mensajes, quiza no sirva en este caso
        self.iotmq.subscribe_to_ctls(self._handle_ctl)

 

    def connect_and_wait_until_ready(self):
        _LOGGER.debug('*** Conectando ***')
        self.iotmq.connect_and_wait_until_ready()
        _LOGGER.debug ('*** Conectado ***')

        self.iotmq.schedule(30, self.send_ping)
        self.iotmq.schedule(30, self.refresh_state)
        if self._monitor:
            _LOGGER.debug('***Enviando primer ping***')
            # Do a first ping, which will also fetch initial statuses if the ping succeeds
            self.send_ping()
            self.refresh_state()
            _LOGGER.debug ('*** Enviando mensaje de estatus de la entidad ***')
            self.iotmq.schedule(3600,self.refresh_state)

    def _handle_ctl(self, ctl):
        method = '_handle_' + ctl['event']
        if hasattr(self, method):
            getattr(self, method)(ctl)
            
        
    def _handle_color(self, event):
        self.color_status=event
        if 'is_on' in event:
            self.is_on=event['is_on']
        if 'is_available' in event:
            self.is_available=event['is_available']
        if 'hs' in event:
            self.hs_color=event['hs']
        if 'brn' in event:
            self.brn=event['brn']
        if 'type' in event:
            self.type=event['type']
            try:
                self.support_features=FEATURES[type]
                self.color_mode=COLOR_MODE[type]
            except KeyError:
                self.support_features=None
            
        if 'brnw' in event:
            self.brnw=event['brnw']
        self.color_statusEvents.notify(self.color_status)
        self.broker_status = 'online'
        self.broker_statusEvents.notify(self.broker_status)
        _LOGGER.debug("broker_Status: {}".format(self.broker_status))
            
        #if 'speed' in event:
        #    _LOGGER.debug("Handle get clean speed: " + str(event))

        #    self.fan_speed = FAN_SPEED_FROM_ECOVACS[event['speed']]
        #    self.fanEvents.notify(self.fan_speed)

    def send_ping(self):
        try:
            if not self.iotmq.send_ping():
                raise RuntimeError()
            else:
                self.broker_status = 'online'
                self.broker_statusEvents.notify(self.broker_status)

        except RuntimeError as err:
            _LOGGER.warning("Ping did not reach TechLife. Will retry.")
            self._failed_pings += 1
            if self._failed_pings >= 4:
                self.broker_status = 'offline'
                self.broker_statusEvents.notify(self.broker_status)
                self.is_available_status=False
                self.is_availableEvents.notify(self.is_available_status)
                

        else:
            self._failed_pings = 0
                # If we don't yet have a vacuum status, request initial statuses again now that the ping succeeded
            if self.broker_status == 'offline' or self.broker_status is None:
                _LOGGER.debug("broker_Status: {}".format(self.broker_status))
                _LOGGER.debug("enviando primera actualizacion mensaje")
                self.refresh_state()

    def refresh_state(self):
        _LOGGER.debug ('*** Enviando mensaje en refresh_state ***')
        try:
            self.run('fcf0000000000000000000000000f0fd')
            _LOGGER.debug('Mensaje de actualización enviado')
        except: #Exception as err:
            #_LOGGER.debug(traceback.format_exc())
            _LOGGER.debug('No se envío el mensaje de actualización')
            pass
        
            

    def send_command(self, action,color):
        self.iotmq.send_command(action,color)  #IOTMQ devices need the full action for additional parsing

    def run(self, action=None, color={}):
        self.send_command(action,color)

    def disconnect(self, wait=False):
        if not self.vacuum['iotmq']:
            self.xmpp.disconnect(wait=wait)
        else:
            self.iotmq._disconnect()
            #self.xmpp.disconnect(wait=wait) #Leaving in case xmpp is added to iotmq in the future                   

#This is used by EcoVacsIOTMQ and EcoVacsXMPP for _ctl_to_dict
def RepresentsInt(stringvar):
    try: 
        int(stringvar)
        return True
    except ValueError:
        return False

class lightIOTMQ(ClientMQTT):
    
    def __init__(self, mac,broker,username,password):
    #def __init__(self, user, domain, resource, secret, continent, vacuum, server_address=None, verify_ssl=True):
        ClientMQTT.__init__(self)
        self.ctl_subscribers = []        
        self.mac = mac
        self.broker = broker
        self.username = username
        self.password = password
        self.scheduler = sched.scheduler(time.time, time.sleep)
        self.scheduler_thread = threading.Thread(target=self.scheduler.run, daemon=True, name="mqtt_schedule_thread")
        self.message=None
        self.send_echo=echo(mac,broker)

#        self._client_id = self.user + '@' + self.domain.split(".")[0] + '/' + self.resource        
        self.username_pw_set(self.username, self.password)

        self.ready_flag = Event()

    def connect_and_wait_until_ready(self):        
        #self._on_log = self.on_log #This provides more logging than needed, even for debug
        self._on_message = self._handle_ctl_mqtt
        self._on_connect = self.on_connect     
        self.connect(self.broker, 1883, 60)
        self.loop_start()        
        self.wait_until_ready()

    def subscribe_to_ctls(self, function):
        self.ctl_subscribers.append(function)   

    def _disconnect(self):
        self.disconnect() #disconnect mqtt connection
        self.scheduler.empty() #Clear schedule queue  

    def _run_scheduled_func(self, timer_seconds, timer_function):
        timer_function()
        self.schedule(timer_seconds, timer_function)

    def schedule(self, timer_seconds, timer_function):
        self.scheduler.enter(timer_seconds, 1, self._run_scheduled_func,(timer_seconds, timer_function))
        if not self.scheduler_thread.is_alive():
            self.scheduler_thread.start()
        
    def wait_until_ready(self):
        self.ready_flag.wait()

    def on_connect(self, client, userdata, flags, rc):        
        if rc != 0:
            _LOGGER.error("EcoVacsMQTT - error connecting with MQTT Return {}".format(rc))
            raise RuntimeError("EcoVacsMQTT - error connecting with MQTT Return {}".format(rc))
                 
        else:
            _LOGGER.debug("EcoVacsMQTT - Connected with result code "+str(rc))
            _LOGGER.debug("EcoVacsMQTT - Subscribing to all")       
            pub = "dev_pub_%s" % self.mac
            sub = "dev_sub_%s" % self.mac
            self.subscribe(pub)
            self.subscribe(sub)
            self.ready_flag.set()

    #def on_log(self, client, userdata, level, buf): #This is very noisy and verbose
    #    _LOGGER.debug("EcoVacsMQTT Log: {} ".format(buf))
   
    def send_ping(self):
        _LOGGER.debug("*** MQTT sending ping ***")
        rc = self._send_simple_command(MQTTPublish.paho.PINGREQ)
        if rc == MQTTPublish.paho.MQTT_ERR_SUCCESS:
            _LOGGER.debug("*** Ping Recibido ***")
            return True         
        else:
            _LOGGER.debug("*** Ping Rechazado ***")
            return False

    def send_command(self, action=None,color={}):
        #Si es un comando conocido
        a=None
        if action in KNOW_ACTION:
            try:
                a=KNOW_ACTION[action]
            except KeyError:
                a=action
            _LOGGER.debug('Enviando mensaje de: {}'.format(a))
            action=bytearray.fromhex(action)
            _LOGGER.debug('action: {}'.format(action))
        else:
            if not 'type' in color:
                _LOGGER.debug('No se sabe qué tipo de iluminación es')
            if 'type' in color:
                if color['type'] == 'rgb':
                    #Rojo de 255 a 10000
                    r=int(color['r'])/255*10000
                    #Verde de 255 a 10000
                    g=int(color['g'])/255*10000
                    #Azul de 255 a 10000
                    b=int(color['b'])/255*10000
                    #Intensidad en 100
                    brn=int(color['brn'])
                    
                    _LOGGER.debug('r: {} g: {} b: {} brn:{}'.format(r,g,b,brn))
                    #Convierte los numeros rgb 10000 a hex y despues extrae sus valores
                    brightness=brn/255
                    brn_100=brightness*100
                    brn_100=int(brn_100)
                    _LOGGER.debug('brightness:{}'.format(brightness))
                    red=r*brightness
                    _LOGGER.debug('red:{}'.format(red))
                    red=int(red)
                    green=g*brightness
                    _LOGGER.debug('green:{}'.format(green))
                    green=int(green)
                    blue=b*brightness
                    _LOGGER.debug('blue:{}'.format(blue))
                    blue=int(blue)
                    _LOGGER.debug('rojo: {} verde: {} azul: {} brn:{}'.format(red,green,blue,brn_100))
                    payload = bytearray.fromhex("28 00 00 00 00 00 00 00 00 00 00 00 00 0f 00 29")
                    
                    payload[1]= red & 0xFF
                    payload[2]= red >> 8
                    payload[3]= green & 0xFF
                    payload[4]= green >> 8
                    payload[5]= blue & 0xFF
                    payload[6]= blue >> 8       
                    payload[11]= brn_100 & 0xFF
                    print("Payload para cambiar de color: %s"%payload)
                    action = self.calc_checksum(payload)
                if color['type'] == 'w':
                    #Brillo en 100
                    brightness=int(color['brn'])*100
                    assert 0 <= value <= 10000
                    payload = bytearray.fromhex(
                        "28 00 00 00 00 00 00 00 00 00 00 00 00 f0 00 29")
                    payload[7] = value & 0xFF
                    payload[8] = value >> 8
                    action = self.calc_checksum(payload)
                _LOGGER.debug('Enviando mensaje de color con: {}'.format(action))
                    
        self.publish("dev_sub_%s" % self.mac, action)
        
        if a=='UPDATE':
            asyncio.run(self.wait_until_message())
##########################
    async def wait_until_message(self):
        self.message='send'
        timeout = time.time() + 3
        while True:
            
            if self.message=='re':
                break
            elif time.time() > timeout:
                as_dict={
                    'is_available':False,
                    'is_on':False,
                    'rgb':None,
                    'hs':None,
                    'event':'color'
                }
                if as_dict is not None:
                    for s in self.ctl_subscribers:
                        s(as_dict)
                break
    
##########################            
            
            
                
                
    def calc_checksum(self, stream):
        checksum = 0
        for i in range(1, 14):
            checksum = checksum ^ stream[i]
        stream[14] = checksum & 0xFF
        return bytearray(stream)
            

    def _handle_ctl_mqtt(self, client, userdata, message):
        _LOGGER.debug("Techlife MQTT Received Message on Topic: {} - Message: {}".format(message.topic, binascii.hexlify(message.payload)))
        
        as_dict = self._ctl_to_dict_mqtt(message)
        if as_dict is not None:
            for s in self.ctl_subscribers:
                s(as_dict)

    def _ctl_to_dict_mqtt(self, message):
        
        _LOGGER.info("Entrando a on_message: {}".format(message))
        try:
            msg = binascii.hexlify(message.payload)
            topic = message.topic
            _LOGGER.info("[ON_MESSAGE] Command recivido en topic %s: %s" %(topic, msg))
            result={'type':None,
            'rgb':None,
            'hs':None,
            'rgbw':None,
            'rgbww':None,
            'brn':None,
            'brnw':None,
            'is_on':None,
            'is_available':None,
            'event':None
            }
            if (topic == "dev_sub_%s" % self.mac):
                _LOGGER.debug('Comando enviado')
            if ((topic == "dev_pub_%s" % self.mac) and message.payload[0] == 0x11 and message.payload[22] == 0x22):
                message_hex=message.payload.hex()
                self.message='re'
                _LOGGER.debug('Status recibido: {}'.format(message_hex))
                if message.payload[12]== 0x01:
                    result['type']='w'
                if message.payload[12]==0x00:
                    result['type']='rgb'
                ############ actualizar state ###########
                state_hex=message_hex[38:40]
                if state_hex=="23":
                    result['is_on']=True
                    result['is_available']=True
                elif state_hex=="24":
                    result['is_on']=False
                    result['is_available']=True
                ############ actualizar RGB ###############
                rgb_hex=(message_hex[2:6],message_hex[6:10],message_hex[10:14])
                rgb_10k=(int(self.to_little(rgb_hex[0]),16),int(self.to_little(rgb_hex[1]),16),int(self.to_little(rgb_hex[2]),16))
                rgb_255=tuple(x*255/10000 for x in rgb_10k)
                hs=color_util.color_RGB_to_hs(rgb_255[0],rgb_255[1],rgb_255[2])
                result['rgb']=rgb_255
                result['hs']=hs
                ############ Actualizar brillo de RGB###############
                brightness_hex=message_hex[22:24]
                _LOGGER.debug('Brightness_hex: {}'.format(brightness_hex))
                brightness_100=int(brightness_hex,16)
                _LOGGER.debug('Brightness_100: {}'.format(brightness_100))
                brightness_255=brightness_100*2.55
                _LOGGER.debug('Brightness_255: {}'.format(brightness_255))
                result['brn']=brightness_255
                result['event']='color'
                _LOGGER.debug('Datos de result: {}'.format(result))
                ############ Actualizar brillo de WW ##############
                brightness_hex=message_hex[16:20]
                brightness_10k=int(self.to_little(brightness_hex),16)
                brightness_255=brightness_10k/10000*255
                result['brnw']=brightness_255
                return result
        except Exception as err:
            _LOGGER.debug(traceback.format_exc())
            _LOGGER.info('No se leyó el mensaje')

    def to_little(self,val):
        little_hex = bytearray.fromhex(val)
        little_hex.reverse()
        print("Byte array format:", little_hex)

        str_little = ''.join(format(x, '02x') for x in little_hex)
        return str_little
        
class echo():
    def __init__(self,mac,broker):
        self.mqttServerIp = broker #Your mqttserver
        self.bulbMacAddress = mac #Macaddress of light in your network
    
    ###############################################
    
    def calcChecksum(self,stream):
      checksum = 0
      for i in range(1, 14):
          checksum = checksum ^ stream[i]
      stream[14] = checksum & 255
    
      return bytearray(stream)
    
    
    def changeIP (self, ipAddr, port):
      Command = bytearray.fromhex("AF 00 00 00 00 00 00 f0 00 00 00 00 00 00 00 b0")
      l = list(Command)
      idx = 1
      for ip in map(int,ipAddr.split('.')):
          l[idx] = ip
          idx = idx + 1
      l[5] = port & 0xff
      l[6] = port >> 8
      return self.calcChecksum(l)
      
    def cmd(self):
        text = '\\x' + '\\x'.join(format(x, '02x') for x in self.changeIP(self.mqttServerIp,1883))
        cmd1 = 'echo -en "{}" | mosquitto_pub -t "dev_sub_{}" -h "cloud.qh-tek.com" -s'.format(text,self.bulbMacAddress.lower())
        cmd2 = 'echo -en "{}" | mosquitto_pub -t "dev_sub_{}" -h "cloud.hq-tek.com" -s'.format(text,self.bulbMacAddress.lower())
        os.system(cmd1)
        os.system(cmd2)
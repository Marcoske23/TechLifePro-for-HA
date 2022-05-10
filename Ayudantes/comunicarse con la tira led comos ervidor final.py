from ast import Num
import paho.mqtt.client as mqtt
import time
import binascii
import traceback
import struct
i=0
mac = '62:17:d2:ec:70:98'
broker_url = '192.168.50.4'
broker_username = 'mqttuser'
broker_password = 'mqttpassword'
state=""


def on_connect(client, obj, flags, rc):
    if rc==0:
        print("[ON_CONNECT] Connected OK")
        client.subscribe("dev_pub_%s" % mac)
        client.subscribe("dev_sub_%s" % mac)
        response=bytearray.fromhex('fcf0000000000000000000000000f0fd')
        client.publish("dev_sub_%s"%mac,response)
    else:
        print("[ON_CONNECT] Bad connection Returned code=%s",rc)

def on_disconnect(client, userdata, rc):
    print("[ON_DISCONNECT] disconnecting reason  "  +str(rc))
    client.connected_flag=False
    client.disconnect_flag=True

def on_log(client, userdata, level, buff):
    print("[ON_LOG]: %s" % buff)

def to_little(val):
  little_hex = bytearray.fromhex(val)
  little_hex.reverse()
  print("Byte array format:", little_hex)

  str_little = ''.join(format(x, '02x') for x in little_hex)

  return str_little

def on_message(client, userdata, message):
    try:
        msg = binascii.hexlify(message.payload)
        topic = message.topic
        print("[ON_MESSAGE] Command received in topic %s: %s" % (topic, msg))
        if ((topic == "dev_pub_%s" % mac) and message.payload[0] == 0x11 and message.payload[22] == 0x22):
            message_hex=message.payload.hex()
            state_hex=message_hex[38:40]
            if state_hex=="23":
                state="on"
            elif state_hex=="24":
                state="off"
            else:
                state="unavailable"
            print("state= %s "%(state))
            red_hex=message_hex[2:6]
            green_hex=message_hex[6:10]
            blue_hex=message_hex[10:14]
            
            print("red: %s green: %s blue: %s"%(red_hex,green_hex,blue_hex))
            red=int(to_little(red_hex),16)
            green=int(to_little(green_hex),16)
            blue=int(to_little(blue_hex),16)
            red_255=int(red*255/10000)
            green_255=int(green*255/10000)
            blue_255=int(blue*255/10000)
            print("red: %s green: %s blue: %s"%(red,green,blue))
            print("red255: %s green255: %s blue255: %s"%(red_255,green_255,blue_255))
            rgb=(red_255,green_255,blue_255)
            color_hex=''.join(["%0.2X" % c for c in rgb])
            print(color_hex)
            #response = bytearray.fromhex("110000000000003f0d000000014100ffffff1524f14d22")
            #response = bytearray.fromhex("111027000000000000000064004100FFFFFF1623F32B22")
            #response1=bytearray.fromhex('cc0f0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000fdd')
            #client.publish("dev_sub_%s" % mac, response1)
            #response2=bytearray.fromhex('b0e6070507160d3606f00000000038b1')
            #client.publish("dev_sub_%s" % mac, response2)
    except Exception as e:
        traceback.print_exc()
############### MAIN #########################

print("Start")

client=mqtt.Client("PRUEBA")
client.username_pw_set(broker_username,broker_password)

print("entra a on_message")
print("entra a on_connect")
client.on_connect=on_connect #attach function to callback
client.on_message=on_message #attach function to callback

print("state: ", state)
print("conectando")
client.connect(broker_url,1883,60)


while True:
    print("Entrando a bucle")
    try:
        print("loop_forever")
        
        i=i+1
        print("i: ",i)
        client.loop_forever()
    except KeyboardInterrupt:
        client.disconnect()
        exit(0)
    except:
        raise
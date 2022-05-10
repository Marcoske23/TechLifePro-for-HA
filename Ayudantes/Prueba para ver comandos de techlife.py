import paho.mqtt.client as mqtt
import time
import binascii
import traceback

bulb_mac = '62:17:d2:ec:70:98'
mqtt_server = "cloud.qh-tek.com"
mqtt_user = 'testuser'
mqtt_pass = 'testpass'

def on_connect(client, obj, flags, rc):
    if rc==0:
        print("[ON_CONNECT] Connected OK")
        client.subscribe("dev_pub_%s" % bulb_mac)
        client.subscribe("dev_sub_%s" % bulb_mac)
    else:
        print("[ON_CONNECT] Bad connection Returned code=%s",rc)

def on_disconnect(client, userdata, rc):
    print("[ON_DISCONNECT] disconnecting reason  "  +str(rc))
    client.connected_flag=False
    client.disconnect_flag=True

def on_log(client, userdata, level, buff):
    print("[ON_LOG]: %s" % buff)

def on_message(client, userdata, message):
    try:
        msg = binascii.hexlify(message.payload)
        topic = message.topic
        print("[ON_MESSAGE] Command received in topic %s: %s" % (topic, msg))
        print(((msg[1]<<8)+msg[2]))
        if ((topic == "dev_sub_%s" % bulb_mac) and message.payload[0] == 0xfc and message.payload[1] == 0xf0):
            #response = bytearray.fromhex("110000000000003f0d000000014100ffffff1524f14d22")
            print("azul")
            response = bytearray.fromhex("110000000010270000000026004100ffffff1623f36922")
            client.publish("dev_pub_%s" % bulb_mac, response)
    except Exception as e:
        traceback.print_exc()
############### MAIN #########################

print("Start")
client = mqtt.Client("clientid%s" % bulb_mac) #create new instance
client.on_message=on_message #attach function to callback
client.on_connect=on_connect #attach function to callback
#client.on_log=on_log

print("Connecting to broker")
if mqtt_user:
    client.username_pw_set(mqtt_user, password=mqtt_pass)

client.connect(mqtt_server) #connect to broker


while True:
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        client.disconnect()
        exit(0)
    except:
        raise
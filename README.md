# TechLife Bulb - Custom Integration
This light integration controls your techlife RGB lights without flashing or modifying.
Actually im working to integrate for white lights.
Note: TechLife Pro only support send messages and cannot sub for obtain the actual state of the light.


## Requirements:
In order to make the light (or lights) work you will need to:
1. Copy this repository in Custom_Components in Home Assistant
  ```
/config/custom_components/TechLife
  ```
2. Connect the bulbs to your wifi (Using app or custom script)
You can connect the light bulb to your 2.4GHz Wifi network wiuthout install the TechLife app to do this. The app is poorly designed and does not work most of the time. Instead, follow these simple steps.

Modify the following variables in the excellent Python script included below (taken from here 31)

ssid : Your 2.4GHz Wifi network’s SSID
password : Your 2.4GHz Wifi network’s password
bssid : Your 2.4GHz Wifi network’s BSSID (MAC address) written as a byte array
Screw in the light bulb and turn it on

Connect to the Wifi network created by the light bulb

Execute the Python script

At this point, the bulb will reboot, connect to your Wifi network, and automatically start listening for MQTT commands.

Take note of the output that the script spits out; this is your light bulb’s MAC address, which you’ll need for the next steps.

TechLifePro_Setup.py:
  ```
#!/usr/bin/env python
# 1. Modify the variables according to your setup: ssid, password, bssid, [email]
# 2. Connect the computer to AP-TechLife-xx-xx SSID
# 3. Run the script
import socket

# Variables to change
ssid = 'YOURSSID'
password = 'WIFIPASSWORD'
bssid = bytearray([0xaa, 0xaa, 0xaa, 0xaa, 0xaa, 0xaa]) # Enter your WiFi router's WiFi interface MAC address in hex (eg. AA:AA:AA:AA:AA:AA)
email = 'none@nowhere.com' # not absolutely required

# The bulb's network details
TCP_IP = '192.168.66.1'
TCP_PORT = 8000
BUFFER_SIZE = 1024

# Initialize Payload
payload = bytearray(145)
payload[0x00] = 0xff
payload[0x69] = 0x01

# Add the SSID to the payload
ssid_start = 0x01
ssid_length = 0
for letter in ssid:
    payload[(ssid_start + ssid_length)] = ord(letter)
    ssid_length += 1

# Add the WiFi password to the payload
pass_start = 0x22
pass_length = 0
for letter in password:
    payload[(pass_start + pass_length)] = ord(letter)
    pass_length += 1

# Add the BSSID to the payload
bssid_start = 0x63
bssid_length = 0
for digit in bssid:
    payload[(bssid_start + bssid_length)] = digit
    bssid_length += 1

# Add the email to the payload
email_start = 0x6a
email_length = 0
for letter in email:
    payload[(email_start + email_length)] = ord(letter)
    email_length += 1

checksum = 0
j = 1
while j < 0x8f:
   checksum = (payload[j] ^ checksum)
   checksum = checksum & 0xff
   j += 1

payload[0x8e] = 0xf0
payload[0x8f] = checksum & 0xff
payload[0x90] = 0xef

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((TCP_IP, TCP_PORT))
s.send(payload)
data = s.recv(BUFFER_SIZE)
s.close()
print ("received data:", data)
```
3. Create an user in your HA called `testuser` with password `testpassword`
4. Redirect bulb traffic to your custom mqtt server redirecting dns entries:

  Option 1: using **dnsmasq** inside HA with this configuration:
  ``` yaml
    hosts:
      - host: cloud.qh-tek.com
        ip: 192.168.0.0 #brokerip
      - host: cloud.hq-tek.com
        ip: 192.168.0.0 #brokerip
  ```
  Option2: Using this Pythion Script
  The TechLife Pro light bulbs are configured to listen to a specific MQTT topic on one of two specific external domains. We therefore need to instruct the light bulbs to listen to your server instead.

Using a Python 2.7 compiler (either on your computer, or using an online service such as this one https://www.tutorialspoint.com/execute_python_online.php ), run the following script, replacing the values in the first two lines with the appropriate values in your case.
  ```
mqttServerIp = '10.0.1.11' #Your mqttserver
bulbMacAddress = 'aa:bb:cc:dd:ee:ff' #Macaddress of light in your network

###############################################

def calcChecksum(stream):
    checksum = 0
    for i in range(1, 14):
        checksum = checksum ^ stream[i]
    stream[14] = checksum & 255

    return bytearray(stream)


def changeIP (ipAddr, port):
    Command = bytearray.fromhex("AF 00 00 00 00 00 00 f0 00 00 00 00 00 00 00 b0")
    l = list(Command)
    idx = 1
    for ip in map(int,ipAddr.split('.')):
        l[idx] = ip
        idx = idx + 1
    l[5] = port & 0xff
    l[6] = port >> 8
    return calcChecksum(l)
    
command = '\\x' + '\\x'.join(format(x, '02x') for x in changeIP(mqttServerIp,1883))

print 'echo -en "' + command + '" | mosquitto_pub -t "dev_sub_' + bulbMacAddress.lower() + '" -h "cloud.qh-tek.com" -s'
print 'echo -en "' + command + '" | mosquitto_pub -t "dev_sub_' + bulbMacAddress.lower() + '" -h "cloud.hq-tek.com" -s'
  ```

The result should be something like this:
  ```
echo -en "\xaf\x0a\x00\x01\x0b\x5b\x07\xf0\x00\x00\x00\x00\x00\x00\xac\xb0" | mosquitto_pub -t "dev_sub_aa:bb:cc:dd:ee:ff" -h "cloud.qh-tek.com" -s
echo -en "\xaf\x0a\x00\x01\x0b\x5b\x07\xf0\x00\x00\x00\x00\x00\x00\xac\xb0" | mosquitto_pub -t "dev_sub_aa:bb:cc:dd:ee:ff" -h "cloud.hq-tek.com" -s
  ```
Copy/paste these two lines on the command line and execute them; at least one of them should be successful. This tells the overseas MQTT server to instruct the bulb to use your local MQTT server from now on.

The bulb should flash once after a few seconds to confirm that it has received the command.

5.- Restart your Home Assistant
Once you have restarted, the custom_component will be available in your system (check home_assistant.log) so now you can configure your lights folowing the
6.- Create new light in   ``` light.yaml   ``` with this configuration

## Example Configuration

Example configuration to create an entity called `light.yourbulb`.

``` yaml
light: 
    - platform: techlife_bulb_control
      mac_address: "00:00:00:00:00:00" # Get this from your router in my case lights have this name: lwipr91h_sta
      name: "YourBulb"
      broker_url: 192.168.0.0
      broker_username: !secret broker_username
      broker_password: !secret broker_password
```

## Credits and Info
I used information following this articles and forum posts. All credits all credit to this people who have extracted all the commands needed to change bulbs state. I only packed all in this custom_component.

- Original Post: https://community.home-assistant.io/t/integrating-techlife-pro-light-bulbs-without-opening-or-soldering/178423


- mqqt messages to change lights: https://community.openhab.org/t/hacking-techlife-pro-bulbs/85940


- Base Doc for custom_component: https://github.com/home-assistant/example-custom-config/blob/master/custom_components/example_light

- Custom component for TechLife Bulb (Support only on/off and dim): https://github.com/thorin8k/techlife_bulb







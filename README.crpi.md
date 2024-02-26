# Picframe installation and customization for my own Raspberry Pi


# OS installation
## OS version
The latest OS version supported by the picframe is Buster. An ISO image is stored on 
the NAS, under `/volume1/backup/picframe`. 

## Disabling low voltage warning
1. Add the line below to the `/boot/config.txt` file:
```
avoid_warnings=1
```
1. Remove the battery monitor plugin:
```
sudo apt remove lxplug-ptbatt
```
1. Reboot




## Picframe data
### Pictures
The pictures go in `/mnt/Pictures`.

### Configuration
On the raspberry Pi, the configuration files go in `/mnt/picframe_data`.
In this repository the configuration data is in the directory: `cristian_config`.
The `runPicframe.sh` script is in the `linuxenv` repository.

### Autostart
The autostart script for picframe (`picframe.desktop`):
* is in the `cristian_config` directory
* goes to `~/.config/autostart`


## Mosquitto MQTT broker
### General
Documentation: https://mosquitto.org/documentation/
Configuration dir: `/etc/mosquitto`
Passwords:
* are stored in the VeraCrypt file in the `picframe` directory
* go in: `/etc/mosquitto/conf.d/passwords`



### Sheely controls
Topic: `/shellies`
Shelly button: /shellies/button_pic_frame/input_event

Shelly motion 

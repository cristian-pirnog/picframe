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

# Development enviroment
For setting up the development environment follow the steps below, then use the created environment in e.g. VSCode.
```
python -m venv .venv  # Create a virtual environment in .venv dir
source .venv/bin/activate
pip install -r requirements.txt
```

# Picframe data
## Pictures
The pictures go in `/mnt/Pictures`.

## Configuration
On the raspberry Pi, the configuration file is stored in the Git repository under `cristian_config`. All the other files
are taken directly from the repository.
The `runPicframe.sh` script is in the `linuxenv` repository.


# Autostart
## Run as a systemd service
1. `sudo su`
1. Copy the files from the `systemd` directory of this repo into `/etc/systemd/system`.
1. Run the command `systemctl enable picframe`
1. Reboot

## Old way
The autostart script for picframe (`picframe.desktop`):
* is in the `cristian_config` directory
* goes to `~/.config/autostart`


# Mosquitto MQTT broker
## General
Documentation: https://mosquitto.org/documentation/
Configuration dir: `/etc/mosquitto`
Passwords:
* are stored in the VeraCrypt file in the `picframe` directory
* go in: `/etc/mosquitto/conf.d/passwords`


# Sheely controls
## General
Topic: `/shellies`
Shelly button: /shellies/button_pic_frame/input_event
Shelly motion:  

## Setting up MQTT
This goes for the devices from the first generation (at least, for Shelly Motion 1)
1. Connect to the device in the browser by typing its IP address (or its network name)
1. Click on `Internet and security` tab
  1. Click on `Enable MQTT`
  1. Set the `Username` and `Password` as configured in the section above
  1. Set the `Server` to `raspberrypi:1883`
  1. Enable `Clean Session`

# Pictures from same month of the year
On the first week of each month, the picframe will only show pictures from the same month of
the year. In order to do this automatically, the model is refreshed via an MQTT message.
The script for publishing the message and the associated Cron job are in the `linuxenv` repository
under `xcustoms/pi.home/CRON/refreshPicframeModel.sh`. The username/password for the MQTT publisher
must be placed in a 

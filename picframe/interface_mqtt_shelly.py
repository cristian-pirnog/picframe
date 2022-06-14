"""MQTT interface of picframe."""

import logging
import time
import paho.mqtt.client as mqtt
import json
import os
from picframe import __version__
from picframe.controller import Controller
from interface_mqtt import InterfaceMQTT as InterfaceMQTTBase

class InterfaceMQTT(InterfaceMQTTBase):
    """MQTT interface of picframe.

    This interface interacts via mqtt with the user to steer the image display via Shelly

    Attributes
    ----------
    controller : Controler
        Controller for picframe


    Methods
    -------

    """
    topic_prefix = "shellies"


    def on_connect(self, client, userdata, flags, rc):
        super().on_connect(client, userdata, flags, rc)
        
        if rc != 0:
            self.__logger.warning("Can't connect with mqtt broker. Reason = {0}".format(rc))
            return
        self.__logger.info('Connected with MQTT broker')

        self.__logger.info(f'Subscribing to topic')
        try:
            result = client.subscribe(f'{self.topic_prefix}/#', qos=0)
            self.__logger.info(f'Got result {result} from MQTT subscribe command')
        except Exception as e:
            self.__logger.error(f'Got exception: {e}')
        # TODO: Fetch the last message sent by the sensor (ON or OFF) and react to it



    def on_message(self, client, userdata, message):
        self.__logger.info('on_message called')
        if not message.topic.startswith(self.topic_prefix):
            super().on_message(client, userdata, message)
            return

        self.__logger.info(f'Message topic: {message.topic}')
        try:
            self.__logger.info(f'Got MQTT message {message.payload}')
            msg = json.loads(message.payload.decode("utf-8"))
            self.__logger.info(f'Decoded MQTT payload {msg}')

            # display
            if r'button_pic_frame/input_event' in message.topic:
                self.handle_button(msg)
            elif 'shellymotionsensor' in message.topic:
                self.handle_motion_sensor(msg)
            else:
                self.__logger.info(f'Ignoring MQTT message from topic: {message.topic}')
        except Exception as e:
            self.__logger.error(f'Got error: {e}')
            return


    def handle_motion_sensor(self, msg):
        # self.__logger.debug(f"Handling sensor message: {msg}")
        self.__controller.display_is_on = bool(msg["sensor"]["motion"])


    def handle_button(self, msg):
        self.__logger.info(f"Handling button message: {msg}")
        if msg['event'] == 'S':
            self.__logger.info('Pausing playback')
            self.__controller.paused = not self.__controller.paused
            self.__logger.info(f'Paused status is: {self.__controller.paused}')
        elif msg['event'] == 'SS': # Go to previous picture
            self.__logger.info('Showing previous picture')
            self.__controller.paused = False
            self.__controller.back()
        elif msg['event'] == 'SSS':
            self.__logger.info('Showing the text')
            self.__controller.set_show_text()
        elif msg['event'] == 'L':
            self.__logger.info('Toggling the display')
            self.__controller.display_is_on = not self.__controller.display_is_on

    def publish_state(self, image, image_attr):
        pass


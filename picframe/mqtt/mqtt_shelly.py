"""MQTT interface of picframe."""

import logging
import time
import json
import os
from picframe import __version__
import re

from picframe.mqtt.interface import InterfaceMQTT

class MQTTShelly(InterfaceMQTT):
    """MQTT interface of picframe.

    This interface interacts via mqtt with the user to steer the image display via Shelly

    Attributes
    ----------
    controller : Controler
        Controller for picframe


    Methods
    -------

    """

    def __init__(self, controller, mqtt_config):
        super().__init__(controller, mqtt_config)
        self._logger = logging.getLogger("interface_mqtt_shelly.InterfaceMQTT")
        self._subscriber_topic_prefix = mqtt_config["subscriber_topic_prefix"]


    def on_connect(self, client, userdata, flags, rc):        
        if rc != 0:
            self._logger.warning("Can't connect with mqtt broker. Reason = {0}".format(rc))
            return
        self._logger.info('Connected with MQTT broker')

        self._logger.info(f'Subscribing to topic: {self._subscriber_topic_prefix}')
        try:
            result = client.subscribe(f'{self._subscriber_topic_prefix}/#', qos=0)
            self._logger.info(f'Got result {result} from MQTT subscribe command')
        except Exception as e:
            self._logger.error(f'Got exception: {e}')
        # TODO: Fetch the last message sent by the sensor (ON or OFF) and react to it



    def on_message(self, client, userdata, message):
        self._logger.debug('on_message called')
        if not message.topic.startswith(self._subscriber_topic_prefix):
            super().on_message(client, userdata, message)
            return

        try:
            self._logger.info(f"Topic {message.topic}. Message {message.payload}")
            msg = json.loads(message.payload.decode("utf-8"))
            self._logger.debug(f'Decoded MQTT payload {msg}')

            # display
            if f"{self._subscriber_topic_prefix}/button/input_event" in message.topic:
                self.handle_button(msg)
            elif message.topic == f"{self._subscriber_topic_prefix}/motion/status":
                self.handle_motion_sensor(msg)
            elif message.topic == f"{self._subscriber_topic_prefix}/reload_model/set":
                self._logger.debug(f"Received reload_model: {msg}")
                self.__controller.reload_model()
            else:
                self._logger.debug(f'Ignoring MQTT message from topic: {message.topic}')
        except Exception as e:
            self._logger.error(f'Got error: {e} - for message: {message.payload}')
            return


    def handle_motion_sensor(self, msg):
        self._logger.debug(f"Handling sensor message: {msg}")
        self.__controller.display_is_on = bool(msg["motion"])


    def handle_button(self, msg):
        self._logger.debug(f"Handling button message: {msg}")
        if msg['event'] == 'S':
            self._logger.debug('Toggling playback pause')
            self.__controller.paused = not self.__controller.paused
            self._logger.debug(f'Paused status is: {self.__controller.paused}')
        elif msg['event'] == 'SS': # Go to previous picture
            self._logger.info('Showing previous picture')
            self.__controller.paused = False
            self.__controller.back()
        elif msg['event'] == 'SSS':
            self._logger.info('Showing the text')
            self.__controller.set_show_text()
        elif msg['event'] == 'L':
            self._logger.info('Toggling the display')
            self.__controller.display_is_on = not self.__controller.display_is_on

    def publish_state(self, image, image_attr):
        self.__client.publish(f"{self._subscriber_topic_prefix}/", 
                              json.dumps({"alive": True}), qos=0, retain=False)



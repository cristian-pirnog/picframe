"""MQTT interface of picframe."""

import logging
import time
import paho.mqtt.client as mqtt
import json
import os
from picframe import __version__
from picframe.controller import Controller


class InterfaceMQTT:
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


    def __init__(self, controller, mqtt_config):
        self.__logger = logging.getLogger(self.__class__.__name__)
        self.__logger.info('creating an instance of InterfaceMQTT')
        self.__controller = controller
        try:
            device_id = mqtt_config['device_id']
            self.__client = mqtt.Client(client_id = device_id, clean_session=True)
            login = mqtt_config['login']
            password = mqtt_config['password']
            self.__client.username_pw_set(login, password)
            tls = mqtt_config['tls']
            if tls:
                self.__client.tls_set(tls)
            server = mqtt_config['server']
            port = mqtt_config['port']
            self.__client.on_connect = self.on_connect
            self.__client.on_message = self.on_message
            self.__client.connect(server, port, 60)
            # self.__device_id = mqtt_config['device_id']
        except Exception as e:
            self.__logger.info("MQTT not set up because of: {}".format(e))

    def start(self):
        try:
            self.__controller.publish_state = self.publish_state
            self.__client.loop_start()
        except Exception as e:
            self.__logger.info("MQTT not started because of: {}".format(e))

    def stop(self):
        try:
            self.__controller.publish_state = Controller.noop_publish_state
            self.__client.loop_stop()
        except Exception as e:
            self.__logger.info("MQTT stopping failed because of: {}".format(e))


    def on_connect(self, client, userdata, flags, rc):
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
            self.__logger.info(f'Ignoring message "{message.payload}" from topic "{message.topic}"')
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
        self.__logger.info(f"Handling sensor message: {msg}")
        self.__controller.display_is_on = bool(msg["motion"])


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
            self.__logger.info('Turning the display on')
            self.__controller.display_is_on = True

    def publish_state(self, image, image_attr):
        pass


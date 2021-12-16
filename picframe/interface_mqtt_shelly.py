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
    topic = "shellies/"


    def __init__(self, controller, mqtt_config):
        self.__logger = logging.getLogger("interface_mqtt.InterfaceMQTT")
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
            self.__client.connect(server, port, 60)
            self.__client.on_connect = self.on_connect
            self.__client.on_message = self.on_message
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
        self.__logger.info('Connected with mqtt broker')

        client.subscribe(f'{self.topic}#', qos=0)

        # TODO: Fetch the last message sent by the sensor (ON or OFF) and react to it



    def on_message(self, client, userdata, message):
        msg = json.loads(message.payload.decode("utf-8"))

        ###### switches ######
        # display
        if message.topic == self.topic:
            if msg["motion"]:
                self.__controller.display_is_on = True
            else:
                self.__controller.display_is_on = False


    def publish_state(self, image, image_attr):
        pass


import logging

from abc import abstractmethod
import paho.mqtt.client as mqtt_client


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

    def __init__(self, controller, mqtt_config: dict):
        self._logger = logging.getLogger("interface_mqtt_shelly.InterfaceMQTT")
        self._subscriber_topic_prefix = mqtt_config["subscriber_topic_prefix"]

        self._logger.info('creating an instance of InterfaceMQTT')
        self._controller = controller

        device_id = mqtt_config['device_id']
        self._client = mqtt_client.Client(client_id = device_id, clean_session=True)
        login = mqtt_config['login']
        password = mqtt_config['password']
        self._client.username_pw_set(login, password)
        tls = mqtt_config['tls']
        if tls:
            self._client.tls_set(tls)
        server = mqtt_config['server']
        port = mqtt_config['port']
        self._client.connect(server, port, 60)


    def __del__(self):
        self.stop()
        self._logger.info(f'Deleting the {self._class__.__name__} instance')

    def start(self):
        try:
            self._controller.publish_state = self.publish_state
            self._client.loop_start()
        except Exception as e:
            self._logger.info("MQTT not started because of: {}".format(e))

    def stop(self):
        # If the client is not started, there is no need to stop it
        if self._client._thread is None:
            return
        
        try:
            self._controller.publish_state = None
            self._client.loop_stop()
        except Exception as e:
            self._logger.info("MQTT stopping failed because of: {}".format(e))

    @abstractmethod
    def on_connect(self, client, userdata, flags, rc) -> None:
        pass

    @abstractmethod
    def on_message(self, client, userdata, message) -> None:
        pass

    @abstractmethod
    def publish_state(self, image, image_attr) -> None:
        pass


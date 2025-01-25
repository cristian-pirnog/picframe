
from picframe.mqtt.interface import InterfaceMQTT


class MQTTDisabled(InterfaceMQTT):
    def start(self):
        pass

    def stop(self):
        pass

    def on_connect(self, client, userdata, flags, rc):
        pass

    def on_message(self, client, userdata, message):
        pass

    def publish_state(self, image, image_attr):
        pass

def create(controller, mqtt_config: dict) -> InterfaceMQTT:
    if not mqtt_config['use_mqtt']:
        return MQTTDisabled()
    
    if mqtt_config['type'] == 'shelly':
        from picframe.mqtt.mqtt_shelly import MQTTShelly as MQTT
    else:
        from picframe.mqtt.mqtt_homeassistant import MQTTHomeAssistant as MQTT
    return MQTT(controller, mqtt_config)        

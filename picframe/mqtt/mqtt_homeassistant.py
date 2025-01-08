"""MQTT interface of picframe."""

import logging
import time
import json
import os
from picframe import __version__


class MQTTHomeAssistant(InterfaceMQTT):
    """MQTT interface of picframe.

    This interface interacts via mqtt with the user to steer the image display.

    Attributes
    ----------
    controller : Controler
        Controller for picframe


    Methods
    -------

    """

    def __init__(self, controller, mqtt_config):
        self.super().__init__(controller, mqtt_config)
        try:
            self._client.will_set("homeassistant/switch/" + mqtt_config['device_id'] + "/available", "offline", qos=0, retain=True)
            self._client.on_connect = self.on_connect
            self._client.on_message = self.on_message
            self.__device_id = mqtt_config['device_id']
        except Exception as e:
            self._logger.info("MQTT not set up because of: {}".format(e))

    def on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            self._logger.warning("Can't connect with mqtt broker. Reason = {0}".format(rc))
            return
        self._logger.info('Connected with mqtt broker')

        sensor_topic_head = "homeassistant/sensor/" + self.__device_id
        number_topic_head = "homeassistant/number/" + self.__device_id
        select_topic_head = "homeassistant/select/" + self.__device_id
        switch_topic_head = "homeassistant/switch/" + self.__device_id

        # send last will and testament
        available_topic = switch_topic_head + "/available"
        client.publish(available_topic, "online", qos=0, retain=True)

        ## sensors
        self.__setup_sensor(client, sensor_topic_head, "date_from", "mdi:calendar-arrow-left", available_topic)
        self.__setup_sensor(client, sensor_topic_head, "date_to", "mdi:calendar-arrow-right", available_topic)
        self.__setup_sensor(client, sensor_topic_head, "location_filter", "mdi:map-search", available_topic)
        self.__setup_sensor(client, sensor_topic_head, "tags_filter", "mdi:image-search", available_topic)
        self.__setup_sensor(client, sensor_topic_head, "image_counter", "mdi:camera-burst", available_topic)
        self.__setup_sensor(client, sensor_topic_head, "image", "mdi:file-image", available_topic, has_attributes=True)

        ## numbers
        self.__setup_number(client, number_topic_head, "brightness", 0.0, 1.0, 0.1, "mdi:brightness-6", available_topic)
        self.__setup_number(client, number_topic_head, "time_delay", 1, 400, 1, "mdi:image-plus", available_topic)
        self.__setup_number(client, number_topic_head, "fade_time", 1, 50, 1,"mdi:image-size-select-large", available_topic)
        self.__setup_number(client, number_topic_head, "matting_images", 0.0, 1.0, 0.01, "mdi:image-frame", available_topic)

        ## selects
        _, dir_list = self._controller.get_directory_list()
        dir_list.sort()
        self.__setup_select(client, select_topic_head, "directory", dir_list, "mdi:folder-multiple-image", available_topic, init=True)
        command_topic = self.__device_id + "/directory"
        client.subscribe(command_topic, qos=0)

        ## switches
        self.__setup_switch(client, switch_topic_head, "_reload_model", "mdi:reload", available_topic)
        self.__setup_switch(client, switch_topic_head, "_same_month_photos", "mdi:same-month", available_topic)
        self.__setup_switch(client, switch_topic_head, "_text_refresh", "mdi:refresh", available_topic)
        self.__setup_switch(client, switch_topic_head, "_delete", "mdi:delete", available_topic)
        self.__setup_switch(client, switch_topic_head, "_name_toggle", "mdi:subtitles", available_topic,
                            self._controller.text_is_on("name"))
        self.__setup_switch(client, switch_topic_head, "_title_toggle", "mdi:subtitles", available_topic,
                            self._controller.text_is_on("title"))
        self.__setup_switch(client, switch_topic_head, "_caption_toggle", "mdi:subtitles", available_topic,
                            self._controller.text_is_on("caption"))
        self.__setup_switch(client, switch_topic_head, "_date_toggle", "mdi:calendar-today", available_topic,
                            self._controller.text_is_on("date"))
        self.__setup_switch(client, switch_topic_head, "_location_toggle", "mdi:crosshairs-gps", available_topic,
                            self._controller.text_is_on("location"))
        self.__setup_switch(client, switch_topic_head, "_directory_toggle", "mdi:folder", available_topic,
                            self._controller.text_is_on("directory"))
        self.__setup_switch(client, switch_topic_head, "_text_off", "mdi:badge-account-horizontal-outline", available_topic)
        self.__setup_switch(client, switch_topic_head, "_display", "mdi:panorama", available_topic,
                            self._controller.display_is_on)
        self.__setup_switch(client, switch_topic_head, "_clock", "mdi:clock-outline", available_topic,
                            self._controller.clock_is_on)
        self.__setup_switch(client, switch_topic_head, "_shuffle", "mdi:shuffle-variant", available_topic,
                            self._controller.shuffle)
        self.__setup_switch(client, switch_topic_head, "_paused", "mdi:pause", available_topic,
                            self._controller.paused)
        self.__setup_switch(client, switch_topic_head, "_back", "mdi:skip-previous", available_topic)
        self.__setup_switch(client, switch_topic_head, "_next", "mdi:skip-next", available_topic)

        client.subscribe(self.__device_id + "/purge_files", qos=0) # close down without killing!
        client.subscribe(self.__device_id + "/stop", qos=0) # close down without killing!

    def __setup_sensor(self, client, sensor_topic_head, topic, icon, available_topic, has_attributes=False):
        config_topic = sensor_topic_head + "_" + topic + "/config"
        name = self.__device_id + "_" + topic
        if has_attributes == True:
            config_payload = json.dumps({"name": name,
                                     "icon": icon,
                                     "state_topic": sensor_topic_head + "/state",
                                     "value_template": "{{ value_json." + topic + "}}",
                                     "avty_t": available_topic,
                                     "json_attributes_topic": sensor_topic_head + "_" + topic + "/attributes",
                                     "uniq_id": name,
                                     "dev":{"ids":[self.__device_id]}})
        else:
            config_payload = json.dumps({"name": name,
                                     "icon": icon,
                                     "state_topic": sensor_topic_head + "/state",
                                     "value_template": "{{ value_json." + topic + "}}",
                                     "avty_t": available_topic,
                                     "uniq_id": name,
                                     "dev":{"ids":[self.__device_id]}})
        client.publish(config_topic, config_payload, qos=0, retain=True)
        client.subscribe(self.__device_id + "/" + topic, qos=0)

    def __setup_number(self, client, number_topic_head, topic, min, max, step, icon, available_topic):
        config_topic = number_topic_head + "_" + topic + "/config"
        command_topic = self.__device_id + "/" + topic
        state_topic = "homeassistant/sensor/" + self.__device_id + "/state"
        name = self.__device_id + "_" + topic
        config_payload = json.dumps({"name": name,
                                    "min": min,
                                    "max": max,
                                    "step": step,
                                    "icon": icon,
                                    "state_topic": state_topic,
                                    "command_topic": command_topic,
                                    "value_template": "{{ value_json." + topic + "}}",
                                    "avty_t": available_topic,
                                    "uniq_id": name,
                                    "dev":{"ids":[self.__device_id]}})
        client.publish(config_topic, config_payload, qos=0, retain=True)
        client.subscribe(command_topic, qos=0)

    def __setup_select(self, client, select_topic_head, topic, options, icon, available_topic, init=False):
        config_topic = select_topic_head + "_" + topic + "/config"
        command_topic = self.__device_id + "/" + topic
        state_topic = "homeassistant/sensor/" + self.__device_id + "/state"
        name = self.__device_id + "_" + topic

        config_payload = json.dumps({"name": name,
                                    "icon": icon,
                                    "options": options,
                                    "state_topic": state_topic,
                                    "command_topic": command_topic,
                                    "value_template": "{{ value_json." + topic + "}}",
                                    "avty_t": available_topic,
                                    "uniq_id": name,
                                    "dev":{"ids":[self.__device_id]}})
        client.publish(config_topic, config_payload, qos=0, retain=True)
        if init:
            client.subscribe(command_topic, qos=0)

    def __setup_switch(self, client, switch_topic_head, topic, icon,
                       available_topic, is_on=False):
        config_topic = switch_topic_head + topic + "/config"
        command_topic = switch_topic_head + topic + "/set"
        state_topic = switch_topic_head + topic + "/state"
        config_payload = json.dumps({"name": self.__device_id + topic,
                                     "icon": icon,
                                     "command_topic": command_topic,
                                     "state_topic": state_topic,
                                     "avty_t": available_topic,
                                     "uniq_id": self.__device_id + topic,
                                     "dev": {
                                        "ids": [self.__device_id],
                                        "name": self.__device_id,
                                        "mdl": "PictureFrame",
                                        "sw": __version__,
                                        "mf": "pi3d PictureFrame project"}})

        client.subscribe(command_topic , qos=0)
        client.publish(config_topic, config_payload, qos=0, retain=True)
        client.publish(state_topic, "ON" if is_on else "OFF", qos=0, retain=True)

    def on_message(self, client, userdata, message):
        self._logger.info(f"Handling message for topic: {message.topic} with payload: {message.payload}")
        payload = message.payload
        if not payload:
            self._logger.info(f"Ignoring message with empty payload for topic: {message.topic}")
            return 
        msg = message.payload.decode("utf-8")
        switch_topic_head = "homeassistant/switch/" + self.__device_id

        ###### switches ######
        # display
        if message.topic == switch_topic_head + "_display/set":
            state_topic = switch_topic_head + "_display/state"
            if msg == "ON":
                self._controller.display_is_on = True
                client.publish(state_topic, "ON", retain=True)
            elif msg == "OFF":
                self._controller.display_is_on = False
                client.publish(state_topic, "OFF", retain=True)
        # clock
        if message.topic == switch_topic_head + "_clock/set":
            state_topic = switch_topic_head + "_clock/state"
            if msg == "ON":
                self._controller.clock_is_on = True
                client.publish(state_topic, "ON", retain=True)
            elif msg == "OFF":
                self._controller.clock_is_on = False
                client.publish(state_topic, "OFF", retain=True)
        # shuffle
        elif message.topic == switch_topic_head + "_shuffle/set":
            state_topic = switch_topic_head + "_shuffle/state"
            if msg == "ON":
                self._controller.shuffle = True
                client.publish(state_topic, "ON", retain=True)
            elif msg == "OFF":
                self._controller.shuffle = False
                client.publish(state_topic, "OFF", retain=True)
        # paused
        elif message.topic == switch_topic_head + "_paused/set":
            state_topic = switch_topic_head + "_paused/state"
            if msg == "ON":
                self._controller.paused = True
                client.publish(state_topic, "ON", retain=True)
            elif msg == "OFF":
                self._controller.paused = False
                client.publish(state_topic, "OFF", retain=True)
        # back buttons
        elif message.topic == switch_topic_head + "_back/set":
            state_topic = switch_topic_head + "_back/state"
            if msg == "ON":
                client.publish(state_topic, "OFF", retain=True)
                self._controller.back()
        # next buttons
        elif message.topic == switch_topic_head + "_next/set":
            state_topic = switch_topic_head + "_next/state"
            if msg == "ON":
                client.publish(state_topic, "OFF", retain=True)
                self._controller.next()
        # delete
        elif message.topic == switch_topic_head + "_delete/set":
            state_topic = switch_topic_head + "_delete/state"
            if msg == "ON":
                client.publish(state_topic, "OFF", retain=True)
                self._controller.delete()
        # title on
        elif message.topic == switch_topic_head + "_title_toggle/set":
            state_topic = switch_topic_head + "_title_toggle/state"
            if msg in ("ON", "OFF"):
                self._controller.set_show_text("title", msg)
                client.publish(state_topic, msg, retain=True)
        # caption on
        elif message.topic == switch_topic_head + "_caption_toggle/set":
            state_topic = switch_topic_head + "_caption_toggle/state"
            if msg in ("ON", "OFF"):
                self._controller.set_show_text("caption", msg)
                client.publish(state_topic, msg, retain=True)
        # name on
        elif message.topic == switch_topic_head + "_name_toggle/set":
            state_topic = switch_topic_head + "_name_toggle/state"
            if msg in ("ON", "OFF"):
                self._controller.set_show_text("name", msg)
                client.publish(state_topic, msg, retain=True)
        # date_on
        elif message.topic == switch_topic_head + "_date_toggle/set":
            state_topic = switch_topic_head + "_date_toggle/state"
            if msg in ("ON", "OFF"):
                self._controller.set_show_text("date", msg)
                client.publish(state_topic, msg, retain=True)
        # location_on
        elif message.topic == switch_topic_head + "_location_toggle/set":
            state_topic = switch_topic_head + "_location_toggle/state"
            if msg in ("ON", "OFF"):
                self._controller.set_show_text("location", msg)
                client.publish(state_topic, msg, retain=True)
        # directory_on
        elif message.topic == switch_topic_head + "_directory_toggle/set":
            state_topic = switch_topic_head + "_directory_toggle/state"
            if msg in ("ON", "OFF"):
                self._controller.set_show_text("folder", msg)
                client.publish(state_topic, msg, retain=True)
        # text_off
        elif message.topic == switch_topic_head + "_text_off/set":
            state_topic = switch_topic_head + "_text_off/state"
            if msg == "ON":
                self._controller.set_show_text()
                client.publish(state_topic, "OFF", retain=True)
                state_topic = switch_topic_head + "_directory_toggle/state"
                client.publish(state_topic, "OFF", retain=True)
                state_topic = switch_topic_head + "_location_toggle/state"
                client.publish(state_topic, "OFF", retain=True)
                state_topic = switch_topic_head + "_date_toggle/state"
                client.publish(state_topic, "OFF", retain=True)
                state_topic = switch_topic_head + "_name_toggle/state"
                client.publish(state_topic, "OFF", retain=True)
                state_topic = switch_topic_head + "_title_toggle/state"
                client.publish(state_topic, "OFF", retain=True)
                state_topic = switch_topic_head + "_caption_toggle/state"
                client.publish(state_topic, "OFF", retain=True)
        # text_refresh
        elif message.topic == switch_topic_head + "_text_refresh/set":
            state_topic = switch_topic_head + "_text_refresh/state"
            if msg == "ON":
                client.publish(state_topic, "OFF", retain=True)
                self._controller.refresh_show_text()
        # reload_model
        elif message.topic == switch_topic_head + "_reload_model/set":
            self._logger.info(f"Received reload_model: {msg}")
            self._controller.reload_model()
        elif message.topic == switch_topic_head + "_same_month_photos/set":
            self._logger.info(f"Received same_month_photos: {msg}")
            self._controller.show_same_month_photos(msg)

        ##### values ########
        # change subdirectory
        elif message.topic == self.__device_id + "/directory":
            self._logger.info("Recieved subdirectory: %s", msg)
            self._controller.subdirectory = msg
        # date_from
        elif message.topic == self.__device_id + "/date_from":
            self._logger.info("Recieved date_from: %s", msg)
            self._controller.date_from = msg
        # date_to
        elif message.topic == self.__device_id + "/date_to":
            self._logger.info("Recieved date_to: %s", msg)
            self._controller.date_to = msg
        # fade_time
        elif message.topic == self.__device_id + "/fade_time":
            self._logger.info("Recieved fade_time: %s", msg)
            self._controller.fade_time = float(msg)
        # time_delay
        elif message.topic == self.__device_id + "/time_delay":
            self._logger.info("Recieved time_delay: %s", msg)
            self._controller.time_delay = float(msg)
        # brightness
        elif message.topic == self.__device_id + "/brightness":
            self._logger.info("Recieved brightness: %s", msg)
            self._controller.brightness = float(msg)
        # matting_images
        elif message.topic == self.__device_id + "/matting_images":
            self._logger.info("Received matting_images: %s", msg)
            self._controller.matting_images = float(msg)
        # location filter
        elif message.topic == self.__device_id + "/location_filter":
            self._logger.info("Recieved location filter: %s", msg)
            self._controller.location_filter = msg
        # tags filter
        elif message.topic == self.__device_id + "/tags_filter":
            self._logger.info("Recieved tags filter: %s", msg)
            self._controller.tags_filter = msg

        # set the flag to purge files from database
        elif message.topic == self.__device_id + "/purge_files":
            self._controller.purge_files()

        # stop loops and end program
        elif message.topic == self.__device_id + "/stop":
            self._controller.stop()

    def publish_state(self, image, image_attr):
        sensor_topic_head =  "homeassistant/sensor/" + self.__device_id
        switch_topic_head = "homeassistant/switch/" + self.__device_id
        select_topic_head = "homeassistant/select/" + self.__device_id
        sensor_state_topic = sensor_topic_head + "/state"

        sensor_state_payload = {}

        ## sensor
        # directory sensor
        actual_dir, dir_list = self._controller.get_directory_list()
        sensor_state_payload["directory"] = actual_dir
        # image counter sensor
        sensor_state_payload["image_counter"] = str(self._controller.get_number_of_files())
        # image sensor
        _, tail = os.path.split(image)
        sensor_state_payload["image"] = tail
        # date_from
        sensor_state_payload["date_from"] = int(self._controller.date_from)
        # date_to
        sensor_state_payload["date_to"] = int(self._controller.date_to)
        # location_filter
        sensor_state_payload["location_filter"] = self._controller.location_filter
        # tags_filter
        sensor_state_payload["tags_filter"] = self._controller.tags_filter

        ## number state
        # time_delay
        sensor_state_payload["time_delay"] = self._controller.time_delay
        # fade_time
        sensor_state_payload["fade_time"] = self._controller.fade_time
        # brightness
        sensor_state_payload["brightness"] = self._controller.brightness
        # matting_images
        sensor_state_payload["matting_images"] = self._controller.matting_images

        # send last will and testament
        available_topic = switch_topic_head + "/available"
        self._client.publish(available_topic, "online", qos=0, retain=True)

        #pulish sensors
        attributes_topic = sensor_topic_head + "_image/attributes"
        self._logger.debug("Send image attributes: %s", image_attr)
        self._client.publish(attributes_topic, json.dumps(image_attr), qos=0, retain=False)
        dir_list.sort()
        self.__setup_select(self._client, select_topic_head, "directory", dir_list, "mdi:folder-multiple-image", available_topic, init=False)

        self._logger.info("Send sensor state: %s", sensor_state_payload)
        self._client.publish(sensor_state_topic, json.dumps(sensor_state_payload), qos=0, retain=False)


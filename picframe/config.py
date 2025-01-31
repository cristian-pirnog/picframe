from enum import Enum, unique
import logging
import logging.config
from pathlib import Path
import yaml
import json

DEFAULT_CONFIG = {
    'viewer': {
        'blur_amount': 12,
        'blur_zoom': 1.0,
        'blur_edges': False,
        'edge_alpha': 0.5,
        'fps': 20.0,
        'background': [0.2, 0.2, 0.3, 1.0],
        'blend_type': "blend", # {"blend":0.0, "burn":1.0, "bump":2.0}

        'font_file': '~/picframe_data/data/fonts/NotoSans-Regular.ttf',
        'shader': '~/picframe_data/data/shaders/blend_new',
        'show_text_fm': '%b %d, %Y',
        'show_text_tm': 20.0,
        'show_text_sz': 40,
        'show_text': "name location",
        'text_justify': 'L',
        'fit': False,
        #'auto_resize': True,
        'kenburns': False,
        'display_x': 0,
        'display_y': 0,
        'display_w': None,
        'display_h': None,
        'use_glx': False,                          # default=False. Set to True on linux with xserver running
        'test_key': 'test_value',
        'mat_images': True,
        'mat_type': None,
        'outer_mat_color': None,
        'inner_mat_color': None,
        'outer_mat_border': 75,
        'inner_mat_border': 40,
        'inner_mat_use_texture': False,
        'outer_mat_use_texture': True,
        'mat_resource_folder': '~/picframe_data/data/mat',
        'show_clock': False,
        'clock_justify': "R",
        'clock_text_sz': 120,
        'clock_format': "%I:%M",
    },
    'model': {

        'pic_dir': '~/Pictures',
        'no_files_img': '~/picframe_data/data/no_pictures.jpg',
        'follow_links': False,
        'subdirectory': '',
        'recent_n': 3,
        'reshuffle_num': 1,
        'time_delay': 200.0,
        'fade_time': 10.0,
        'shuffle': True,
        'sort_cols': 'fname ASC',
        'image_attr': ['PICFRAME GPS'],                          # image attributes send by MQTT, Keys are taken from exifread library, 'PICFRAME GPS' is special to retrieve GPS lon/lat
        'load_geoloc': True,
        'locale': 'en_US.utf8',
        'key_list': [['tourism','amenity','isolated_dwelling'],['suburb','village'],['city','county'],['region','state','province'],['country']],
        'geo_key': 'this_needs_to@be_changed',  # use your email address
        'db_file': '~/picframe_data/data/pictureframe.db3',
        'portrait_pairs': False,
        'deleted_pictures': '~/DeletedPictures',
        'log_level': 'WARNING',
        'log_file': '',
    },
    "controller": {
        'use_kbd': False,
    },
    'mqtt': {
        'use_mqtt': False,                          # Set tue true, to enable mqtt
        'server': '',
        'port': 8883,
        'login': '',
        'password': '',
        'tls': '',
        'device_id': 'picframe',                                 # unique id of device. change if there is more than one picture frame
        'subscriber_topic_prefix': 'shellies/'
    },
    'http': {
        'use_http': False,
        'path': '~/picframe_data/html',
        'port': 9000,
        'use_ssl': False,
        'keyfile': "/path/to/key.pem",
        'certfile': "/path/to/fullchain.pem"
    }
}


@unique
class ConfigSection(Enum):
    MODEL = "model"
    VIEWER = "viewer"
    MQTT = "mqtt"
    HTTP = "http"
    CONTROLLER = "controller"


class Config:
    def __init__(self, configfile: Path):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.debug('creating an instance of Model')
        self._config = {}

        configfile = Path(configfile)
        self._logger.info(f"Open config file: {configfile}")
        with configfile.open('r') as fr:
            try:
                conf = yaml.safe_load(fr)
                for section in list(ConfigSection):
                    self._config[section] = {**DEFAULT_CONFIG[section.value], **conf[section.value]}

                self._logger.debug(f'config data = {self._config}')
            except yaml.YAMLError as exc:
                self._logger.error(f"Can't parse yaml config file: {configfile}, {exc}")
                raise
        
        log_config_file = configfile.parent / 'log_config.json'
        with log_config_file.open('r') as fr:
            logging.config.dictConfig(json.load(fr))
        print('Completed logger initialization')


    def get(self, section: ConfigSection):
        return self._config[section]

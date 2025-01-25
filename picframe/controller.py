"""Controller of picframe."""

from datetime import datetime
import logging
import time
import json
import signal
import ssl

from picframe.mqtt import factory as mqtt_factory
from picframe import interface_kbd, interface_http
from picframe.model import Model
from picframe.config import Config, ConfigSection
from picframe.viewer_display import ViewerDisplay


EXIF_TO_FIELD = {'EXIF FNumber': 'f_number',
                    'Image Make': 'make',
                    'Image Model': 'model',
                    'EXIF ExposureTime': 'exposure_time',
                    'EXIF ISOSpeedRatings': 'iso',
                    'EXIF FocalLength': 'focal_length',
                    'EXIF Rating': 'rating',
                    'EXIF LensModel': 'lens',
                    'EXIF DateTimeOriginal': 'exif_datetime',
                    'IPTC Keywords': 'tags',
                    'IPTC Caption/Abstract': 'caption',
                    'IPTC Object Name': 'title'}

def make_date(txt):
    dt = txt.replace('/',':').replace('-',':').replace(',',':').replace('.',':').split(':')
    dt_tuple = tuple(int(i) for i in dt) #TODO catch badly formed dates?
    return time.mktime(dt_tuple + (0, 0, 0, 0, 0, 0))


class Controller:
    """Controller of picframe.

    This controller interacts via mqtt with the user to steer the image display.

    Attributes
    ----------
    model : Model
        model of picframe containing config and business logic
    viewer : ViewerDisplay
        viewer of picframe representing the display


    Methods
    -------
    paused
        Getter and setter for pausing image display.
    next
        Show next image.
    back
        Show previous image.

    """

    def __init__(self, model: Model, viewer: ViewerDisplay, config: Config):
        self._logger = logging.getLogger("controller.Controller")
        self._logger.info('creating an instance of Controller')
        self._model = model
        self._viewer = viewer
        self._paused = False
        self._next_tm = 0
        self._date_from = make_date('1901/12/15') # TODO This seems to be the minimum date to be handled by date functions
        self._date_to = make_date('2038/1/1')
        self._location_filter = ""
        self._where_clauses = {}
        self._sort_clause = "exif_datetime ASC"
        self._keep_looping = True
        self._location_filter = ''
        self._tags_filter = ''
        self._shutdown_complete = False
        
        self._mqtt = mqtt_factory.create(config.get(ConfigSection.MQTT), self)
        self._mqtt.start()

        self._http = self._create_http(config.get(ConfigSection.HTTP))

        if config['use_kbd']:
            interface_kbd.InterfaceKbd(self) # TODO make kbd failsafe

    def __del__(self):
        self._logger.info('Deleting the Controller')
        self._keep_looping = False
        self._mqtt.stop()

        if self._http is not None:
            self._http.stop()

    def _create_http(self, http_config) -> interface_http.InterfaceHttp:
        if http_config['use_http']:
            from picframe import interface_http
            model_config = self._model.get_model_config()
            http = interface_http.InterfaceHttp(self,
                                                http_config['path'],
                                                model_config['pic_dir'],
                                                model_config['no_files_img'],
                                                http_config['port'],
                                                http_config['auth'],
                                                http_config['username'],
                                                http_config['password'],
                                            )  # TODO: Implement TLS
            if http_config['use_ssl']:
                http.socket = ssl.wrap_socket(http.socket,
                                              keyfile=http_config['keyfile'],
                                              certfile=http_config['certfile'],
                                              server_side=True)
            return http
        return None
    
    @property
    def paused(self):
        """Get or set the current state for pausing image display. Setting paused to true
        will show the actual image as long paused is not set to false.
        """
        return self._paused

    @paused.setter
    def paused(self, val:bool):
        self._paused = val
        pic = self._model.get_current_pics()[0] # only refresh left text
        self._viewer.reset_name_tm(pic, val, side=0, pair=self._model.get_current_pics()[1] is not None)

    def next(self):
        self._next_tm = 0
        self._viewer.reset_name_tm()

    def back(self):
        self._model.set_next_file_to_previous_file()
        self._next_tm = 0
        self._viewer.reset_name_tm()

    def delete(self):
        self._model.delete_file()
        self.back() # TODO check needed to avoid skipping one as record has been deleted from model.__file_list
        self._next_tm = 0

    def set_show_text(self, txt_key=None, val="ON"):
        if val is True: # allow to be called with boolean from httpserver
            val = "ON"
        self._viewer.set_show_text(txt_key, val)
        for (side, pic) in enumerate(self._model.get_current_pics()):
            if pic is not None:
                self._viewer.reset_name_tm(pic, self.paused, side, self._model.get_current_pics()[1] is not None)

    def refresh_show_text(self):
        for (side, pic) in enumerate(self._model.get_current_pics()):
            if pic is not None:
                self._viewer.reset_name_tm(pic, self.paused, side, self._model.get_current_pics()[1] is not None)

    def purge_files(self):
        self._model.purge_files()

    @property
    def subdirectory(self):
        return self._model.subdirectory

    def reload_model(self):
        self._viewer.set_show_month(datetime.now().day <= 7)
        self._model.force_reload()
 
    def show_same_month_photos(self, config: str):
        try:
            config = json.loads(config)
        except:
            config = {"activate": False}

        value = config.get("activate", False)
        self._model.same_month_photos = value
        self._viewer.set_show_month(value)
        self.reload_model()

    @subdirectory.setter
    def subdirectory(self, dir):
        self._model.subdirectory = dir
        self._model.force_reload()
        self._next_tm = 0

    @property
    def date_from(self):
        return self._date_from

    @date_from.setter
    def date_from(self, val):
        try:
            self._date_from = float(val)
        except ValueError:
            self._date_from = make_date(val if len(val) > 0 else '1901/12/15')
        if len(val) > 0:
            self._model.set_where_clause('date_from', "exif_datetime > {:.0f}".format(self._date_from))
        else:
            self._model.set_where_clause('date_from') # remove from where_clause
        self._model.force_reload()
        self._next_tm = 0

    @property
    def date_to(self):
        return self._date_to

    @date_to.setter
    def date_to(self, val):
        try:
            self._date_to = float(val)
        except ValueError:
            self._date_to = make_date(val if len(val) > 0 else '2038/1/1')
        if len(val) > 0:
            self._model.set_where_clause('date_to', "exif_datetime < {:.0f}".format(self._date_to))
        else:
            self._model.set_where_clause('date_to') # remove from where_clause
        self._model.force_reload()
        self._next_tm = 0

    @property
    def display_is_on(self):
        return self._viewer.display_is_on

    @display_is_on.setter
    def display_is_on(self, on_off):
        self._viewer.display_is_on = on_off

    @property
    def clock_is_on(self):
        return self._viewer.clock_is_on

    @clock_is_on.setter
    def clock_is_on(self, on_off):
        self._viewer.clock_is_on = on_off

    @property
    def shuffle(self):
        return self._model.shuffle

    @shuffle.setter
    def shuffle(self, val:bool):
        self._model.shuffle = val
        self._model.force_reload()
        self._next_tm = 0

    @property
    def fade_time(self):
        return self._model.fade_time

    @fade_time.setter
    def fade_time(self, time):
        self._model.fade_time = float(time)
        self._next_tm = 0

    @property
    def time_delay(self):
        return self._model.time_delay

    @time_delay.setter
    def time_delay(self, time):
        time = float(time) # convert string before comparison
        # might break it if too quick
        if time < 5.0:
            time = 5.0
        self._model.time_delay = time
        self._next_tm = 0

    @property
    def brightness(self):
        return self._viewer.get_brightness()

    @brightness.setter
    def brightness(self, val):
        self._viewer.set_brightness(float(val))

    @property
    def matting_images(self):
        return self._viewer.get_matting_images()

    @matting_images.setter
    def matting_images(self, val):
        self._viewer.set_matting_images(float(val))

    @property
    def location_filter(self):
        return self._location_filter

    @location_filter.setter
    def location_filter(self, val):
        self._location_filter = val
        if len(val) > 0:
            self._model.set_where_clause("location_filter", self._build_filter(val, "location"))
        else:
            self._model.set_where_clause("location_filter") # remove from where_clause
        self._model.force_reload()
        self._next_tm = 0

    @property
    def tags_filter(self):
        return self._tags_filter

    @tags_filter.setter
    def tags_filter(self, val):
        self._tags_filter = val
        if len(val) > 0:
            self._model.set_where_clause("tags_filter", self._build_filter(val, "tags"))
        else:
            self._model.set_where_clause("tags_filter") # remove from where_clause
        self._model.force_reload()
        self._next_tm = 0

    def _build_filter(self, val, field):
        if val.count("(") != val.count(")"):
            return None # this should clear the filter and not raise an error
        val = val.replace(";", "").replace("'", "").replace("%", "").replace('"', '') # SQL scrambling
        tokens = ("(", ")", "AND", "OR", "NOT") # now copes with NOT
        val_split = val.replace("(", " ( ").replace(")", " ) ").split() # so brackets not joined to words
        filter = []
        last_token = ""
        for s in val_split:
            s_upper = s.upper()
            if s_upper in tokens:
                if s_upper in ("AND", "OR"):
                    if last_token in ("AND", "OR"):
                        return None # must have a non-token between
                    last_token = s_upper
                filter.append(s)
            else:
                if last_token is not None:
                    filter.append("{} LIKE '%{}%'".format(field, s))
                else:
                    filter[-1] = filter[-1].replace("%'", " {}%'".format(s))
                last_token = None
        return "({})".format(" ".join(filter)) # if OR outside brackets will modify the logic of rest of where clauses

    def text_is_on(self, txt_key):
        return self._viewer.text_is_on(txt_key)

    def get_number_of_files(self):
        return self._model.get_number_of_files()

    def get_directory_list(self):
        actual_dir, dir_list = self._model.get_directory_list()
        return actual_dir, dir_list

    def get_current_path(self):
        (pic, _) = self._model.get_current_pics()
        return pic.fname

    def loop(self):
        # catch ctrl-c
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        #next_check_tm = time.time() + self._model.get_model_config()['check_dir_tm']
        while self._keep_looping:
            # If the display is not on, just sleep for a bit and then go back to start of loop
            if not self.display_is_on:
                time.sleep(1)
                self._next_tm = time.time() + self._model.time_delay
                continue

            #if self._next_tm == 0: #TODO double check why these were set when next_tm == 0
            #    time_delay = 1 # must not be 0
            #    fade_time = 1 # must not be 0
            #else:
            time_delay = self._model.time_delay
            fade_time = self._model.fade_time

            tm = time.time()
            pics = None #get_next_file returns a tuple of two in case paired portraits have been specified
            if not self.paused and tm > self._next_tm:
                self._next_tm = tm + self._model.time_delay
                pics = self._model.get_next_file()
                if pics[0] is None:
                    self._next_tm = 0 # skip this image file moved or otherwise not on db
                    pics = None # signal slideshow_is_running not to load new image
                else:
                    image_attr = {}
                    for key in self._model.get_model_config()['image_attr']:
                        if key == 'PICFRAME GPS':
                            image_attr['latitude'] = pics[0].latitude
                            image_attr['longitude'] = pics[0].longitude
                        elif key == 'PICFRAME LOCATION':
                            image_attr['location'] = pics[0].location
                        else:
                            field_name = EXIF_TO_FIELD[key]
                            image_attr[key] = pics[0].__dict__[field_name] #TODO nicer using namedtuple for Pic
                    self._mqtt.publish_state(pics[0].fname, image_attr)
            self._model.pause_looping = self._viewer.is_in_transition()
            (loop_running, skip_image) = self._viewer.slideshow_is_running(pics, time_delay, fade_time, self._paused)
            if not loop_running:
                break
            if skip_image:
                self._next_tm = 0
        self._shutdown_complete = True

    def start(self):
        self._viewer.slideshow_start()
        self.loop()

    def stop(self):
        self._keep_looping = False
        while not self._shutdown_complete:
            time.sleep(0.05) # block until main loop has stopped
        self._viewer.slideshow_stop() # do this last

    def _signal_handler(self, sig, frame):
        self._logger.info(f'Stopping picframe due to signal: {sig}')
        self._shutdown_complete = True
        self.stop()

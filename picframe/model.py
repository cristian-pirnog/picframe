import abc
from datetime import datetime
from pathlib import Path
import yaml
import os
import time
import logging
import logging.config
import random
import json
import locale
from picframe import geo_reverse, image_cache

class Pic: #TODO could this be done more elegantly with namedtuple

    def __init__(self, fname, last_modified, file_id, orientation=1, exif_datetime=0,
                 f_number=0, exposure_time=None, iso=0, focal_length=None,
                 make=None, model=None, lens=None, rating=None, latitude=None,
                 longitude=None, width=0, height=0, is_portrait=0, location=None, title=None,
                 caption=None, tags=None):
        self.fname = fname
        self.last_modified = last_modified
        self.file_id = file_id
        self.orientation = orientation
        self.exif_datetime = exif_datetime
        self.f_number = f_number
        self.exposure_time = exposure_time
        self.iso = iso
        self.focal_length = focal_length
        self.make = make
        self.model = model
        self.lens = lens
        self.rating = rating
        self.latitude = latitude
        self.longitude = longitude
        self.width = width
        self.height = height
        self.is_portrait = is_portrait
        self.location = location
        self.tags=tags
        self.caption=caption
        self.title=title


class Model:

    def __init__(self, config: dict):
        self._logger = logging.getLogger("model.Model")
        self._logger.debug('creating an instance of Model')
        self._config = config

        self._file_list = [] # this is now a list of tuples i.e (file_id1,) or (file_id1, file_id2)
        self._number_of_files = 0 # this is shortcut for len(__file_list)
        self.same_month_photos = False
        self.same_day_photos = False
        self._reload_files = True
        self._file_index = 0 # pointer to next position in __file_list
        self._current_pics = (None, None) # this hold a tuple of (pic, None) or two pic objects if portrait pairs
        self._num_run_through = 0

        try:
            locale.setlocale(locale.LC_TIME, self._config['locale'])
        except:
            self._logger.error("error trying to set locale to {}".format(self._config['locale']))
        self._pic_dir = os.path.expanduser(self._config['pic_dir'])
        self._subdirectory = os.path.expanduser(self._config['subdirectory'])
        self._load_geoloc = self._config['load_geoloc']
        self._geo_reverse = geo_reverse.GeoReverse(self._config['geo_key'], key_list=self._config()['key_list'])
        self._image_cache = image_cache.ImageCache(self._pic_dir,
                                                    self._config['follow_links'],
                                                    os.path.expanduser(self._config['db_file']),
                                                    self._geo_reverse,
                                                    self._config['portrait_pairs'],
                                                    continuous_update=self._config["update_cache"])
        self._deleted_pictures = self._config['deleted_pictures']
        self._no_files_img = os.path.expanduser(self._config['no_files_img'])
        self._sort_cols = self._config['sort_cols']
        self._col_names = None
        self._where_clauses = {} # these will be modified by controller
        self._logger.info("Completed initialization")

    def get_mqtt_config(self):
        return self._config['mqtt']

    def get_http_config(self):
        return self._config['http']

    @property
    def fade_time(self):
        return self._config['model']['fade_time']

    @fade_time.setter
    def fade_time(self, time):
        self._config['model']['fade_time'] = time

    @property
    def time_delay(self):
        return self._config['model']['time_delay']

    @time_delay.setter
    def time_delay(self, time):
        self._config['model']['time_delay'] = time

    @property
    def subdirectory(self):
        return self._subdirectory

    @subdirectory.setter
    def subdirectory(self, dir):
        _, root = os.path.split(self._pic_dir)
        actual_dir = root
        if self.subdirectory != '':
            actual_dir = self.subdirectory
        if actual_dir != dir:
            if root == dir:
                self._subdirectory = ''
            else:
                self._subdirectory = dir
            self._logger.info("Set subdirectory to: %s", self._subdirectory)
            self._reload_files = True

    @property
    def shuffle(self):
        return self._config['model']['shuffle']

    @shuffle.setter
    def shuffle(self, val:bool):
        self._config['model']['shuffle'] = val #TODO should this be altered in config?
        #if val == True:
        #    self._shuffle_files()
        #else:
        #    self._sort_files()
        self._reload_files = True

    def set_where_clause(self, key, value=None):
        # value must be a string for later join()
        if (value is None or len(value) == 0):
            if key in self._where_clauses:
                self._where_clauses.pop(key)
            return
        self._where_clauses[key] = value

    def get_where_clauses(self):
        return self._where_clauses

    def pause_looping(self, val):
        self._image_cache.pause_looping(val)

    def purge_files(self):
        self._image_cache.purge_files()

    def get_directory_list(self):
        _, root = os.path.split(self._pic_dir)
        actual_dir = root
        if self.subdirectory != '':
            actual_dir = self.subdirectory
        follow_links = self.get_self._config()['follow_links']
        subdir_list = next(os.walk(self._pic_dir, followlinks=follow_links))[1]
        subdir_list[:] = [d for d in subdir_list if not d[0] == '.']
        if not follow_links:
            subdir_list[:] = [d for d in subdir_list if not os.path.islink(self._pic_dir + '/' + d)]
        subdir_list.insert(0,root)
        return actual_dir, subdir_list

    def force_reload(self):
        self._reload_files = True

    def set_next_file_to_previous_file(self):
        self._file_index = (self._file_index - 2) % self._number_of_files # TODO deleting last image results in ZeroDivisionError

    def get_next_file(self):
        missing_images = 0

        # loop until we acquire a valid image set
        while True:
            pic1 = None
            pic2 = None

            # Reload the playlist if requested
            if self._reload_files:
                self._image_cache.start()
                for _ in range(5): # give image_cache chance on first load if a large directory
                    self._get_files()
                    missing_images = 0
                    if self._number_of_files > 0:
                        break
                    time.sleep(0.5)

            # If we don't have any files to show, prepare the "no images" image
            # Also, set the reload_files flag so we'll check for new files on the next pass...
            if self._number_of_files == 0 or missing_images >= self._number_of_files:
                pic1 = Pic(self._no_files_img, 0, 0)
                self._reload_files = True
                break

            # If we've displayed all images...
            #   If it's time to shuffle, set a flag to do so
            #   Loop back, which will reload and shuffle if necessary
            if self._file_index == self._number_of_files:
                self._num_run_through += 1
                if self.shuffle and self._num_run_through >= self.get_self._config()['reshuffle_num']:
                    self._reload_files = True
                self._file_index = 0
                continue

            # Load the current image set
            file_ids = self._file_list[self._file_index]
            pic_row = self._image_cache.get_file_info(file_ids[0])
            pic1 = Pic(**pic_row) if pic_row is not None else None
            if len(file_ids) == 2:
                pic_row = self._image_cache.get_file_info(file_ids[1])
                pic2 = Pic(**pic_row) if pic_row is not None else None

            # Verify the images in the selected image set actually exist on disk
            # Blank out missing references and swap positions if necessary to try and get
            # a valid image in the first slot.
            if pic2 and not os.path.isfile(pic2.fname): pic2 = None
            if pic1 and not os.path.isfile(pic1.fname): pic1 = None
            if (not pic1 and pic2): pic1, pic2 = pic2, pic1

            # Increment the image index for next time
            self._file_index += 1

            # If pic1 is valid here, everything is OK. Break out of the loop and return the set
            if pic1:
                break

            # Here, pic1 is undefined. That's a problem. Loop back and get another image set.
            # Track the number of times we've looped back so we can abort if we don't have *any* images to display
            missing_images += 1

        self._current_pics = (pic1, pic2)
        return self._current_pics

    def get_number_of_files(self):
        #return self._number_of_files
        #return sum(1 for pics in self._file_list for pic in pics if pic is not None)
        # or
        return sum(
                    sum(1 for pic in pics if pic is not None)
                        for pics in self._file_list
                )

    def get_current_pics(self):
        return self._current_pics

    def delete_file(self):
        # delete the current pic. If it's a portrait pair then only the left one will be deleted
        pic = self._current_pics[0]
        if pic is None:
            return None
        f_to_delete = pic.fname
        move_to_dir = os.path.expanduser(self._deleted_pictures)
        # TODO should these os system calls be inside a try block in case the file has been deleted after it started to show?
        if not os.path.exists(move_to_dir):
          os.system("mkdir {}".format(move_to_dir)) # problems with ownership using python func
        os.system("mv '{}' '{}'".format(f_to_delete, move_to_dir)) # and with SMB drives
        # find and delete record from __file_list
        for i, file_rec in enumerate(self._file_list):
            if file_rec[0] == pic.file_id: # database id TODO check that db tidies itself up
                self._file_list.pop(i)
                self._number_of_files -= 1
                break

    def get_picture_dir(self):
        if self.subdirectory != "":
            picture_dir = os.path.join(self._pic_dir, self.subdirectory) # TODO catch, if subdirecotry does not exist
        else:
            picture_dir = self._pic_dir

        return picture_dir

    def __get_files(self):

        # On the first week of the month, use files from the same month
        if self.same_day_photos:
            file_selector = SameDayFileSelector(self)
        if self.same_month_photos or datetime.now().day <= 7:
            file_selector = SameMonthFileSelector(self)
        else:
            file_selector = DefaultFileSelector(self)


        file_selector = FileSelectorFactory.get(self)
        self._logger.info(f"Using file selector: {file_selector.__class__.__name__}")

        where_clause = file_selector.get_where_clause()
        sort_clause = file_selector.get_sort_clause()
        
        self._file_list = self._image_cache.query_cache(where_clause, sort_clause)
        self._number_of_files = len(self._file_list)
        self._file_index = 0
        self._num_run_through = 0
        self._reload_files = False


class FileSelector(abc.ABC):
    def __init__(self, model: Model) -> None:
        self.model = model
        super().__init__()

    def get_where_clause(self) -> str:
        where_list = [f"fname LIKE '{self.model.get_picture_dir()}/%'"]
        where_list.extend(self._get_where_list())
        return " AND ".join(where_list) if len(where_list) > 0 else "1"


    def get_sort_clause(self) -> str:
        sort_list = []
        recent_n = self.model.get_self._config()["recent_n"]
        if recent_n > 0:
            sort_list.append("last_modified > {:.0f}".format(time.time() - 3600 * 24 * recent_n))

        if self.model.shuffle:
            sort_list.append("RANDOM()")
        else:
            sort_list.extend(self._get_sort_list())

        return ",".join(sort_list)

    @abc.abstractmethod
    def _get_where_list(self) -> str:
        pass


    @abc.abstractmethod
    def _get_sort_list(self) -> str:
        pass


class DefaultFileSelector(FileSelector):
    def __init__(self, model: Model) -> None:
        super().__init__(model)
        self.model = model

    def _get_where_list(self) -> str:
        return self.model.get_where_clauses()


    def _get_sort_list(self) -> str:
        sort_list = []

        if self.model.__col_names is None:
            self.model.__col_names = self.model.__image_cache.get_column_names() # do this once
        for col in self.model.__sort_cols.split(","):
            colsplit = col.split()
            if colsplit[0] in self.model.__col_names and (len(colsplit) == 1 or colsplit[1].upper() in ("ASC", "DESC")):
                sort_list.append(col)
        sort_list.append("fname ASC") # always finally sort on this in case nothing else to sort on or sort_cols is ""
        
        return sort_list


class SameMonthFileSelector(FileSelector):
    def __init__(self, model: Model) -> None:
        super().__init__(model)
        self.month = datetime.now().month

    def _get_where_list(self) -> str:
        return [f"STRFTIME('%m', DATETIME(exif_datetime, 'unixepoch')) = '{self.month:02}'"]

    
    def _get_sort_list(self) -> str:
        return [""]

class SameDayFileSelector(FileSelector):
    def __init__(self, model: Model) -> None:
        super().__init__(model)
        now = datetime.now()
        self.month = now.month
        self.day = now.day

    def _get_where_list(self) -> str:
        return [f"STRFTIME('%m%d', DATETIME(exif_datetime, 'unixepoch')) = '{self.month:02}{self.day:02}'"]

    
    def _get_sort_list(self) -> str:
        return [""]



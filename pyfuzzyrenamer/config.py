import configparser
import copy
import logging
import os
from enum import IntEnum
from multiprocessing import cpu_count
from pathlib import Path

from pyfuzzyrenamer import filters, masks

D_FILENAME = 0
D_MATCH_SCORE = 1
D_MATCHNAME = 2
D_PREVIEW = 3
D_NBMATCH = 4
D_STATUS = 5
D_CHECKED = 6


class SimilarityScorer(IntEnum):
    WRATIO = 0
    QRATIO = 1
    PARTIAL_RATIO = 2
    TOKEN_SORT_RATIO = 3
    PARTIAL_TOKEN_SORT_RATIO = 4
    TOKEN_SET_RATIO = 5
    PARTIAL_TOKEN_SET_RATIO = 6

    def __str__(self):
        if self.value == 0:
            return "Combined"
        elif self.value == 1:
            return "Simple ratio"
        elif self.value == 2:
            return "Partial Ratio"
        elif self.value == 3:
            return "Token Sort Ratio"
        elif self.value == 4:
            return "Partial Token Sort Ratio"
        elif self.value == 5:
            return "Token Set Ratio"
        elif self.value == 6:
            return "Partial Token Set Ratio"
        else:
            return ""

class MatchStatus(IntEnum):
    NONE = 0
    MATCH = 1
    USRMATCH = 2
    NOMATCH = 3

    def __str__(self):
        if self.value == 1:
            return "Matched"
        elif self.value == 2:
            return "User choice"
        elif self.value == 3:
            return "No match found"
        else:
            return ""


DEFAULT_CONFIG_FILE = os.sep.join([os.getcwd(), "pyfuzzyrenamer.ini"])
default_columns = [
    {"index": D_FILENAME, "width": 300, "label": "Source Name", "shown": True},
    {"index": D_MATCH_SCORE, "width": 80, "label": "Similarity(%)", "shown": True},
    {"index": D_MATCHNAME, "width": 300, "label": "Closest Match", "shown": True},
    {"index": D_PREVIEW, "width": 300, "label": "Renaming Preview", "shown": True},
    {"index": D_NBMATCH, "width": 60, "label": "Match#", "shown": False},
    {"index": D_STATUS, "width": 100, "label": "Matching Status", "shown": True},
    {"index": D_CHECKED, "width": 60, "label": "Checked", "shown": False},
]
default_masks_teststring = "(1986) Hitchhiker's Guide to the Galaxy, The (AGA) Disk1"
default_filters_teststring = "Hitchhiker's Guide to the Galaxy, The (AGA)"
default_masks = (
    "+Ending Disk#\n"
    + r'"(\s?disk\d)$"'
    + "\n"
    + "+Starting (Year)\n"
    + r'"^(\(\d{4}\)\s?)"'
    + "\n"
    + "+Language (En,Fr,...)\n"
    + r"(\s\((Fr|En|De|Es|It|Nl|Pt|Sv|No|Da).*?\))"
)
default_filters = (
    "+Strip brackets\n"
    + r'" ?[\(\[\{][^\)\]\}]+[\)\]\}]"'
    + "\n"
    + r'" "'
    + "\n"
    + "+Strip articles\n"
    + r'"(^(?:(?:the|a|an)\s+)|, the)"'
    + "\n"
    + r'" "'
    + "\n"
    + "+Strip non alphanumeric\n"
    + r'"(?ui)\W"'
    + "\n"
    + r'" "'
)


def get_config_file():
    return os.environ.get("PYFUZZYRENAMER_CONFIG_FILE", DEFAULT_CONFIG_FILE)


CONFIG_FILE = get_config_file()

theConfig = {}


class CustomWindowConfigHandler:
    def __init__(self):
        self.dict = {}

    def SaveValue(self, key, value):
        self.dict[key] = value
        return True

    def RestoreValue(self, key):
        return self.dict.get(key.lower())


thePersistentConfig = CustomWindowConfigHandler()


def get_config():
    return theConfig


def get_persistent_config():
    return thePersistentConfig


def get_default_columns():
    return default_columns


def default():
    theConfig.clear()
    theConfig["view_bottom"] = False
    theConfig["show_log"] = False
    theConfig["show_fullpath"] = False
    theConfig["hide_extension"] = False
    theConfig["match_firstletter"] = False
    theConfig["keep_match_ext"] = False
    theConfig["rename_choice"] = False
    theConfig["keep_original"] = False
    theConfig["source_w_multiple_choice"] = True
    theConfig["folder_sources"] = os.getcwd()
    theConfig["folder_choices"] = os.getcwd()
    theConfig["folder_output"] = ""
    theConfig["filters"] = default_filters
    theConfig["masks"] = default_masks
    theConfig["masks_test"] = default_masks_teststring
    theConfig["filters_test"] = default_filters_teststring
    theConfig["workers"] = cpu_count()
    theConfig["similarityscorer"] = SimilarityScorer.WRATIO
    theConfig["recent_session"] = []
    theConfig["recent_sources"] = []
    theConfig["recent_choices"] = []
    for i in range(0, len(default_columns)):
        theConfig["col%d_order" % (i + 1)] = default_columns[i]["index"]
        theConfig["col%d_size" % (i + 1)] = default_columns[i]["width"] if default_columns[i]["shown"] else 0


def read(config_file=None):
    default()

    # read config file
    try:
        config_file = os.sep.join([os.getcwd(), "config.ini"])
        config = configparser.ConfigParser()
        cfg_file = config.read(CONFIG_FILE or config_file, encoding="utf-8-sig")
        if not len(cfg_file):
            return theConfig
        try:
            theConfig["view_bottom"] = True if config["ui"]["view_bottom"] == "True" else False
        except KeyError:
            pass
        try:
            theConfig["show_log"] = True if config["ui"]["show_log"] == "True" else False
        except KeyError:
            pass
        try:
            theConfig["show_fullpath"] = True if config["global"]["show_fullpath"] == "True" else False
        except KeyError:
            pass
        try:
            theConfig["hide_extension"] = True if config["global"]["hide_extension"] == "True" else False
        except KeyError:
            pass
        try:
            theConfig["keep_match_ext"] = True if config["global"]["keep_match_ext"] == "True" else False
        except KeyError:
            pass
        try:
            theConfig["rename_choice"] = True if config["global"]["rename_choice"] == "True" else False
        except KeyError:
            pass
        try:
            theConfig["keep_original"] = True if config["global"]["keep_original"] == "True" else False
        except KeyError:
            pass
        try:
            theConfig["match_firstletter"] = True if config["matching"]["match_firstletter"] == "True" else False
        except KeyError:
            pass
        try:
            theConfig["source_w_multiple_choice"] = True if config["matching"]["source_w_multiple_choice"] == "True" else False
        except KeyError:
            pass
        try:
            theConfig["folder_sources"] = config["recent"]["folder_sources"]
        except KeyError:
            pass
        try:
            theConfig["folder_choices"] = config["recent"]["folder_choices"]
        except KeyError:
            pass
        try:
            theConfig["folder_output"] = config["recent"]["folder_output"]
        except KeyError:
            pass
        for i in range(1, 9):
            try:
                f = config["recent"]["recent_session%d" % i]
                if Path(f).is_file():
                    theConfig["recent_session"].append(f)
            except KeyError:
                pass
        for i in range(1, 9):
            try:
                f = config["recent"]["recent_sources%d" % i]
                if Path(f).is_dir():
                    theConfig["recent_sources"].append(f)
            except KeyError:
                pass
        for i in range(1, 9):
            try:
                f = config["recent"]["recent_choices%d" % i]
                if Path(f).is_dir() or Path(f).is_file():
                    theConfig["recent_choices"].append(f)
            except KeyError:
                pass
        try:
            theConfig["filters"] = config["matching"]["filters"]
        except KeyError:
            pass
        try:
            theConfig["masks"] = config["matching"]["masks"]
        except KeyError:
            pass
        try:
            theConfig["masks_test"] = config["matching"]["masks_test"]
        except KeyError:
            pass
        try:
            theConfig["filters_test"] = config["matching"]["filters_test"]
        except KeyError:
            pass
        try:
            theConfig["workers"] = int(config["matching"]["workers"])
        except KeyError:
            pass
        try:
            theConfig["similarityscorer"] = int(config["matching"]["similarityscorer"])
        except KeyError:
            pass
        for i in range(0, len(default_columns)):
            try:
                theConfig["col%d_order" % (i + 1)] = int(config["ui"]["col%d_order" % (i + 1)])
                theConfig["col%d_size" % (i + 1)] = int(config["ui"]["col%d_size" % (i + 1)])
            except KeyError:
                pass

        try:
            get_persistent_config().dict = {key: value for key, value in config.items("window")}
        except configparser.NoSectionError:
            pass

    except configparser.Error as e:
        logging.error("%s when reading config file '%s'" % (e.args[0], CONFIG_FILE or config_file))
        return theConfig

    masks.FileMasked.masks = masks.CompileMasks(theConfig["masks"])
    filters.FileFiltered.filters = filters.CompileFilters(theConfig["filters"])


def write(config_file=None):
    config = configparser.ConfigParser()
    config.read_dict(
        {
            "global": {
                "show_fullpath": theConfig["show_fullpath"],
                "hide_extension": theConfig["hide_extension"],
                "keep_match_ext": theConfig["keep_match_ext"],
                "keep_original": theConfig["keep_original"],
                "rename_choice": theConfig["rename_choice"],
            },
            "matching": {
                "masks": theConfig["masks"],
                "filters": theConfig["filters"],
                "masks_test": theConfig["masks_test"],
                "filters_test": theConfig["filters_test"],
                "match_firstletter": theConfig["match_firstletter"],
                "source_w_multiple_choice": theConfig["source_w_multiple_choice"],
                "similarityscorer": int(theConfig["similarityscorer"]),
                "workers": theConfig["workers"],
            },
            "recent": {
                "folder_sources": theConfig["folder_sources"],
                "folder_choices": theConfig["folder_choices"],
                "folder_output": theConfig["folder_output"],
            },
            "ui": {"view_bottom": theConfig["view_bottom"], "show_log": theConfig["show_log"],},
            "window": {},
        }
    )
    for i in range(0, len(theConfig["recent_session"])):
        config["recent"]["recent_session%d" % (i + 1)] = theConfig["recent_session"][i]
    for i in range(0, len(theConfig["recent_sources"])):
        config["recent"]["recent_sources%d" % (i + 1)] = theConfig["recent_sources"][i]
    for i in range(0, len(theConfig["recent_choices"])):
        config["recent"]["recent_choices%d" % (i + 1)] = theConfig["recent_choices"][i]

    for i in range(0, len(default_columns)):
        config["ui"]["col%d_order" % (i + 1)] = str(theConfig["col%d_order" % (i + 1)])
        config["ui"]["col%d_size" % (i + 1)] = str(theConfig["col%d_size" % (i + 1)])

    for key, value in get_persistent_config().dict.items():
        config["window"][key] = value

    with open(CONFIG_FILE or config_file, "w") as configfile:
        config.write(configfile)

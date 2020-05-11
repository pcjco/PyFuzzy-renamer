import configparser
import copy
import logging
import os
from multiprocessing import cpu_count
from pathlib import Path

from pyfuzzyrenamer import filters, masks

D_FILENAME = 0
D_MATCH_SCORE = 1
D_MATCHNAME = 2
D_PREVIEW = 3
D_STATUS = 4
D_CHECKED = 5
D_PREVIOUS_FILENAME = 6

DEFAULT_CONFIG_FILE = os.sep.join([os.getcwd(), "pyfuzzyrenamer.ini"])
default_columns = [
    [0, 300, "Source Name"],
    [1, 80, "Similarity(%)"],
    [2, 300, "Closest Match"],
    [3, 300, "Renaming Preview"],
    [4, 100, "Status"],
    [5, 60, "Checked"],
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
    + r'"(^(the|a)\b|, the)"'
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


def get_config():
    return theConfig


def get_default_columns():
    return default_columns


def default():
    theConfig.clear()
    theConfig["show_fullpath"] = False
    theConfig["hide_extension"] = False
    theConfig["match_firstletter"] = False
    theConfig["keep_match_ext"] = False
    theConfig["keep_original"] = False
    theConfig["folder_sources"] = os.getcwd()
    theConfig["folder_choices"] = os.getcwd()
    theConfig["folder_output"] = ""
    theConfig["filters"] = default_filters
    theConfig["masks"] = default_masks
    theConfig["masks_test"] = default_masks_teststring
    theConfig["filters_test"] = default_filters_teststring
    theConfig["window"] = [1000, 800, -10, 0]
    theConfig["workers"] = cpu_count()
    theConfig["recent_session"] = []
    for i in range(0, len(default_columns)):
        theConfig["col%d_order" % (i + 1)] = default_columns[i][0]
        theConfig["col%d_size" % (i + 1)] = default_columns[i][1]


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
            theConfig["keep_original"] = True if config["global"]["keep_original"] == "True" else False
        except KeyError:
            pass
        try:
            theConfig["match_firstletter"] = True if config["global"]["match_firstletter"] == "True" else False
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
        for i in range(0, len(default_columns)):
            try:
                theConfig["col%d_order" % (i + 1)] = int(config["ui"]["col%d_order" % (i + 1)])
                theConfig["col%d_size" % (i + 1)] = int(config["ui"]["col%d_size" % (i + 1)])
            except KeyError:
                pass
        try:
            theConfig["window"][0] = int(config["ui"]["width"])
            theConfig["window"][1] = int(config["ui"]["height"])
            theConfig["window"][2] = int(config["ui"]["left"])
            theConfig["window"][3] = int(config["ui"]["top"])
        except KeyError:
            pass

    except configparser.Error as e:
        logging.error("%s when reading config file '%s'" % (e.args[0], config_file))
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
                "match_firstletter": theConfig["match_firstletter"],
            },
            "matching": {
                "masks": theConfig["masks"],
                "filters": theConfig["filters"],
                "masks_test": theConfig["masks_test"],
                "filters_test": theConfig["filters_test"],
                "workers": theConfig["workers"],
            },
            "recent": {
                "folder_sources": theConfig["folder_sources"],
                "folder_choices": theConfig["folder_choices"],
                "folder_output": theConfig["folder_output"],
            },
            "ui": {
                "width": theConfig["window"][0],
                "height": theConfig["window"][1],
                "left": theConfig["window"][2],
                "top": theConfig["window"][3],
            },
        }
    )
    for i in range(0, len(theConfig["recent_session"])):
        config["recent"]["recent_session%d" % (i + 1)] = theConfig["recent_session"][i]

    for i in range(0, len(default_columns)):
        config["ui"]["col%d_order" % (i + 1)] = str(theConfig["col%d_order" % (i + 1)])
        config["ui"]["col%d_size" % (i + 1)] = str(theConfig["col%d_size" % (i + 1)])

    with open(CONFIG_FILE or config_file, "w") as configfile:
        config.write(configfile)

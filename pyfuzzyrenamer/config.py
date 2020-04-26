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
theConfig = {}


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


def read():
    default()

    INI_show_fullpath_val = theConfig["show_fullpath"]
    INI_hide_extension_val = theConfig["hide_extension"]
    INI_keep_match_ext_val = theConfig["keep_match_ext"]
    INI_keep_original_val = theConfig["keep_original"]
    INI_match_firstletter_val = theConfig["match_firstletter"]
    INI_folder_sources_val = theConfig["folder_sources"]
    INI_folder_choices_val = theConfig["folder_choices"]
    INI_folder_output_val = theConfig["folder_output"]
    INI_filters_val = theConfig["filters"]
    INI_masks_val = theConfig["masks"]
    INI_filters_test_val = theConfig["filters_test"]
    INI_masks_test_val = theConfig["masks_test"]
    INI_window_val = theConfig["window"].copy()
    INI_workers_val = theConfig["workers"]
    INI_col_val = copy.deepcopy(default_columns)
    INI_recent_session_val = theConfig["recent_session"].copy()

    # read config file
    INI_global_cat = {}
    INI_recent_cat = {}
    INI_matching_cat = {}
    INI_ui_cat = {}
    try:
        config_file = os.sep.join([os.getcwd(), "config.ini"])
        config = configparser.ConfigParser()
        cfg_file = config.read(config_file, encoding="utf-8-sig")
        if not len(cfg_file):
            return theConfig
        try:
            INI_global_cat = config["global"]
        except KeyError:
            pass
        try:
            INI_recent_cat = config["recent"]
        except KeyError:
            pass
        try:
            INI_matching_cat = config["matching"]
        except KeyError:
            pass
        try:
            INI_ui_cat = config["ui"]
        except KeyError:
            pass

        try:
            INI_show_fullpath_val = (
                True if INI_global_cat["show_fullpath"] == "True" else False
            )
        except KeyError:
            pass
        try:
            INI_hide_extension_val = (
                True if INI_global_cat["hide_extension"] == "True" else False
            )
        except KeyError:
            pass
        try:
            INI_keep_match_ext_val = (
                True if INI_global_cat["keep_match_ext"] == "True" else False
            )
        except KeyError:
            pass
        try:
            INI_keep_original_val = (
                True if INI_global_cat["keep_original"] == "True" else False
            )
        except KeyError:
            pass
        try:
            INI_match_firstletter_val = (
                True if INI_global_cat["match_firstletter"] == "True" else False
            )
        except KeyError:
            pass
        try:
            INI_folder_sources_val = INI_recent_cat["folder_sources"]
        except KeyError:
            pass
        try:
            INI_folder_choices_val = INI_recent_cat["folder_choices"]
        except KeyError:
            pass
        try:
            INI_folder_output_val = INI_recent_cat["folder_output"]
        except KeyError:
            pass
        for i in range(1, 9):
            try:
                f = INI_recent_cat["recent_session%d" % i]
                if Path(f).is_file():
                    INI_recent_session_val.append(f)
            except KeyError:
                pass
        try:
            INI_filters_val = INI_matching_cat["filters"]
        except KeyError:
            pass
        try:
            INI_masks_val = INI_matching_cat["masks"]
        except KeyError:
            pass
        try:
            INI_masks_test_val = INI_matching_cat["masks_test"]
        except KeyError:
            pass
        try:
            INI_filters_test_val = INI_matching_cat["filters_test"]
        except KeyError:
            pass
        try:
            INI_workers_val = int(INI_matching_cat["workers"])
        except KeyError:
            pass
        for i in range(0, len(default_columns)):
            try:
                INI_col_val[i][0] = int(INI_ui_cat["col%d_order" % (i + 1)])
                INI_col_val[i][1] = int(INI_ui_cat["col%d_size" % (i + 1)])
            except KeyError:
                pass
        try:
            INI_window_val[0] = int(INI_ui_cat["width"])
            INI_window_val[1] = int(INI_ui_cat["height"])
            INI_window_val[2] = int(INI_ui_cat["left"])
            INI_window_val[3] = int(INI_ui_cat["top"])
        except KeyError:
            pass

    except configparser.Error as e:
        logging.error("%s when reading config file '%s'" % (e.args[0], config_file))
        return theConfig

    theConfig["show_fullpath"] = INI_show_fullpath_val
    theConfig["hide_extension"] = INI_hide_extension_val
    theConfig["keep_match_ext"] = INI_keep_match_ext_val
    theConfig["keep_original"] = INI_keep_original_val
    theConfig["match_firstletter"] = INI_match_firstletter_val
    theConfig["folder_sources"] = INI_folder_sources_val
    theConfig["folder_choices"] = INI_folder_choices_val
    theConfig["folder_output"] = INI_folder_output_val
    theConfig["filters"] = INI_filters_val
    theConfig["masks"] = INI_masks_val
    theConfig["filters_test"] = INI_filters_test_val
    theConfig["masks_test"] = INI_masks_test_val
    for i in range(0, len(default_columns)):
        theConfig["col%d_order" % (i + 1)] = INI_col_val[i][0]
        theConfig["col%d_size" % (i + 1)] = INI_col_val[i][1]
    theConfig["workers"] = INI_workers_val
    theConfig["window"] = INI_window_val
    theConfig["recent_session"] = INI_recent_session_val
    masks.FileMasked.masks = masks.CompileMasks(theConfig["masks"])
    filters.FileFiltered.filters = filters.CompileFilters(theConfig["filters"])


def write():
    config_file = os.sep.join([os.getcwd(), "config.ini"])
    config = configparser.ConfigParser()
    config["global"] = {
        "show_fullpath": theConfig["show_fullpath"],
        "hide_extension": theConfig["hide_extension"],
        "keep_match_ext": theConfig["keep_match_ext"],
        "keep_original": theConfig["keep_original"],
        "match_firstletter": theConfig["match_firstletter"],
    }
    config["matching"] = {
        "masks": theConfig["masks"],
        "filters": theConfig["filters"],
        "masks_test": theConfig["masks_test"],
        "filters_test": theConfig["filters_test"],
        "workers": theConfig["workers"],
    }
    config["recent"] = {
        "folder_sources": theConfig["folder_sources"],
        "folder_choices": theConfig["folder_choices"],
        "folder_output": theConfig["folder_output"],
    }
    for i in range(0, len(theConfig["recent_session"])):
        config["recent"]["recent_session%d" % (i + 1)] = theConfig["recent_session"][i]

    ui = {}
    ui["width"] = theConfig["window"][0]
    ui["height"] = theConfig["window"][1]
    ui["left"] = theConfig["window"][2]
    ui["top"] = theConfig["window"][3]
    for i in range(0, len(default_columns)):
        ui["col%d_order" % (i + 1)] = theConfig["col%d_order" % (i + 1)]
        ui["col%d_size" % (i + 1)] = theConfig["col%d_size" % (i + 1)]
    config["ui"] = ui

    with open(config_file, "w") as configfile:
        config.write(configfile)

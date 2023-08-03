import argparse
from pyfuzzyrenamer._version import __version__

theArgs = argparse.Namespace
theArgsParser = argparse.ArgumentParser(prog="pyfuzzyrenamer")
theArgsParser.add_argument('--version', action='version', version='%(prog)s {version}'.format(version=__version__))
theArgsParser.add_argument("--sources", help="directory for sources")
theArgsParser.add_argument("--choices", help="directory for choices")
subparsers = theArgsParser.add_subparsers(dest="mode", help="sub-command help")

parser_rename = subparsers.add_parser("rename", help="rename sources")
parser_report_match = subparsers.add_parser("report_match", help="report best match")
parser_preview_rename = subparsers.add_parser("preview_rename", help="preview renaming")


def get_args():
    return theArgs


def get_argparser():
    return theArgsParser


def read():
    global theArgs
    theArgs = theArgsParser.parse_args()
    return theArgs

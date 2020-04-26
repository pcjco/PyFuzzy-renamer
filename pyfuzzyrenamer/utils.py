import os
import re
import sys
import wx
from pathlib import Path

illegal_chars = r'/?<>\:*|"' if (sys.platform == "win32") else r":"


def GetFileStemAndSuffix(file):
    stem = file.stem
    suffix = file.suffix
    if not file.suffix[1:].isalnum():
        stem = file.name
        suffix = ""
    return stem, suffix


def group(L):

    first = last = L[0]
    for n in L[1:]:
        if n - 1 == last:  # Part of the group, bump the end
            last = n
        else:  # Not part of the group, yield current group and start a new
            yield first, last
            first = last = n
    yield first, last  # Yield the last group


def shorten_path(file_path, length):
    parts = Path(file_path).parts
    if len(parts[-1]) >= length:
        return parts[-1]
    if len(parts) > 2:
        for i in range(1, len(parts) - 1):
            ret = parts[0] + "..." + os.sep + os.sep.join(parts[i:])
            if len(ret) <= length:
                return ret
    return ret


def strip_illegal_chars(s):
    s = re.sub(r"(?<=\S)[" + illegal_chars + r"](?=\S)", "-", s)
    s = re.sub(r"\s?[" + illegal_chars + r"]\s?", " ", s)
    return s


def strip_extra_whitespace(s):
    return " ".join(s.split()).strip()


def get_selected_items(list_control):
    """
    Gets the selected items for the list control.
    Selection is returned as a list of selected indices,
    low to high.
    """

    selection = []

    # start at -1 to get the first selected item
    current = -1
    while True:
        next = GetNextSelected(list_control, current)
        if next == -1:
            return selection

        selection.append(next)
        current = next


def GetNextSelected(list_control, current):
    """Returns next selected item, or -1 when no more"""

    return list_control.GetNextItem(current, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)


def ClipBoardFiles():
    ret = []
    try:
        if wx.TheClipboard.Open():
            if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_TEXT)):
                do = wx.TextDataObject()
                wx.TheClipboard.GetData(do)
                ret = do.GetText().splitlines()
            elif wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_FILENAME)):
                do = wx.FileDataObject()
                wx.TheClipboard.GetData(do)
                filenames = do.GetFilenames()
                for f in filenames:
                    try:
                        fp = Path(f)
                        if fp.is_dir():
                            for fp2 in fp.resolve().glob("*"):
                                if fp2.is_file():
                                    ret.append(str(fp2))
                        else:
                            ret.append(f)
                    except (OSError, IOError):
                        pass
            wx.TheClipboard.Close()
    except (OSError, IOError):
        pass
    return ret
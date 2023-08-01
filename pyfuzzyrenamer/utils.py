import math
import os
import re
import sys
import wx
import zipfile
import csv
from xml.etree.ElementTree import iterparse
from pathlib import Path
import subprocess
from collections import defaultdict
try:
    from win32com.shell import shell, shellcon
except ImportError:
    pass


illegal_chars = r'/?<>\:*|"' if (sys.platform == "win32") else r":"


def GetFileStemAndSuffix(file):
    stem = file.stem
    suffix = file.suffix if file.suffix != ".noext" else ""
    return stem, suffix


def GetFileParentStemAndSuffix(file):
    p = str(file.parent)
    parent = (p + os.sep) if p != "." else ""
    return (parent,) + GetFileStemAndSuffix(file)


def group(L):

    first = last = L[0]
    for n in L[1:]:
        if n - 1 == last:  # Part of the group, bump the end
            last = n
        else:  # Not part of the group, yield current group and start a new
            yield first, last
            first = last = n
    yield first, last  # Yield the last group


def shorten_path(filename, length):
    l = len(filename)
    if l < length:
        return filename
    fp = Path(filename)
    parts = fp.parts
    if len(parts) > 2:
        for i in range(1, len(parts) - 1):
            ret = parts[0] + "..." + os.sep + os.sep.join(parts[i:])
            if len(ret) <= length:
                return ret
    ret = filename[: math.ceil(l / 2) - 2] + "..." + filename[-math.floor(l / 2) + 1 :]
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
    item = -1
    while True:
        item = GetNextSelected(list_control, item)
        if item == -1:
            return selection

        selection.append(item)


def GetNextSelected(list_control, item):
    """Returns next selected item, or -1 when no more"""

    return list_control.GetNextItem(item, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)


def get_focused_items(list_control):
    """
    Gets the focused items for the list control.
    Selection is returned as a list of focused indices,
    low to high.
    """

    selection = []

    # start at -1 to get the first selected item
    item = -1
    while True:
        item = GetNextFocused(list_control, item)
        if item == -1:
            return selection

        selection.append(item)


def GetNextFocused(list_control, item):
    """Returns next selected item, or -1 when no more"""

    return list_control.GetNextItem(item, wx.LIST_NEXT_ALL, wx.LIST_STATE_FOCUSED)


def ClipBoardFiles():
    ret = []
    try:
        if wx.TheClipboard.Open():
            if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_TEXT)):
                do = wx.TextDataObject()
                wx.TheClipboard.GetData(do)
                filenames = do.GetText().splitlines()
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

    
def open_file(filename):
    try:
        if sys.platform.startswith('linux'):
            subprocess.Popen(['xdg-open', filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        elif sys.platform.startswith('win32'):
            os.startfile(filename)
        elif sys.platform.startswith('cygwin'):
            os.startfile(filename)
        elif sys.platform.startswith('darwin'):
            subprocess.Popen(['open', filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            subprocess.Popen(['xdg-open', filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except:
        wx.LogMessage("Could not open file %s" % (filename))

        
def launch_file_explorer(pathes):
    '''Given a list of Path up one File Explorer window
       per folder with all the child files selected'''
    
    folders = defaultdict(list)
    for p in pathes:
        folders[str(p.parent)].append(p.name)

    for path, files in folders.items():
        folder_pidl = shell.SHILCreateFromPath(path,0)[0]
        desktop = shell.SHGetDesktopFolder()
        shell_folder = desktop.BindToObject(folder_pidl, None, shell.IID_IShellFolder)
        name_to_item_mapping = dict([(desktop.GetDisplayNameOf(item, 0), item) for item in shell_folder])
        to_show = []
        for file in files:
            if not file in name_to_item_mapping:
                wx.LogMessage('File: "%s" not found in "%s"' % (file, path))
                continue
            to_show.append(name_to_item_mapping[file])
        shell.SHOpenFolderAndSelectItems(folder_pidl, to_show, 0)

        
def read_xlsx(fname, sheet = None):
    rows = []
    try:
        z = zipfile.ZipFile(fname)
        if 'xl/sharedStrings.xml' in z.namelist():
            # Get shared strings
            strings = [element.text for event, element
                       in iterparse(z.open('xl/sharedStrings.xml')) 
                       if element.tag.endswith('}t')]
        sheets = { element.attrib['name']:element.attrib['sheetId'] for event,element in iterparse(z.open('xl/workbook.xml'))
                                          if element.tag.endswith('}sheet') }
        row = {}
        value = ''

        if sheet in sheets:
            sheetfile = 'xl/worksheets/sheet'+sheets[sheet]+'.xml'
        else:
            sheetfile = 'xl/worksheets/sheet1.xml'
        for event, element in iterparse(z.open(sheetfile)):
            # get value or index to shared strings
            if element.tag.endswith('}v') or element.tag.endswith('}t'):
                value = element.text
            # If value is a shared string, use value as an index
            if element.tag.endswith('}c'):
                if element.attrib.get('t') == 's':
                    value = strings[int(value)]
                # split the row/col information so that the row leter(s) can be separate
                letter = re.sub('\d','',element.attrib['r'])
                row[letter] = value
                value = ''
            if element.tag.endswith('}row'):
                rows.append(row)
                row = {}
    except:
        wx.LogMessage("Could not open file %s" % (fname))
    return rows

def read_csv(fname):
    rows = []
    try:
        with open(fname, 'r') as csvfile:
            reader = csv.DictReader(csvfile, fieldnames=['A', 'B'])
    except:
        wx.LogMessage("Could not open file %s" % (fname))
    return rows

def versiontuple(v):
   filled = []
   for point in v.split("."):
      filled.append(point.zfill(8))
   return tuple(filled)    

#!/usr/bin/python

import os
import re
import sys
import logging
import os.path
import wx
import wx.adv
import wx.aui
import wx.html
import wx.lib.mixins.listctrl as listmix
from wx.lib.embeddedimage import PyEmbeddedImage
from pathlib import Path
import configparser
import fuzzywuzzy.fuzz
import fuzzywuzzy.process
import pickle as pickle


class data_struct(object):
    FILENAME = 0
    MATCH_SCORE = 1
    MATCHNAME = 2
    PREVIEW = 3
    PREVIOUS_FILENAME = 4


glob_choices = set()
forced_match_id = {}
candidates = {}

illegal_chars = r'/?<>\:*|"' if (sys.platform == "win32") else r':'
default_masks_teststring = '(1986) Hitchhiker\'s Guide to the Galaxy, The (AGA) Disk1'
default_filters_teststring = 'Hitchhiker\'s Guide to the Galaxy, The (AGA)'
default_masks = '+Ending Disk#\n' + \
                r'"(\s?disk\d)$"' + '\n' + \
                '+Starting (Year)\n' + \
                r'"^(\(\d{4}\)\s?)"'
default_filters = '+Strip brackets\n' + \
                  r'" ?[\(\[\{][^\)\]\}]+[\)\]\}]"' + '\n' + \
                  r'" "' + '\n' + \
                  '+Strip articles\n' + \
                  r'"(^(the|a)\b|, the)"' + '\n' + \
                  r'" "' + '\n' + \
                  '+Strip non alphanumeric\n' + \
                  r'"(?ui)\W"' + '\n' + \
                  r'" "'


def strip_illegal_chars(s):
    s = re.sub(r'(?<=\S)[' + illegal_chars + r'](?=\S)', '-', s)
    s = re.sub(r'\s?[' + illegal_chars + r']\s?', ' ', s)
    return s

def strip_extra_whitespace(s):
    return ' '.join(s.split()).strip()


def mySimilarityScorer(s1, s2):
    return fuzzywuzzy.fuzz.WRatio(s1, s2,
                                  force_ascii=False, full_process=False)


def GetFileStemAndSuffix(file):
    stem = file.stem
    suffix = file.suffix
    if not file.suffix[1:].isalnum():
        stem = file.name
        suffix = ''
    return stem, suffix

def filter_processed(file, filters):
    stem, suffix = GetFileStemAndSuffix(file)
    ret = stem
    # convert to lowercase.
    ret = ret.lower()
    # remove leading and trailing whitespaces.
    ret = ret.strip()
    # apply filters
    for filter in filters:
        ret = filter[0].sub(filter[1], ret)
    ret = ' '.join(ret.split())
    if stem != ret:
        wx.LogMessage('String filtered : %s --> %s' % (stem, ret))
    return ret


def group(L):
    first = last = L[0]
    for n in L[1:]:
        if n - 1 == last:  # Part of the group, bump the end
            last = n
        else:  # Not part of the group, yield current group and start a new
            yield first, last
            first = last = n
    yield first, last  # Yield the last group


def mask_processed(file, masks, filters, applyFilters=True):
    stem, suffix = GetFileStemAndSuffix(file)
    ret = stem
    # apply masks
    interval = set()
    for mask in masks:
        matches = mask.search(ret)
        if matches:
            for groupNum in range(0, len(matches.groups())):
                groupNum = groupNum + 1
                interval = set.union(interval, {*range(matches.start(groupNum), matches.end(groupNum) + 1)})
    interval_lst = sorted(interval)
    post = ''
    pre = ''
    middle = stem
    if interval_lst:
        grp = list(group(interval_lst))
        if grp[0][0] == 0:
            pre = stem[grp[0][0]:grp[0][1]]
            if len(grp) > 1 and grp[-1][1] == len(stem):
                post = stem[grp[-1][0]:grp[-1][1]]
                middle = stem[grp[0][1]:grp[-1][0]]
            else:
                middle = stem[grp[0][1]:]
        elif grp[-1][1] == len(stem):
            post = stem[grp[-1][0]:grp[-1][1]]
            middle = stem[:grp[-1][0]]
    if applyFilters:
        # convert to lowercase.
        middle = middle.lower()
        # remove leading and trailing whitespaces.
        middle = middle.strip()
        # apply filters
        for filter in filters:
            middle = filter[0].sub(filter[1], middle)
        middle = ' '.join(middle.split())
    if stem != middle:
        wx.LogMessage('String masked : %s --> [%s]%s[%s]' % (stem, pre, middle, post))
    return pre, middle, post


def fuzz_processor(file):
    if type(file).__name__ == 'FileFiltered':
        return file.filtered
    elif type(file).__name__ == 'FileMasked':
        return file.masked[1]


def get_matches(sources, progress):
    ret = []
    Qmatch_firstletter = config_dict['match_firstletter']
    count = 0
    for f in sources:
        count += 1
        cancelled = not progress.Update(count, '')[0]
        if cancelled:
            return ret
        if not candidates:
            ret.append(None)
            continue
        f_masked = FileMasked(f)
        if not f_masked.masked[1]:
            ret.append(None)
            continue
        if Qmatch_firstletter:
            first_letter = f_masked.masked[1][0]
            if first_letter in candidates.keys():
                ret.append(FileMatch(f, fuzzywuzzy.process.extract(f_masked, candidates[first_letter], scorer=mySimilarityScorer, processor=fuzz_processor, limit=10)))
            else:
                ret.append(None)
        else:
            ret.append(FileMatch(f, fuzzywuzzy.process.extract(f_masked, candidates['all'], scorer=mySimilarityScorer, processor=fuzz_processor, limit=10)))
    return ret


def get_match(source):
    ret = None
    if not candidates:
        return ret
    f_masked = FileMasked(source)
    if not f_masked.masked[1]:
        return ret

    if config_dict['match_firstletter']:
        first_letter = f_masked.masked[1][0]
        if first_letter in candidates.keys():
            ret = fuzzywuzzy.process.extract(f_masked, candidates[first_letter], scorer=mySimilarityScorer, processor=fuzz_processor, limit=10)
    else:
        ret = fuzzywuzzy.process.extract(f_masked, candidates['all'], scorer=mySimilarityScorer, processor=fuzz_processor, limit=10)
    return ret


def getRenamePreview(input, match):
    if not match:
        return None
    Qkeep_match_ext = config_dict['keep_match_ext']
    stem, suffix = GetFileStemAndSuffix(match)
    match_clean = strip_extra_whitespace(strip_illegal_chars(stem))
    if Qkeep_match_ext:
        match_clean += suffix
    f_masked = FileMasked(input)
    stem, suffix = GetFileStemAndSuffix(input)
    return Path(os.path.join(str(input.parent), f_masked.masked[0] + match_clean + f_masked.masked[2]) + suffix)


def RefreshCandidates():
    global candidates
    candidates.clear()
    candidates['all'] = [FileFiltered(f) for f in glob_choices]
    if config_dict['match_firstletter']:
        for word in candidates['all']:
            first_letter = word.filtered[0]
            if first_letter in candidates.keys():
                candidates[first_letter].append(word)
            else:
                candidates[first_letter] = [word]


def CompileFilters(config):
    ret = []
    lines = config.splitlines()
    it = iter(lines)
    for l1, l2, l3 in zip(it, it, it):
        if l1.startswith('+'):
            try:
                ret.append((re.compile(l2.strip()[1:-1]), l3.strip()[1:-1], re.IGNORECASE))
            except re.error:
                pass
    return ret


def CompileMasks(config):
    ret = []
    lines = config.splitlines()
    it = iter(lines)
    for l1, l2 in zip(it, it):
        if l1.startswith('+'):
            try:
                ret.append(re.compile(l2.strip()[1:-1], re.IGNORECASE))
            except re.error:
                pass
    return ret


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
                            for fp2 in fp.resolve().glob('*'):
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


class FileMatch:
    def __init__(self, file, match_results):
        self.file = file
        self.match_results = match_results


class FileFiltered:
    filters = []

    def __init__(self, file):
        self.file = file
        self.filtered = filter_processed(file, FileFiltered.filters)


class FileMasked:
    masks = []

    def __init__(self, file):
        self.file = file
        self.masked = mask_processed(file, FileMasked.masks, FileFiltered.filters)

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

    return list_control.GetNextItem(current,
                            wx.LIST_NEXT_ALL,
                            wx.LIST_STATE_SELECTED)

class FuzzyRenamerFileDropTarget(wx.FileDropTarget):
    def __init__(self, window):
        wx.FileDropTarget.__init__(self)
        self.window = window

    def OnDropFiles(self, x, y, filenames):
        Qsources = self.SourcesOrChoices(self.window)
        files = []
        for f in filenames:
            try:
                fp = Path(f)
                if fp.is_file():
                    files.append(f)
                elif fp.is_dir():
                    for fp2 in fp.resolve().glob('*'):
                        if fp2.is_file():
                            files.append(str(fp2))
            except (OSError, IOError):
                pass
        if Qsources:
            self.window.AddSourceFromFiles(files)
        else:
            self.window.AddChoicesFromFiles(files)
        return True

    def SourcesOrChoices(self, parent, question="Add the files to source or choice list?", caption='Drag&Drop question'):
        dlg = wx.MessageDialog(parent, question, caption, wx.YES_NO | wx.ICON_QUESTION)
        dlg.SetYesNoLabels('Sources', 'Choices')
        result = dlg.ShowModal() == wx.ID_YES
        dlg.Destroy()
        return result


class FuzzyRenamerListCtrl(wx.ListCtrl, listmix.ColumnSorterMixin):

    def __init__(self, parent, ID=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.ColumnSorterMixin.__init__(self, 4)
        self.EnableCheckBoxes()
        self.Bind(wx.EVT_CHAR, self.onKeyPress)
        self.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnBeginLabelEdit)
        self.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnEndLabelEdit)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.RightClickCb)
        self.Bind(wx.EVT_LIST_ITEM_CHECKED, self.CheckedCb)
        self.Bind(wx.EVT_LIST_ITEM_UNCHECKED, self.UncheckedCb)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.SelectCb)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.UnselectCb)

        self.InsertColumn(0, 'Source Name', width=300)
        self.InsertColumn(1, 'Similarity(%)', width=80)
        self.InsertColumn(2, 'Closest Match', width=300)
        self.InsertColumn(3, 'Renaming Preview', width=300)

        self.listdata = {}
        self.itemDataMap = self.listdata

    def onKeyPress(self, event):
        global glob_choices
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_SPACE:
            index = self.GetFirstSelected()
            check = True
            if index != -1:
                if self.IsItemChecked(index):
                    check = False
            if self.GetSelectedItemCount() == 1:
                check = not check
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            while index != -1:
                f = self.GetItemFont(index)
                if not f.IsOk():
                    f = self.GetFont()
                self.CheckItem(index, check)
                if check:
                    font.SetStyle(wx.FONTSTYLE_NORMAL)
                else:
                    font.SetStyle(wx.FONTSTYLE_ITALIC)
                font.SetWeight(f.GetWeight())
                self.SetItemFont(index, font)
                index = self.GetNextSelected(index)
        elif keycode == wx.WXK_F2:
            if self.GetSelectedItemCount() == 1:
                index = self.GetFirstSelected()
        elif keycode == wx.WXK_CONTROL_A:
            item = -1
            while 1:
                item = self.GetNextItem(item)
                if item == -1:
                    break
                self.SetItemState(item, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
        elif keycode == wx.WXK_DELETE:
            selected = get_selected_items(self)

            selected.reverse()  # Delete all the items, starting with the last item
            for row_id in selected:
                pos = self.GetItemData(row_id)  # 0-based unsorted index
                self.DeleteItem(row_id)
                del self.listdata[pos]
        elif keycode == wx.WXK_CONTROL_V:
            files = ClipBoardFiles()
            if files:
                dlg = wx.MessageDialog(self.GetParent().GetParent(), "Add the files to source or choice list?", 'Paste question', wx.YES_NO | wx.ICON_QUESTION)
                dlg.SetYesNoLabels('Sources', 'Choices')
                Qsources = dlg.ShowModal() == wx.ID_YES
                dlg.Destroy()
                if Qsources:
                    self.GetParent().GetParent().GetParent().AddSourceFromFiles(files)
                else:
                    self.GetParent().GetParent().GetParent().AddChoicesFromFiles(files)

        if keycode:
            event.Skip()

    def RightClickCb(self, event):
        global forced_match_id
        forced_match_id.clear()
        if not self.GetSelectedItemCount() or self.GetSelectedItemCount() > 1:
            return
        if not candidates:
            return
        pos = event.GetItem().GetData()
        matches = get_match(self.listdata[pos][data_struct.FILENAME])
        if matches:
            menu = wx.Menu()
            for match in matches:
                id = wx.NewIdRef()
                stem, suffix = GetFileStemAndSuffix(match[0].file)
                menu.Append(id.GetValue(), "[%d%%] %s" % (match[1], stem))
                self.Bind(wx.EVT_MENU, self.MenuSelectionCb, id=id)
                forced_match_id[id] = (event.GetIndex(), match[0].file)

            self.PopupMenu(menu, event.GetPoint())
            menu.Destroy()

    def CheckedCb(self, event):
        index = event.GetIndex()
        f = self.GetItemFont(index)
        if not f.IsOk():
            f = self.GetFont()
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        font.SetStyle(wx.FONTSTYLE_NORMAL)
        font.SetWeight(f.GetWeight())
        self.SetItemFont(index, font)

    def UncheckedCb(self, event):
        index = event.GetIndex()
        f = self.GetItemFont(index)
        if not f.IsOk():
            f = self.GetFont()
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        font.SetStyle(wx.FONTSTYLE_ITALIC)
        font.SetWeight(f.GetWeight())
        self.SetItemFont(index, font)

    def SelectCb(self, event):
        nb = self.GetSelectedItemCount()
        if nb:
            self.GetParent().GetParent().GetParent().GetParent().statusbar.SetStatusText('%d item(s) selected' % self.GetSelectedItemCount(), 1)
        else:
            self.GetParent().GetParent().GetParent().GetParent().statusbar.SetStatusText('', 1)

    def UnselectCb(self, event):
        nb = self.GetSelectedItemCount()
        if nb:
            self.GetParent().GetParent().GetParent().GetParent().statusbar.SetStatusText('%d item(s) selected' % self.GetSelectedItemCount(), 1)
        else:
            self.GetParent().GetParent().GetParent().GetParent().statusbar.SetStatusText('', 1)

    def MenuSelectionCb(self, event):
        row_id, forced_match = forced_match_id[event.GetId()]
        forced_match_id.clear()
        pos = self.GetItemData(row_id)  # 0-based unsorted index
        similarity = mySimilarityScorer(FileMasked(self.listdata[pos][data_struct.FILENAME]).masked[1], FileFiltered(forced_match).filtered)
        self.listdata[pos][data_struct.MATCH_SCORE] = similarity
        self.listdata[pos][data_struct.MATCHNAME] = forced_match
        self.listdata[pos][data_struct.PREVIEW] = getRenamePreview(self.listdata[pos][data_struct.FILENAME], forced_match)

        Qview_fullpath = config_dict['show_fullpath']
        Qhide_extension = config_dict['hide_extension']
        self.SetItem(row_id, data_struct.MATCH_SCORE, str(self.listdata[pos][data_struct.MATCH_SCORE]))
        stem, suffix = GetFileStemAndSuffix(self.listdata[pos][data_struct.MATCHNAME])
        self.SetItem(row_id, data_struct.MATCHNAME, str(self.listdata[pos][data_struct.MATCHNAME]) if Qview_fullpath else (stem if Qhide_extension else self.listdata[pos][data_struct.MATCHNAME].name))
        stem, suffix = GetFileStemAndSuffix(self.listdata[pos][data_struct.PREVIEW])
        self.SetItem(row_id, data_struct.PREVIEW, str(self.listdata[pos][data_struct.PREVIEW]) if Qview_fullpath else (stem if Qhide_extension else self.listdata[pos][data_struct.PREVIEW].name))

        f = self.GetItemFont(row_id)
        if not f.IsOk():
            f = self.GetFont()
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        font.SetStyle(f.GetStyle())
        self.SetItemFont(row_id, font)

    def OnBeginLabelEdit(self, event):
        event.Allow()
        if config_dict['show_fullpath']:
            d = Path(event.GetLabel())
            (self.GetEditControl()).SetValue(d.name)

    def OnEndLabelEdit(self, event):
        if event.IsEditCancelled() or not event.GetLabel():
            event.Veto()
            return
        row_id = event.GetIndex()
        pos = self.GetItemData(row_id)  # 0-based unsorted index
        new_name = event.GetLabel()
        old_path = self.listdata[pos][data_struct.FILENAME]
        old_name = old_path.name
        new_name_clean = strip_extra_whitespace(strip_illegal_chars(new_name))

        event.Veto()  # do not allow further process as we will edit ourself the item label

        if new_name != new_name_clean:
            wx.LogMessage('String cleaned : %s --> %s' % (new_name, new_name_clean))

        if new_name_clean != old_name:
            old_file = str(old_path)
            new_file = os.path.join(str(old_path.parent), new_name_clean)
            new_path = Path(new_file)

            try:
                if old_path.is_file():
                    os.rename(old_file, new_file)
                    wx.LogMessage('Renaming : %s --> %s' % (old_file, new_file))

                    Qview_fullpath = config_dict['show_fullpath']
                    Qhide_extension = config_dict['hide_extension']

                    new_match = get_match(new_path)
                    if new_match:
                        self.listdata[pos] = [new_path, new_match[0][1], new_match[0][0].file, getRenamePreview(new_path, new_match[0][0].file), old_path]
                        self.SetItem(row_id, data_struct.MATCH_SCORE, str(self.listdata[pos][data_struct.MATCH_SCORE]))
                        stem, suffix = GetFileStemAndSuffix(self.listdata[pos][data_struct.MATCHNAME])
                        self.SetItem(row_id, data_struct.MATCHNAME, str(self.listdata[pos][data_struct.MATCHNAME]) if Qview_fullpath else (stem if Qhide_extension else self.listdata[pos][data_struct.MATCHNAME].name))
                        stem, suffix = GetFileStemAndSuffix(self.listdata[pos][data_struct.PREVIEW])
                        self.SetItem(row_id, data_struct.PREVIEW, str(self.listdata[pos][data_struct.PREVIEW]) if Qview_fullpath else (stem if Qhide_extension else self.listdata[pos][data_struct.PREVIEW].name))
                    else:
                        self.listdata[pos] = [new_path, 0, '', '', old_path]
                        self.SetItem(row_id, data_struct.MATCH_SCORE, '')
                        self.SetItem(row_id, data_struct.MATCHNAME, '')
                        self.SetItem(row_id, data_struct.PREVIEW, '')

                    stem, suffix = GetFileStemAndSuffix(self.listdata[pos][data_struct.FILENAME])
                    self.SetItem(row_id, data_struct.FILENAME, str(self.listdata[pos][data_struct.FILENAME]) if Qview_fullpath else (stem if Qhide_extension else self.listdata[pos][data_struct.FILENAME].name))

            except (OSError, IOError):
                wx.LogMessage('Error when renaming : %s --> %s' % (old_file, new_file))
        else:
            wx.LogMessage('Not renaming %s (same name)' % (old_name))

    def GetListCtrl(self):
        return self

    def RefreshList(self):
        Qview_fullpath = config_dict['show_fullpath']
        Qhide_extension = config_dict['hide_extension']

        row_id = -1
        while True:
            row_id = self.GetNextItem(row_id)
            if row_id == -1:
                break
            pos = self.GetItemData(row_id)  # 0-based unsorted index
            data = self.listdata[pos]
            filepath = str(data[data_struct.FILENAME])
            stem, suffix = GetFileStemAndSuffix(data[data_struct.FILENAME])
            self.SetItem(row_id, data_struct.FILENAME, filepath if Qview_fullpath else (stem if Qhide_extension else data[data_struct.FILENAME].name))
            if data[data_struct.MATCHNAME]:
                self.SetItem(row_id, data_struct.MATCH_SCORE, str(data[data_struct.MATCH_SCORE]))
                stem, suffix = GetFileStemAndSuffix(data[data_struct.MATCHNAME])
                self.SetItem(row_id, data_struct.MATCHNAME, str(data[data_struct.MATCHNAME]) if Qview_fullpath else (stem if Qhide_extension else data[data_struct.MATCHNAME].name))
                stem, suffix = GetFileStemAndSuffix(data[data_struct.PREVIEW])
                self.SetItem(row_id, data_struct.PREVIEW, str(data[data_struct.PREVIEW]) if Qview_fullpath else (stem if Qhide_extension else data[data_struct.PREVIEW].name))
            else:
                self.SetItem(row_id, data_struct.MATCH_SCORE, '')
                self.SetItem(row_id, data_struct.MATCHNAME, '')
                self.SetItem(row_id, data_struct.PREVIEW, '')

    def AddToList(self, newdata):
        Qview_fullpath = config_dict['show_fullpath']
        Qhide_extension = config_dict['hide_extension']

        index = 0 if not self.listdata else sorted(self.listdata.keys())[-1] + 1  # start indexing after max index
        row_id = self.GetItemCount()

        for data in newdata:

            # Treat duplicate file
            stem, suffix = GetFileStemAndSuffix(data[data_struct.FILENAME])
            item_name = str(data[data_struct.FILENAME]) if Qview_fullpath else (stem if Qhide_extension else data[data_struct.FILENAME].name)
            found = self.FindItem(-1, item_name)
            if found != -1:
                continue

            self.InsertItem(row_id, item_name)
            if data[data_struct.MATCHNAME]:
                self.SetItem(row_id, data_struct.MATCH_SCORE, str(data[data_struct.MATCH_SCORE]))
                stem, suffix = GetFileStemAndSuffix(data[data_struct.MATCHNAME])
                self.SetItem(row_id, data_struct.MATCHNAME, str(data[data_struct.MATCHNAME]) if Qview_fullpath else (stem if Qhide_extension else data[data_struct.MATCHNAME].name))
                stem, suffix = GetFileStemAndSuffix(data[data_struct.PREVIEW])
                self.SetItem(row_id, data_struct.PREVIEW, str(data[data_struct.PREVIEW]) if Qview_fullpath else (stem if Qhide_extension else data[data_struct.PREVIEW].name))
            self.SetItemData(row_id, index)
            self.CheckItem(row_id, True)
            self.listdata[index] = data
            row_id += 1
            index += 1

    def OnSortOrderChanged(self):
        row_id = self.GetFirstSelected()
        if row_id != -1:
            self.EnsureVisible(row_id)

class MainPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS)

        self.parent = parent

        self.mgr = wx.aui.AuiManager()
        self.mgr.SetManagedWindow(self)

        panel_top = wx.Panel(parent=self)
        panel_list = wx.Panel(parent=panel_top)
        panel_listbutton = wx.Panel(parent=panel_list)

        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_sizer.Add(panel_list, 1, wx.EXPAND)
        panel_top.SetSizer(top_sizer)

        btn_add_source_from_files = wx.Button(panel_listbutton, label="Sources")
        btn_add_source_from_files.SetBitmap(AddFile_16_PNG.GetBitmap(), wx.LEFT)
        btn_add_source_from_files.SetToolTip("Add sources from files")

        btn_add_choice_from_file = wx.Button(panel_listbutton, label="Choices")
        btn_add_choice_from_file.SetBitmap(AddFile_16_PNG.GetBitmap(), wx.LEFT)
        btn_add_choice_from_file.SetToolTip("Add choices from files")

        btn_run = wx.Button(panel_listbutton, label="Best match")
        btn_run.SetBitmap(ProcessMatch_16_PNG.GetBitmap(), wx.LEFT)
        btn_run.SetToolTip("Find best choice for each source")

        btn_reset = wx.Button(panel_listbutton, label="Reset")
        btn_reset.SetBitmap(Reset_16_PNG.GetBitmap(), wx.LEFT)
        btn_reset.SetToolTip("Reset source and choice lists")

        btn_filters = wx.Button(panel_listbutton, label="Masks && Filters")
        btn_filters.SetBitmap(Filters_16_PNG.GetBitmap(), wx.LEFT)
        btn_filters.SetToolTip("Edit list of masks and filters")

        btn_ren = wx.Button(panel_listbutton, label="Rename")
        btn_ren.SetBitmap(Rename_16_PNG.GetBitmap(), wx.LEFT)
        btn_ren.SetToolTip("Rename sources")

        btn_undo = wx.Button(panel_listbutton, label="Undo")
        btn_undo.SetBitmap(Undo_16_PNG.GetBitmap(), wx.LEFT)
        btn_undo.SetToolTip("Undo last rename")

        panel_listbutton_sizer = wx.BoxSizer(wx.HORIZONTAL)
        panel_listbutton_sizer.Add(btn_add_source_from_files, 0, wx.ALL, 1)
        panel_listbutton_sizer.Add(btn_add_choice_from_file, 0, wx.ALL, 1)
        panel_listbutton_sizer.Add(btn_filters, 0, wx.ALL, 1)
        panel_listbutton_sizer.Add(btn_run, 0, wx.ALL, 1)
        panel_listbutton_sizer.Add(btn_reset, 0, wx.ALL, 1)
        panel_listbutton_sizer.Add(btn_ren, 0, wx.ALL, 1)
        panel_listbutton_sizer.Add(btn_undo, 0, wx.ALL, 1)
        panel_listbutton.SetSizer(panel_listbutton_sizer)

        self.list_ctrl = FuzzyRenamerListCtrl(panel_list, size=(-1, -1), style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_EDIT_LABELS)

        file_drop_target = FuzzyRenamerFileDropTarget(self)
        self.SetDropTarget(file_drop_target)

        panel_list_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_list_sizer.Add(panel_listbutton, 0, wx.EXPAND | wx.ALL, 0)
        panel_list_sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 0)
        panel_list.SetSizer(panel_list_sizer)

        panel_log = wx.Panel(parent=self)

        log = wx.TextCtrl(panel_log, -1, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        wx.Log.SetActiveTarget(wx.LogTextCtrl(log))

        log_sizer = wx.BoxSizer()
        log_sizer.Add(log, 1, wx.EXPAND | wx.ALL, 5)
        panel_log.SetSizer(log_sizer)

        self.mgr.AddPane(panel_top, wx.aui.AuiPaneInfo().Name("pane_list").CenterPane())
        self.mgr.AddPane(panel_log, wx.aui.AuiPaneInfo().CloseButton(True).Name("pane_log").Caption("Log").FloatingSize(-1, 200).BestSize(-1, 200).MinSize(-1, 120).Bottom())
        self.mgr.Update()
        self.Bind(wx.EVT_BUTTON, self.OnRun, btn_run)
        self.Bind(wx.EVT_BUTTON, self.OnRename, btn_ren)
        self.Bind(wx.EVT_BUTTON, self.OnReset, btn_reset)
        self.Bind(wx.EVT_BUTTON, self.OnFilters, btn_filters)
        self.Bind(wx.EVT_BUTTON, self.OnUndo, btn_undo)
        self.Bind(wx.EVT_BUTTON, self.OnAddSourceFromFiles, btn_add_source_from_files)
        self.Bind(wx.EVT_BUTTON, self.OnAddChoicesFromFiles, btn_add_choice_from_file)

    def OnViewFullPath(self, evt):
        global config_dict
        item = self.parent.GetMenuBar().FindItemById(evt.GetId())
        config_dict['show_fullpath'] = item.IsChecked()
        write_config(config_dict)
        self.parent.hide_extension.Enable(not config_dict['show_fullpath'])
        self.list_ctrl.RefreshList()

    def OnHideExtension(self, evt):
        global config_dict
        item = self.parent.GetMenuBar().FindItemById(evt.GetId())
        config_dict['hide_extension'] = item.IsChecked()
        write_config(config_dict)
        self.list_ctrl.RefreshList()

    def OnKeepMatchExtension(self, evt):
        global config_dict
        item = self.parent.GetMenuBar().FindItemById(evt.GetId())
        config_dict['keep_match_ext'] = item.IsChecked()
        write_config(config_dict)
        for index in self.list_ctrl.listdata.keys():
            self.list_ctrl.listdata[index][data_struct.PREVIEW] = getRenamePreview(self.list_ctrl.listdata[index][data_struct.FILENAME], self.list_ctrl.listdata[index][data_struct.MATCHNAME])
        self.list_ctrl.RefreshList()

    def OnMatchFirstLetter(self, evt):
        global config_dict
        item = self.parent.GetMenuBar().FindItemById(evt.GetId())
        config_dict['match_firstletter'] = item.IsChecked()
        write_config(config_dict)
        RefreshCandidates()

    def OnAddSourceFromDir(self, evt):
        with wx.DirDialog(self, "Choose source directory", config_dict['folder_sources'], wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST) as dirDialog:

            if dirDialog.ShowModal() == wx.ID_CANCEL:
                return

            self.AddSourceFromDir(dirDialog.GetPath())

    def AddSourceFromDir(self, directory):
        global config_dict
        config_dict['folder_sources'] = directory
        write_config(config_dict)
        newdata = []
        for f in Path(directory).resolve().glob('*'):
            try:
                if f.is_file():
                    newdata.append([f, 0, '', '', f])
            except (OSError, IOError):
                pass
        self.list_ctrl.AddToList(newdata)

    def OnAddSourceFromFiles(self, evt):
        with wx.FileDialog(self, "Choose source files", config_dict['folder_sources'], style=wx.FD_DEFAULT_STYLE | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            self.AddSourceFromFiles(fileDialog.GetPaths())

    def AddSourceFromFiles(self, files):
        global config_dict
        newdata = []
        first = True
        for f in files:
            if not f:
                continue
            try:
                fp = Path(f)
                if first:
                    first = False
                    config_dict['folder_sources'] = str(fp.parent)
                    write_config(config_dict)
                newdata.append([fp, 0, '', '', fp])
            except (OSError, IOError):
                pass
        self.list_ctrl.AddToList(newdata)

    def OnAddSourceFromClipboard(self, evt):
        files = ClipBoardFiles()
        if files:
            self.AddSourceFromFiles(files)

    def OnAddChoicesFromDir(self, evt):
        with wx.DirDialog(self, "Choose choice directory", config_dict['folder_choices'], wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST) as dirDialog:

            if dirDialog.ShowModal() == wx.ID_CANCEL:
                return
            self.AddChoicesFromDir(dirDialog.GetPath())

    def AddChoicesFromDir(self, directory):
        global glob_choices, config_dict
        config_dict['folder_choices'] = directory
        write_config(config_dict)
        for f in Path(directory).resolve().glob('*'):
            try:
                if f.is_file():
                    glob_choices.add(f)
            except (OSError, IOError):
                pass
        RefreshCandidates()

    def OnAddChoicesFromFiles(self, evt):
        with wx.FileDialog(self, "Choose choice files", config_dict['folder_choices'], style=wx.FD_DEFAULT_STYLE | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            self.AddChoicesFromFiles(fileDialog.GetPaths())

    def AddChoicesFromFiles(self, files):
        global glob_choices, config_dict
        first = True
        for f in files:
            if not f:
                continue
            try:
                fp = Path(f)
                if first:
                    first = False
                    config_dict['folder_choices'] = str(fp.parent)
                    write_config(config_dict)
                glob_choices.add(fp)
            except (OSError, IOError):
                pass
        RefreshCandidates()

    def OnAddChoicesFromClipboard(self, evt):
        global glob_choices
        files = ClipBoardFiles()
        if files:
            self.AddChoicesFromFiles(files)

    def OnRun(self, evt):
        if not glob_choices:
            return

        sources = []
        row_id = -1
        while True:  # loop all the checked items
            row_id = self.list_ctrl.GetNextItem(row_id)
            if row_id == -1:
                break
            if self.list_ctrl.IsItemChecked(row_id):
                pos = self.list_ctrl.GetItemData(row_id)  # 0-based unsorted index
                sources.append(self.list_ctrl.listdata[pos][data_struct.FILENAME])

        progress = wx.ProgressDialog("Match Progress", "", maximum=len(sources), parent=None, style=wx.PD_AUTO_HIDE | wx.PD_APP_MODAL | wx.PD_CAN_ABORT | wx.PD_ESTIMATED_TIME | wx.PD_REMAINING_TIME)
                      
        matches = get_matches(sources, progress)
        row_id = -1
        count = 0
        while True:  # loop all the checked items
            if len(matches) < count + 1:
                break;
            row_id = self.list_ctrl.GetNextItem(row_id)
            if row_id == -1:
                break
            if self.list_ctrl.IsItemChecked(row_id):
                pos = self.list_ctrl.GetItemData(row_id)  # 0-based unsorted index
                if matches[count]:
                    self.list_ctrl.listdata[pos][data_struct.MATCH_SCORE] = matches[count].match_results[0][1]
                    self.list_ctrl.listdata[pos][data_struct.MATCHNAME] = matches[count].match_results[0][0].file
                    self.list_ctrl.listdata[pos][data_struct.PREVIEW] = getRenamePreview(self.list_ctrl.listdata[pos][data_struct.FILENAME], self.list_ctrl.listdata[pos][data_struct.MATCHNAME])
                else:
                    self.list_ctrl.listdata[pos][data_struct.MATCH_SCORE] = None
                    self.list_ctrl.listdata[pos][data_struct.MATCHNAME] = None
                    self.list_ctrl.listdata[pos][data_struct.PREVIEW] = None
                count += 1
        self.list_ctrl.RefreshList()

    def OnReset(self, evt):
        glob_choices.clear()
        self.list_ctrl.listdata.clear()
        self.list_ctrl.DeleteAllItems()

    def OnFilters(self, evt):
        global config_dict
        dia = filtersDialog(None, -1, "Masks & Filters")
        res = dia.ShowModal()
        if res == wx.ID_OK:
            config_dict['filters'] = dia.panel.filters_list.GetFilters()
            FileFiltered.filters = CompileFilters(config_dict['filters'])
            config_dict['masks'] = dia.panel.masks_list.GetMasks()
            FileMasked.masks = CompileMasks(config_dict['masks'])
            config_dict['filters_test'] = dia.panel.preview_filters.GetValue()
            config_dict['masks_test'] = dia.panel.preview_masks.GetValue()
            write_config(config_dict)

        dia.Destroy()

    def OnRename(self, evt):
        Qview_fullpath = config_dict['show_fullpath']
        Qhide_extension = config_dict['hide_extension']
        row_id = -1
        while True:  # loop all the checked items
            row_id = self.list_ctrl.GetNextItem(row_id)
            if row_id == -1:
                break
            if self.list_ctrl.IsItemChecked(row_id):
                pos = self.list_ctrl.GetItemData(row_id)  # 0-based unsorted index

                old_path = self.list_ctrl.listdata[pos][data_struct.FILENAME]
                preview_path = self.list_ctrl.listdata[pos][data_struct.PREVIEW]
                if preview_path:
                    if old_path != preview_path:
                        old_file = str(old_path)
                        new_file = str(preview_path)
                        try:
                            if old_path.is_file():
                                os.rename(old_file, new_file)
                                wx.LogMessage('Renaming : %s --> %s' % (old_file, new_file))
                                new_path = Path(new_file)
                                new_match = get_match(new_path)
                                if new_match:
                                    self.list_ctrl.listdata[pos] = [new_path, new_match[0][1], new_match[0][0].file, getRenamePreview(new_path, new_match[0][0].file), old_path]
                                    self.list_ctrl.SetItem(row_id, data_struct.MATCH_SCORE, str(self.list_ctrl.listdata[pos][data_struct.MATCH_SCORE]))
                                    stem, suffix = GetFileStemAndSuffix(self.list_ctrl.listdata[pos][data_struct.MATCHNAME])
                                    self.list_ctrl.SetItem(row_id, data_struct.MATCHNAME, str(self.list_ctrl.listdata[pos][data_struct.MATCHNAME]) if Qview_fullpath else (stem if Qhide_extension else self.list_ctrl.listdata[pos][data_struct.MATCHNAME].name))
                                    stem, suffix = GetFileStemAndSuffix(self.list_ctrl.listdata[pos][data_struct.PREVIEW])
                                    self.list_ctrl.SetItem(row_id, data_struct.PREVIEW, str(self.list_ctrl.listdata[pos][data_struct.PREVIEW]) if Qview_fullpath else (stem if Qhide_extension else self.list_ctrl.listdata[pos][data_struct.PREVIEW].name))
                                else:
                                    self.list_ctrl.listdata[pos] = [new_path, 0, '', '', old_path]
                                    self.list_ctrl.SetItem(row_id, data_struct.MATCH_SCORE, '')
                                    self.list_ctrl.SetItem(row_id, data_struct.MATCHNAME, '')
                                    self.list_ctrl.SetItem(row_id, data_struct.PREVIEW, '')

                                stem, suffix = GetFileStemAndSuffix(self.list_ctrl.listdata[pos][data_struct.FILENAME])
                                self.list_ctrl.SetItem(row_id, data_struct.FILENAME, str(self.list_ctrl.listdata[pos][data_struct.FILENAME]) if Qview_fullpath else (stem if Qhide_extension else self.list_ctrl.listdata[pos][data_struct.FILENAME].name))

                        except (OSError, IOError):
                            wx.LogMessage('Error when renaming : %s --> %s' % (old_file, new_file))
                    else:
                        wx.LogMessage('Not renaming %s (same name)' % (old_path.name))
                else:
                    wx.LogMessage('Not renaming %s (no match)' % (old_path.name))

    def OnUndo(self, evt):
        Qview_fullpath = config_dict['show_fullpath']
        Qhide_extension = config_dict['hide_extension']
        row_id = -1
        while True:  # loop all the checked items
            row_id = self.list_ctrl.GetNextItem(row_id)
            if row_id == -1:
                break
            pos = self.list_ctrl.GetItemData(row_id)  # 0-based unsorted index

            currrent_path = self.list_ctrl.listdata[pos][data_struct.FILENAME]
            previous_path = self.list_ctrl.listdata[pos][data_struct.PREVIOUS_FILENAME]

            if currrent_path != previous_path:
                old_file = str(currrent_path)
                new_file = str(previous_path)
                try:
                    if currrent_path.is_file():
                        os.rename(old_file, new_file)
                    wx.LogMessage('Renaming : %s --> %s' % (old_file, new_file))
                    new_path = Path(new_file)
                    new_match = get_match(new_path)
                    if new_match:
                        self.list_ctrl.listdata[pos] = [new_path, new_match[0][1], new_match[0][0].file, getRenamePreview(new_path, new_match[0][0].file), new_path]
                        self.list_ctrl.SetItem(row_id, data_struct.MATCH_SCORE, str(self.list_ctrl.listdata[pos][data_struct.MATCH_SCORE]))
                        stem, suffix = GetFileStemAndSuffix(self.list_ctrl.listdata[pos][data_struct.MATCHNAME])
                        self.list_ctrl.SetItem(row_id, data_struct.MATCHNAME, str(self.list_ctrl.listdata[pos][data_struct.MATCHNAME]) if Qview_fullpath else (stem if Qhide_extension else self.list_ctrl.listdata[pos][data_struct.MATCHNAME].name))
                        stem, suffix = GetFileStemAndSuffix(self.list_ctrl.listdata[pos][data_struct.PREVIEW])
                        self.list_ctrl.SetItem(row_id, data_struct.PREVIEW, str(self.list_ctrl.listdata[pos][data_struct.PREVIEW]) if Qview_fullpath else (stem if Qhide_extension else self.list_ctrl.listdata[pos][data_struct.PREVIEW].name))
                    else:
                        self.list_ctrl.listdata[pos] = [new_path, 0, '', '', new_path]
                        self.list_ctrl.SetItem(row_id, data_struct.MATCH_SCORE, '')
                        self.list_ctrl.SetItem(row_id, data_struct.MATCHNAME, '')
                        self.list_ctrl.SetItem(row_id, data_struct.PREVIEW, '')

                    stem, suffix = GetFileStemAndSuffix(self.list_ctrl.listdata[pos][data_struct.FILENAME])
                    self.list_ctrl.SetItem(row_id, data_struct.FILENAME, str(self.list_ctrl.listdata[pos][data_struct.FILENAME]) if Qview_fullpath else (stem if Qhide_extension else self.list_ctrl.listdata[pos][data_struct.FILENAME].name))

                except (OSError, IOError):
                    wx.LogMessage('Error when renaming : %s --> %s' % (old_file, new_file))
            else:
                wx.LogMessage('Not renaming %s (same name)' % (currrent_path.name))


class aboutDialog(wx.Dialog):
    def __init__(self, parent, id, label):
        wx.Dialog.__init__(self, parent, id, label, size=(600, 300))

        about = wx.html.HtmlWindow(self, size=(400, 250))
        about.SetPage(
            "<font size=\"30\">PyFuzzy-renamer</font><br><br>"
            "<u>Authors</u><br>"
            "<ul><li>pcjco</li></ul>"
            "<u>Credits</u><br>"
            "<ul><li><a href =\"https://wxpython.org\">wxPython</a></li>"
            "<li><a href =\"https://becrisdesign.com\">Becris Design</a> (icons)</li>"
            "<li><a href =\"https://www.waste.org/~winkles/fuzzyRename/\">Fuzzy Rename</a> (original by jeff@silent.net)</li></ul>"
            "<u>License</u><br>"
            "<ul><li>MIT License</li>"
            "<li>Copyright (c) 2020 pcjco</li></ul>")

        btns = self.CreateButtonSizer(wx.CLOSE)

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(about, 1, wx.ALL | wx.EXPAND, 0)
        mainSizer.Add(btns, 0, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(mainSizer)
        self.Fit()


class helpDialog(wx.Dialog):
    def __init__(self, parent, id, label):
        wx.Dialog.__init__(self, parent, id, label, size=(600, 300), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.Bind(wx.EVT_CLOSE, self.OnClose)

        help = wx.html.HtmlWindow(self, size=(1400, 500))
        help.SetPage(getDoc())

        btns = self.CreateButtonSizer(wx.CLOSE)
        close = wx.FindWindowById(wx.ID_CLOSE, self)
        close.Bind(wx.EVT_BUTTON, self.OnClose)

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(help, 1, wx.ALL | wx.EXPAND, 0)
        mainSizer.Add(btns, 0, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(mainSizer)
        self.Fit()

    def OnClose(self, event):
        self.Destroy()


class filtersDialog(wx.Dialog):
    def __init__(self, parent, id, label):
        wx.Dialog.__init__(self, parent, id, label, size=(350, 300), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.panel = filtersPanel(self)
        btns = self.CreateButtonSizer(wx.OK | wx.CANCEL | wx.APPLY)
        default_button = wx.FindWindowById(wx.ID_APPLY, self)
        default_button.SetLabel('Reset')

        default_button.Bind(wx.EVT_BUTTON, self.OnReset)

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(self.panel, 1, wx.ALL | wx.EXPAND, 0)
        mainSizer.Add(btns, 0, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(mainSizer)
        self.Fit()

    def OnReset(self, event):
        self.panel.filters_list.PopulateFilters(default_filters)
        self.panel.masks_list.PopulateMasks(default_masks)


class filtersPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS)

        self.notebook = wx.Notebook(self)
        page_filters = wx.Panel(self.notebook)
        page_masks = wx.Panel(self.notebook)

        self.notebook.AddPage(page_masks, 'Masks on Sources')
        self.notebook.AddPage(page_filters, 'Matching Filters')

        self.filters_list = FilterListCtrl(page_filters, self, size=(-1, -1), style=wx.LC_REPORT | wx.BORDER_SUNKEN)
        label1 = wx.StaticText(page_filters, label="Test String", size=(60, -1))
        self.preview_filters = wx.TextCtrl(page_filters, value='Hitchhiker\'s Guide to the Galaxy, The (AGA)', size=(300, -1))
        label2 = wx.StaticText(page_filters, label="Result", size=(60, -1))
        self.result_preview_filters = wx.TextCtrl(page_filters, value='', size=(300, -1), style=wx.TE_READONLY)

        wx.FileSystem.AddHandler(wx.MemoryFSHandler())
        image_Info = wx.MemoryFSHandler()
        image_Info.AddFile('info.png', Info_16_PNG.GetBitmap(), wx.BITMAP_TYPE_PNG)

        html_desc_filters = wx.html.HtmlWindow(page_filters, size=(-1, 135))
        html_desc_filters.SetPage(
            "<img src=\"memory:info.png\">"
            " These filters, using Python regular expression patterns, are applied to <b>sources</b> and <b>choices</b> strings before matching occurs."
            "It is used to help matching by cleaning strings (removing tags, ...) beforehand.<br><br>"
            "For example, replacing the pattern <font face=\"verdana\">'(\\(\\d{4}\\))'</font> by <font face=\"verdana\">''</font>:<br>"
            "<ul><li><i><font face=\"verdana\">The Wire <font color=\"red\">(2002)</font></font></i> \u2B62 <i><font face=\"verdana\">The Wire</font></i></li>")

        sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer2.Add(label1, 0, wx.ALL, 5)
        sizer2.Add(self.preview_filters, 1, wx.EXPAND | wx.ALL, 0)

        sizer3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer3.Add(label2, 0, wx.ALL, 5)
        sizer3.Add(self.result_preview_filters, 1, wx.EXPAND | wx.ALL, 0)

        sizer_filters = wx.BoxSizer(wx.VERTICAL)
        sizer_filters.Add(self.filters_list, 2, wx.ALL | wx.EXPAND, 1)
        sizer_filters.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 0)
        sizer_filters.Add(sizer2, 0, wx.ALL | wx.EXPAND, 1)
        sizer_filters.Add(sizer3, 0, wx.ALL | wx.EXPAND, 1)
        sizer_filters.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 0)
        sizer_filters.Add(html_desc_filters, 0, wx.EXPAND | wx.ALL)
        page_filters.SetSizer(sizer_filters)

        self.masks_list = MaskListCtrl(page_masks, self, size=(-1, -1), style=wx.LC_REPORT | wx.BORDER_SUNKEN)
        label21 = wx.StaticText(page_masks, label="Test String", size=(80, -1))
        self.preview_masks = wx.TextCtrl(page_masks, value='(1986) Hitchhiker\'s Guide to the Galaxy, The (AGA) Disk1', size=(300, -1))
        self.result_preview_masks_lead = wx.TextCtrl(page_masks, value='', size=(40, -1), style=wx.TE_READONLY)
        self.result_preview_masks_mid = wx.TextCtrl(page_masks, value='', size=(220, -1), style=wx.TE_READONLY)
        self.result_preview_masks_trail = wx.TextCtrl(page_masks, value='', size=(40, -1), style=wx.TE_READONLY)
        label22 = wx.StaticText(page_masks, label="Lead-Mid-Trail", size=(80, -1))

        html_desc_masks = wx.html.HtmlWindow(page_masks, size=(-1, 200))
        html_desc_masks.SetPage(
            "<img src=\"memory:info.png\">"
            " These masks, using Python regular expression patterns, are removed from <b>sources</b> strings before filtering and matching occur."
            "It is used to remove leading and trailing expressions (year, disk#...) before matching and restore them at renaming.<br><br>"
            "For example, masking the pattern <font face=\"verdana\">'(\\s?disk\\d)$'</font>:<br>"
            "<ol><li>Source\u2B62masked source: <i><font face=\"verdana\">The Wiiire <font color=\"red\"> Disk1</font> \u2B62 The Wiiire</font></i></li>"
            "<li>Masked source\u2B62best choice: <i><font face=\"verdana\">The Wiiire \u2B62 The Wire</font></i></li>"
            "<li>Best choice\u2B62renamed unmasked source: <i><font face=\"verdana\">The Wire \u2B62 The Wire<font color=\"red\"> Disk1</font></font></i></li>")

        sizer22 = wx.BoxSizer(wx.HORIZONTAL)
        sizer22.Add(label21, 0, wx.ALL, 5)
        sizer22.Add(self.preview_masks, 1, wx.EXPAND | wx.ALL, 0)

        sizer32 = wx.BoxSizer(wx.HORIZONTAL)
        sizer32.Add(label22, 0, wx.ALL, 5)
        sizer32.Add(self.result_preview_masks_lead, 1, wx.EXPAND | wx.ALL, 0)
        sizer32.Add(self.result_preview_masks_mid, 5, wx.EXPAND | wx.ALL, 0)
        sizer32.Add(self.result_preview_masks_trail, 1, wx.EXPAND | wx.ALL, 0)

        sizer_masks = wx.BoxSizer(wx.VERTICAL)
        sizer_masks.Add(self.masks_list, 1, wx.ALL | wx.EXPAND, 1)
        sizer_masks.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 0)
        sizer_masks.Add(sizer22, 0, wx.ALL | wx.EXPAND, 1)
        sizer_masks.Add(sizer32, 0, wx.ALL | wx.EXPAND, 1)
        sizer_masks.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 0)
        sizer_masks.Add(html_desc_masks, 0, wx.EXPAND | wx.ALL)
        page_masks.SetSizer(sizer_masks)

        sizer = wx.BoxSizer()
        sizer.Add(self.notebook, 1, wx.EXPAND)

        self.SetSizer(sizer)
        self.UpdateMaskPreview()
        self.UpdateFilterPreview()

        self.Bind(wx.EVT_TEXT, self.onChangePreviewFilters, self.preview_filters)
        self.Bind(wx.EVT_TEXT, self.onChangePreviewMasks, self.preview_masks)

        page_filters.Fit()
        page_masks.Fit()
        self.Fit()

    def onChangePreviewFilters(self, event):
        self.UpdateFilterPreview()

    def onChangePreviewMasks(self, event):
        self.UpdateMaskPreview()

    def UpdateFilterPreview(self):
        filters = CompileFilters(self.filters_list.GetFilters())
        self.result_preview_filters.SetValue(filter_processed(Path(self.preview_filters.GetValue() + '.txt'), filters))

    def UpdateMaskPreview(self):
        masks = CompileMasks(self.masks_list.GetMasks())
        filters = []
        pre, middle, post = mask_processed(Path(self.preview_masks.GetValue() + '.txt'), masks, filters, applyFilters=False)
        self.result_preview_masks_lead.SetValue(pre)
        self.result_preview_masks_mid.SetValue(middle)
        self.result_preview_masks_trail.SetValue(post)


class MaskListCtrlDropTarget(wx.DropTarget):
    def __init__(self, source):
        wx.DropTarget.__init__(self)
        self.dv = source

        # specify the type of data we will accept
        self.data = wx.CustomDataObject("ListCtrlItems")
        self.SetDataObject(self.data)

    # Called when OnDrop returns True.  We need to get the data and
    # do something with it.
    def OnData(self, x, y, d):
        # copy the data from the drag source to our data object
        if self.GetData():
            # convert it back to a list and give it to the viewer
            ldata = self.data.GetData()
            collect = pickle.loads(ldata)
            # Add videos to this playlist
            self.dv._insert(x, y, collect)
        return wx.DragMove

    def OnDragOver(self, x, y, d):
        return wx.DragMove


class MaskListCtrl(wx.ListCtrl, listmix.TextEditMixin):
    ctxmenugui_titles = ['Add', 'Delete']
    ctxmenugui_title_by_id = {}
    for title in ctxmenugui_titles:
        ctxmenugui_title_by_id[wx.NewIdRef()] = title

    def __init__(self, parent, panel, ID=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.TextEditMixin.__init__(self)
        self.EnableCheckBoxes()
        self.panel = panel
        self.unplug_preview = True
        self.Bind(wx.EVT_CHAR, self.onKeyPress)
        self.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnBeginLabelEdit)
        self.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnEndLabelEdit)
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self._startDrag)
        self.Bind(wx.EVT_CONTEXT_MENU, self.RightClickCb)
        self.Bind(wx.EVT_LIST_ITEM_CHECKED, self.CheckCb)
        self.Bind(wx.EVT_LIST_ITEM_UNCHECKED, self.CheckCb)

        self.InsertColumn(0, '#', width=35)
        self.InsertColumn(1, 'Mask Name', width=150)
        self.InsertColumn(2, 'Pattern', width=150)

        dt = MaskListCtrlDropTarget(self)
        dt.SetDefaultAction(wx.DragMove)
        self.SetDropTarget(dt)

        self.PopulateMasks(config_dict['masks'])
        self.unplug_preview = False

    def PopulateMasks(self, masks):
        self.DeleteAllItems()
        lines = masks.splitlines()
        it = iter(lines)
        row_id = 0
        index = 0
        for l1, l2 in zip(it, it):
            data = (l1.strip()[1:], l2.strip()[1:-1])
            self.InsertItem(row_id, "%2d" % (int(index) + 1))
            self.SetItem(row_id, 1, data[0])
            self.SetItem(row_id, 2, data[1])
            if (l1.strip()[0]) == '+':
                self.CheckItem(row_id, True)
            else:
                self.CheckItem(row_id, False)

            row_id += 1
            index += 1

    def GetMasks(self):
        ret = ''
        row_id = -1
        while 1:
            row_id = self.GetNextItem(row_id)
            if row_id == -1:
                break
            ret += '+' if self.IsItemChecked(row_id) else '-'
            ret += self.GetItemText(row_id, 1) + '\n'
            ret += '"' + self.GetItemText(row_id, 2) + '"\n'
        return ret

    def onKeyPress(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_DELETE:
            self.DeleteSelected()

        if keycode:
            event.Skip()

    def OnBeginLabelEdit(self, event):
        if event.GetColumn() == 0:
            event.Veto()
            row_id = event.GetIndex()
            self.CheckItem(row_id, not self.IsItemChecked(row_id))
        else:
            event.Skip()

    def OnEndLabelEdit(self, event):
        if event.IsEditCancelled():
            event.Veto()
        row_id = event.GetIndex()
        col_id = event.GetColumn()
        if col_id > 1:
            masks = ''
            row_id0 = -1
            while 1:
                row_id0 = self.GetNextItem(row_id0)
                if row_id0 == -1:
                    break
                masks += '+' if self.IsItemChecked(row_id0) else '-'
                masks += self.GetItemText(row_id0, 1) + '\n'
                if row_id == row_id0 and col_id == 2:
                    masks += '"' + event.GetText() + '"\n'
                else:
                    masks += '"' + self.GetItemText(row_id0, 2) + '"\n'

            masks = CompileMasks(masks)
            filters = []
            pre, middle, post = mask_processed(Path(self.panel.preview_masks.GetValue() + '.txt'), masks, filters, applyFilters=False)
            self.panel.result_preview_filters.SetValue('[' + pre + '][' + middle + '][' + post + ']')

    def getItemInfo(self, idx):
        """Collect all relevant data of a listitem, and put it in a list"""
        collect = []
        collect.append(idx)  # We need the original index, so it is easier to eventualy delete it
        collect.append(self.IsItemChecked(idx))  # check
        collect.append(self.GetItemText(idx))  # Text first column
        for i in range(1, self.GetColumnCount()):  # Possible extra columns
            collect.append(self.GetItem(idx, i).GetText())
        return collect

    def _startDrag(self, e):
        collect = []
        row_id = -1
        while True:  # find all the selected items and put them in a list
            row_id = self.GetNextItem(row_id, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if row_id == -1:
                break
            collect.append(self.getItemInfo(row_id))

        # Pickle the items list.
        itemdata = pickle.dumps(collect)
        # create our own data format and use it in a
        # custom data object
        ldata = wx.CustomDataObject("ListCtrlItems")
        ldata.SetData(itemdata)
        # Now make a data object for the  item list.
        data = wx.DataObjectComposite()
        data.Add(ldata)

        # Create drop source and begin drag-and-drop.
        dropSource = wx.DropSource(self)
        dropSource.SetData(data)
        res = dropSource.DoDragDrop(flags=wx.Drag_DefaultMove)
        if res == wx.DragMove:
            collect.reverse()  # Delete all the items, starting with the last item
            for i in collect:
                index = self.FindItem(i[0], i[2])
                self.DeleteItem(index)

            # renumbering
            row_id = -1
            while 1:
                row_id = self.GetNextItem(row_id)
                if row_id == -1:
                    break
                self.SetItemText(row_id, "%2d" % (int(row_id) + 1))
            self.panel.UpdateMaskPreview()

    def _insert(self, x, y, seq):
        """ Insert text at given x, y coordinates --- used with drag-and-drop. """

        # Find insertion point.
        index, flags = self.HitTest((x, y))

        if index == wx.NOT_FOUND:  # not clicked on an item
            if flags & (wx.LIST_HITTEST_NOWHERE | wx.LIST_HITTEST_ABOVE | wx.LIST_HITTEST_BELOW):  # empty list or below last item
                index = self.GetItemCount()  # append to end of list
            elif self.GetItemCount() > 0:
                if y <= self.GetItemRect(0).y:  # clicked just above first item
                    index = 0  # append to top of list
                else:
                    index = self.GetItemCount() + 1  # append to end of list
        else:  # clicked on an item
            # Get bounding rectangle for the item the user is dropping over.
            rect = self.GetItemRect(index)

            # If the user is dropping into the lower half of the rect, we want to insert _after_ this item.
            # Correct for the fact that there may be a heading involved
            if y > rect.y + rect.height / 2:
                index += 1

        for i in seq:  # insert the item data
            idx = self.InsertItem(index, i[2])
            self.CheckItem(idx, i[1])
            for j in range(1, self.GetColumnCount()):
                self.SetItem(idx, j, i[2 + j])
            index += 1

    def RightClickCb(self, event):
        menu = wx.Menu()
        for (id, title) in MaskListCtrl.ctxmenugui_title_by_id.items():
            if title != 'Delete' or self.GetSelectedItemCount():
                menu.Append(id.GetId(), title)
                self.Bind(wx.EVT_MENU, self.MenuSelectionCb, id=id)
        pos = self.ScreenToClient(event.GetPosition())
        self.PopupMenu(menu, pos)
        menu.Destroy()
        event.Skip()

    def MenuSelectionCb(self, event):
        operation = MaskListCtrl.ctxmenugui_title_by_id[event.GetId()]
        if operation == 'Add':
            data = ('new mask', '', '')
            row_id = self.GetItemCount()
            self.InsertItem(row_id, "%2d" % (int(row_id) + 1))
            self.SetItem(row_id, 1, data[0])
            self.SetItem(row_id, 2, data[1])
            self.CheckItem(row_id, True)
        elif operation == 'Delete':
            self.DeleteSelected()

    def CheckCb(self, event):
        if not self.unplug_preview:
            self.panel.UpdateMaskPreview()

    def DeleteSelected(self):
        selected = get_selected_items(self)

        selected.reverse()  # Delete all the items, starting with the last item
        for row_id in selected:
            self.DeleteItem(row_id)

        # renumbering
        row_id = -1
        while 1:
            row_id = self.GetNextItem(row_id)
            if row_id == -1:
                break
            self.SetItemText(row_id, "%2d" % (int(row_id) + 1))
        self.panel.UpdateMaskPreview()


class FilterListCtrlDropTarget(wx.DropTarget):
    def __init__(self, source):
        wx.DropTarget.__init__(self)
        self.dv = source

        # specify the type of data we will accept
        self.data = wx.CustomDataObject("ListCtrlItems")
        self.SetDataObject(self.data)

    # Called when OnDrop returns True.  We need to get the data and
    # do something with it.
    def OnData(self, x, y, d):
        # copy the data from the drag source to our data object
        if self.GetData():
            # convert it back to a list and give it to the viewer
            ldata = self.data.GetData()
            collect = pickle.loads(ldata)
            # Add videos to this playlist
            self.dv._insert(x, y, collect)
        return wx.DragMove

    def OnDragOver(self, x, y, d):
        return wx.DragMove


class FilterListCtrl(wx.ListCtrl, listmix.TextEditMixin):
    ctxmenugui_titles = ['Add', 'Delete']
    ctxmenugui_title_by_id = {}
    for title in ctxmenugui_titles:
        ctxmenugui_title_by_id[wx.NewIdRef()] = title

    def __init__(self, parent, panel, ID=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.TextEditMixin.__init__(self)
        self.EnableCheckBoxes()
        self.panel = panel
        self.unplug_preview = True
        self.Bind(wx.EVT_CHAR, self.onKeyPress)
        self.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnBeginLabelEdit)
        self.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnEndLabelEdit)
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self._startDrag)
        self.Bind(wx.EVT_CONTEXT_MENU, self.RightClickCb)
        self.Bind(wx.EVT_LIST_ITEM_CHECKED, self.CheckCb)
        self.Bind(wx.EVT_LIST_ITEM_UNCHECKED, self.CheckCb)

        self.InsertColumn(0, '#', width=35)
        self.InsertColumn(1, 'Filter Name', width=150)
        self.InsertColumn(2, 'Pattern', width=150)
        self.InsertColumn(3, 'Replace', width=150)

        dt = FilterListCtrlDropTarget(self)
        dt.SetDefaultAction(wx.DragMove)
        self.SetDropTarget(dt)

        self.PopulateFilters(config_dict['filters'])
        self.unplug_preview = False

    def PopulateFilters(self, filters):
        self.DeleteAllItems()
        lines = filters.splitlines()
        it = iter(lines)
        row_id = 0
        index = 0
        for l1, l2, l3 in zip(it, it, it):
            data = (l1.strip()[1:], l2.strip()[1:-1], l3.strip()[1:-1])
            self.InsertItem(row_id, "%2d" % (int(index) + 1))
            self.SetItem(row_id, 1, data[0])
            self.SetItem(row_id, 2, data[1])
            self.SetItem(row_id, 3, data[2])
            if (l1.strip()[0]) == '+':
                self.CheckItem(row_id, True)
            else:
                self.CheckItem(row_id, False)

            row_id += 1
            index += 1

    def GetFilters(self):
        ret = ''
        row_id = -1
        while 1:
            row_id = self.GetNextItem(row_id)
            if row_id == -1:
                break
            ret += '+' if self.IsItemChecked(row_id) else '-'
            ret += self.GetItemText(row_id, 1) + '\n'
            ret += '"' + self.GetItemText(row_id, 2) + '"\n'
            ret += '"' + self.GetItemText(row_id, 3) + '"\n'
        return ret

    def onKeyPress(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_DELETE:
            self.DeleteSelected()

        if keycode:
            event.Skip()

    def OnBeginLabelEdit(self, event):
        if event.GetColumn() == 0:
            event.Veto()
            row_id = event.GetIndex()
            self.CheckItem(row_id, not self.IsItemChecked(row_id))
        else:
            event.Skip()

    def OnEndLabelEdit(self, event):
        if event.IsEditCancelled():
            event.Veto()
        row_id = event.GetIndex()
        col_id = event.GetColumn()
        if col_id > 1:
            filters = ''
            row_id0 = -1
            while 1:
                row_id0 = self.GetNextItem(row_id0)
                if row_id0 == -1:
                    break
                filters += '+' if self.IsItemChecked(row_id0) else '-'
                filters += self.GetItemText(row_id0, 1) + '\n'
                if row_id == row_id0 and col_id == 2:
                    filters += '"' + event.GetText() + '"\n'
                else:
                    filters += '"' + self.GetItemText(row_id0, 2) + '"\n'
                if row_id == row_id0 and col_id == 3:
                    filters += '"' + event.GetText() + '"\n'
                else:
                    filters += '"' + self.GetItemText(row_id0, 3) + '"\n'

            filters = CompileFilters(filters)
            self.panel.result_preview_masks.SetValue(filter_processed(Path(self.panel.preview_filters.GetValue() + '.txt'), filters))

    def getItemInfo(self, idx):
        """Collect all relevant data of a listitem, and put it in a list"""
        collect = []
        collect.append(idx)  # We need the original index, so it is easier to eventualy delete it
        collect.append(self.IsItemChecked(idx))  # check
        collect.append(self.GetItemText(idx))  # Text first column
        for i in range(1, self.GetColumnCount()):  # Possible extra columns
            collect.append(self.GetItem(idx, i).GetText())
        return collect

    def _startDrag(self, e):
        collect = []
        row_id = -1
        while True:  # find all the selected items and put them in a list
            row_id = self.GetNextItem(row_id, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if row_id == -1:
                break
            collect.append(self.getItemInfo(row_id))

        # Pickle the items list.
        itemdata = pickle.dumps(collect)
        # create our own data format and use it in a
        # custom data object
        ldata = wx.CustomDataObject("ListCtrlItems")
        ldata.SetData(itemdata)
        # Now make a data object for the  item list.
        data = wx.DataObjectComposite()
        data.Add(ldata)

        # Create drop source and begin drag-and-drop.
        dropSource = wx.DropSource(self)
        dropSource.SetData(data)
        res = dropSource.DoDragDrop(flags=wx.Drag_DefaultMove)
        if res == wx.DragMove:
            collect.reverse()  # Delete all the items, starting with the last item
            for i in collect:
                index = self.FindItem(i[0], i[2])
                self.DeleteItem(index)

            # renumbering
            row_id = -1
            while 1:
                row_id = self.GetNextItem(row_id)
                if row_id == -1:
                    break
                self.SetItemText(row_id, "%2d" % (int(row_id) + 1))
            self.panel.UpdateFilterPreview()

    def _insert(self, x, y, seq):
        """ Insert text at given x, y coordinates --- used with drag-and-drop. """

        # Find insertion point.
        index, flags = self.HitTest((x, y))

        if index == wx.NOT_FOUND:  # not clicked on an item
            if flags & (wx.LIST_HITTEST_NOWHERE | wx.LIST_HITTEST_ABOVE | wx.LIST_HITTEST_BELOW):  # empty list or below last item
                index = self.GetItemCount()  # append to end of list
            elif self.GetItemCount() > 0:
                if y <= self.GetItemRect(0).y:  # clicked just above first item
                    index = 0  # append to top of list
                else:
                    index = self.GetItemCount() + 1  # append to end of list
        else:  # clicked on an item
            # Get bounding rectangle for the item the user is dropping over.
            rect = self.GetItemRect(index)

            # If the user is dropping into the lower half of the rect, we want to insert _after_ this item.
            # Correct for the fact that there may be a heading involved
            if y > rect.y + rect.height / 2:
                index += 1

        for i in seq:  # insert the item data
            idx = self.InsertItem(index, i[2])
            self.CheckItem(idx, i[1])
            for j in range(1, self.GetColumnCount()):
                self.SetItem(idx, j, i[2 + j])
            index += 1

    def RightClickCb(self, event):
        menu = wx.Menu()
        for (id, title) in FilterListCtrl.ctxmenugui_title_by_id.items():
            if title != 'Delete' or self.GetSelectedItemCount():
                menu.Append(id.GetId(), title)
                self.Bind(wx.EVT_MENU, self.MenuSelectionCb, id=id)
        pos = self.ScreenToClient(event.GetPosition())
        self.PopupMenu(menu, pos)
        menu.Destroy()
        event.Skip()

    def MenuSelectionCb(self, event):
        operation = FilterListCtrl.ctxmenugui_title_by_id[event.GetId()]
        if operation == 'Add':
            data = ('new filter', '', '')
            row_id = self.GetItemCount()
            self.InsertItem(row_id, "%2d" % (int(row_id) + 1))
            self.SetItem(row_id, 1, data[0])
            self.SetItem(row_id, 2, data[1])
            self.SetItem(row_id, 3, data[2])
            self.CheckItem(row_id, True)
        elif operation == 'Delete':
            self.DeleteSelected()

    def CheckCb(self, event):
        if not self.unplug_preview:
            self.panel.UpdateFilterPreview()

    def DeleteSelected(self):
        selected = get_selected_items(self)

        selected.reverse()  # Delete all the items, starting with the last item
        for row_id in selected:
            self.DeleteItem(row_id)

        # renumbering
        row_id = -1
        while 1:
            row_id = self.GetNextItem(row_id)
            if row_id == -1:
                break
            self.SetItemText(row_id, "%2d" % (int(row_id) + 1))
        self.panel.UpdateFilterPreview()


class MainFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, "PyFuzzy-renamer",
                          pos=wx.Point(-10, 0), size=wx.Size(1000, 800))

        bundle = wx.IconBundle()
        bundle.AddIcon(wx.Icon(Rename_16_PNG.GetBitmap()))
        bundle.AddIcon(wx.Icon(Rename_32_PNG.GetBitmap()))
        self.SetIcons(bundle)

        self.help = None

        menubar = wx.MenuBar()
        self.statusbar = self.CreateStatusBar(2)
        files = wx.Menu()
        sources = wx.Menu()
        sources_ = wx.MenuItem(files, 100, '&Sources', 'Select sources (to rename)')
        sources_.SetSubMenu(sources)

        source_from_dir = wx.MenuItem(sources, 102, '&Sources from Directory\tCtrl+S', 'Select sources from directory')
        source_from_dir.SetBitmap(AddFolder_16_PNG.GetBitmap())
        sources.Append(source_from_dir)

        source_from_clipboard = wx.MenuItem(sources, 103, 'Sources from &Clipboard', 'Select sources from clipboard')
        source_from_clipboard.SetBitmap(Clipboard_16_PNG.GetBitmap())
        sources.Append(source_from_clipboard)

        choices = wx.Menu()
        choices_ = wx.MenuItem(files, 101, '&Choices', 'Select choices (to match)')
        choices_.SetSubMenu(choices)

        target_from_dir = wx.MenuItem(choices, 105, '&Choices from Directory\tCtrl+T', 'Select choices from directory')
        target_from_dir.SetBitmap(AddFolder_16_PNG.GetBitmap())
        choices.Append(target_from_dir)

        choices_from_clipboard = wx.MenuItem(choices, 106, 'Choices from &Clipboard', 'Select choices from clipboard')
        choices_from_clipboard.SetBitmap(Clipboard_16_PNG.GetBitmap())
        choices.Append(choices_from_clipboard)

        quit = wx.MenuItem(files, 104, '&Quit\tCtrl+Q', 'Quit the Application')
        quit.SetBitmap(Quit_16_PNG.GetBitmap())

        files.Append(sources_)
        files.Append(choices_)
        files.Append(quit)

        options = wx.Menu()
        view_fullpath = options.AppendCheckItem(202, '&View full path', 'View full path')
        view_fullpath.Check(config_dict['show_fullpath'])

        self.hide_extension = options.AppendCheckItem(203, '&Hide extension', 'Hide extension')
        self.hide_extension.Check(config_dict['hide_extension'])
        self.hide_extension.Enable(not config_dict['show_fullpath'])

        self.keep_match_ext = options.AppendCheckItem(201, '&Keep matched file extension', 'Keep matched file extension')
        self.keep_match_ext.Check(config_dict['keep_match_ext'])

        self.match_firstletter = options.AppendCheckItem(204, '&Always match first letter', 'Enforce choices that match the first letter of the source')
        self.match_firstletter.Check(config_dict['match_firstletter'])

        help = wx.Menu()
        doc = wx.MenuItem(help, 300, '&Help', 'Help')
        doc.SetBitmap(Help_16_PNG.GetBitmap())
        help.Append(doc)
        about = wx.MenuItem(help, 301, '&About', 'About the application')
        about.SetBitmap(Info_16_PNG.GetBitmap())
        help.Append(about)

        menubar.Append(files, '&File')
        menubar.Append(options, '&Options')
        menubar.Append(help, '&Help')
        self.SetMenuBar(menubar)
        self.Centre()

        # Add a panel so it looks the correct on all platforms
        self.panel = MainPanel(self)
        self.Bind(wx.EVT_CLOSE, self.OnQuit)
        self.Bind(wx.EVT_MENU, self.OnQuit, id=104)
        self.Bind(wx.EVT_MENU, self.panel.OnAddSourceFromDir, id=102)
        self.Bind(wx.EVT_MENU, self.panel.OnAddSourceFromClipboard, id=103)
        self.Bind(wx.EVT_MENU, self.panel.OnAddChoicesFromDir, id=105)
        self.Bind(wx.EVT_MENU, self.panel.OnAddChoicesFromClipboard, id=106)
        self.Bind(wx.EVT_MENU, self.panel.OnViewFullPath, id=202)
        self.Bind(wx.EVT_MENU, self.panel.OnHideExtension, id=203)
        self.Bind(wx.EVT_MENU, self.panel.OnKeepMatchExtension, id=201)
        self.Bind(wx.EVT_MENU, self.panel.OnMatchFirstLetter, id=204)
        self.Bind(wx.EVT_MENU, self.OnHelp, id=300)
        self.Bind(wx.EVT_MENU, self.OnAbout, id=301)

        self.Show(True)

    def OnAbout(self, event):
        dia = aboutDialog(None, -1, "About PyFuzzy-renamer")
        dia.ShowModal()
        dia.Destroy()

    def OnHelp(self, event):
        self.help = helpDialog(None, -1, "Help")
        self.help.Show()

    def OnQuit(self, event):
        if self.help:
            self.help.Destroy()
        self.panel.mgr.UnInit()
        self.Destroy()


def read_config():
    config_dict = {'show_fullpath': False,
                   'hide_extension': False,
                   'match_firstletter': False,
                   'keep_match_ext': False,
                   'folder_sources': os.getcwd(),
                   'folder_choices': os.getcwd(),
                   'filters': default_filters,
                   'masks': default_masks,
                   'masks_test': default_masks_teststring,
                   'filters_test': default_filters_teststring,
                   }

    INI_show_fullpath_val = config_dict['show_fullpath']
    INI_hide_extension_val = config_dict['hide_extension']
    INI_keep_match_ext_val = config_dict['keep_match_ext']
    INI_match_firstletter_val = config_dict['match_firstletter']
    INI_folder_sources_val = config_dict['folder_sources']
    INI_folder_choices_val = config_dict['folder_choices']
    INI_filters_val = config_dict['filters']
    INI_masks_val = config_dict['masks']
    INI_filters_test_val = config_dict['filters_test']
    INI_masks_test_val = config_dict['masks_test']

    # read config file
    try:
        config_file = os.sep.join([os.getcwd(), 'config.ini'])
        config = configparser.ConfigParser()
        cfg_file = config.read(config_file, encoding='utf-8-sig')
        if not len(cfg_file):
            return config_dict
        try:
            INI_global_cat = config['global']
        except KeyError:
            pass
        try:
            INI_recent_cat = config['recent']
        except KeyError:
            pass
        try:
            INI_matching_cat = config['matching']
        except KeyError:
            pass

        try:
            INI_show_fullpath_val = True if INI_global_cat['show_fullpath'] == 'True' else False
        except KeyError:
            pass
        try:
            INI_hide_extension_val = True if INI_global_cat['hide_extension'] == 'True' else False
        except KeyError:
            pass
        try:
            INI_keep_match_ext_val = True if INI_global_cat['keep_match_ext'] == 'True' else False
        except KeyError:
            pass
        try:
            INI_match_firstletter_val = True if INI_global_cat['match_firstletter'] == 'True' else False
        except KeyError:
            pass
        try:
            INI_folder_sources_val = INI_recent_cat['folder_sources']
        except KeyError:
            pass
        try:
            INI_folder_choices_val = INI_recent_cat['folder_choices']
        except KeyError:
            pass
        try:
            INI_filters_val = INI_matching_cat['filters']
        except KeyError:
            pass
        try:
            INI_masks_val = INI_matching_cat['masks']
        except KeyError:
            pass
        try:
            INI_masks_test_val = INI_matching_cat['masks_test']
        except KeyError:
            pass
        try:
            INI_filters_test_val = INI_matching_cat['filters_test']
        except KeyError:
            pass

    except configparser.Error as e:
        logging.error("%s when reading config file '%s'" %
                      (e.args[0], config_file))
        return config_dict

    config_dict['show_fullpath'] = INI_show_fullpath_val
    config_dict['hide_extension'] = INI_hide_extension_val
    config_dict['keep_match_ext'] = INI_keep_match_ext_val
    config_dict['match_firstletter'] = INI_match_firstletter_val
    config_dict['folder_sources'] = INI_folder_sources_val
    config_dict['folder_choices'] = INI_folder_choices_val
    config_dict['filters'] = INI_filters_val
    config_dict['masks'] = INI_masks_val
    config_dict['filters_test'] = INI_filters_test_val
    config_dict['masks_test'] = INI_masks_test_val
    FileMasked.masks = CompileMasks(config_dict['masks'])
    FileFiltered.filters = CompileFilters(config_dict['filters'])

    return config_dict


def write_config(config_dict):
    config_file = os.sep.join([os.getcwd(), 'config.ini'])
    config = configparser.ConfigParser()
    config['global'] = {'show_fullpath':
                        config_dict['show_fullpath'],
                        'hide_extension':
                        config_dict['hide_extension'],
                        'keep_match_ext':
                        config_dict['keep_match_ext'],
                        'match_firstletter':
                        config_dict['match_firstletter']
                        }
    config['matching'] = {'masks':
                          config_dict['masks'],
                          'filters':
                          config_dict['filters'],
                          'masks_test':
                          config_dict['masks_test'],
                          'filters_test':
                          config_dict['filters_test']
                          }
    config['recent'] = {'folder_sources':
                        config_dict['folder_sources'],
                        'folder_choices':
                        config_dict['folder_choices']
                        }

    with open(config_file, 'w') as configfile:
        config.write(configfile)


def getDoc():
    return (
        "<p>This application uses a list of input files and will rename each one with the most similar file from another list of files.<p>"
        "<h3>Terminology</h3>"
        "The following terminology is used in the application, and in this document:"
        "<ul>"
        "<li>The input files to rename are called the <b>sources</b>;</li>"
        "<li>The files used to search for similarity are called the <b>choices</b>;</li>"
        "<li>The process to search the most similar <b>choice</b> for a given <b>source</b> is referred here as <b>matching</b> process;</li>"
        "<li>A <b>file path</b> is composed of a <b>parent directory</b> and a <b>file name</b>;<br>e.g. <b>file path</b>=c:/foo/bar/setup.tar.gz, <b>parent directory</b>=c:/foo/bar, <b>file name</b>=setup.tar.gz</li>"
        "<li>A <b>file name</b> is composed of a <b>stem</b> and a <b>suffix</b>;<br>e.g. <b>file name</b>=setup.tar.gz, <b>stem</b>=setup.tar, <b>suffix</b>=.gz</li>"
        "</ul>"
        "<h3>Principles</h3>"
        "<p>Here is the process applied to match and rename each <b>source</b>:</p>"
        "<pre>"
        " <font color=\"red\">Choices</font>────┐<br>"
        "            │<br>"
        "        ┌───┴────┐                     ┌────────┐<br>"
        " <font color=\"blue\">Source</font>─┤Matching├─<font color=\"red\">Most Similar Choice</font>─┤Renaming├─<font color=\"red\">Renamed</font> <font color=\"blue\">Source</font><br>"
        "        └────────┘                     └────────┘"
        "</pre>"
        "<p>When searching for the most similar <b>choice</b>, only the stems of <b>choices</b> and stem of <b>source</b> are compared.</p>"
        "<p>When renaming a <b>source</b> file path, only the stem is renamed with the most similar stem amongst <b>choices</b> file pathes.</p>"
        "<p>E.g. if <b>source</b> is <font color=\"blue\">c:/foo/Amaryllis.png</font>, and <b>most similar choice</b> is <font color=\"red\">d:/bar/Amaryllidinae.jpg</font>, <b>renamed source</b> is <font color=\"blue\">c:/foo/</font><font color=\"red\">Amaryllidinae</font><font color=\"blue\">.png</font></p>"
        "<p>If <b>masks</b> and <b>filters</b> are applied, the process applied to match and rename each <b>source</b> is the following:</p>"
        "<pre>"
        "                                ┌─────────┐<br>"
        "                      <font color=\"red\">Choices</font>───┤Filtering├────<font color=\"red\">Filtered Choices</font>────────┐<br>"
        "                                └─────────┘                            │<br>"
        "        ┌───────┐               ┌─────────┐                        ┌───┴────┐                     ┌────────┐                       ┌─────────┐<br>"
        " <font color=\"blue\">Source</font>─┤Masking├─<font color=\"blue\">Masked Source</font>─┤Filtering├─<font color=\"blue\">Masked&Filtered Source</font>─┤Matching├─<font color=\"red\">Most Similar Choice</font>─┤Renaming├─<font color=\"blue\">Masked</font> <font color=\"red\">Renamed</font> <font color=\"blue\">Source</font>─┤Unmasking├─<font color=\"green\">Unmasked</font> <font color=\"red\">Renamed</font> <font color=\"blue\">Source</font><br>"
        "        └───┬───┘               └─────────┘                        └────────┘                     └────────┘                       └────┬────┘<br>"
        "            │                                                                                                                           │<br>"
        "            └────────────────────────────────────────── <font color=\"green\">Leading & Trailing Masks</font> ───────────────────────────────────────────────────────┘"
        "</pre>"
        "<h3>Sources</h3>"
        "<p>Sources are entered in the following ways:"
        "<ul><li>click on the \"Sources\" button to add a selection of files to the current <b>sources</b></li>"
        "<li>Go to \"File->Sources->Sources from Directory\" menu to add files from a selected folder to the current <b>sources</b></li>"
        "<li>Go to \"File->Sources->Sources from Clipboard\" menu to add files or folders from clipboard to the current <b>sources</b></li>"
        "<li>Drag files or folders into application panel and choose \"Sources\" to add those to the current <b>sources</b></li>"
        "<li>Paste (Ctrl+V) into application panel and choose \"Sources\" to add the files or folders in clipboard to the current <b>sources</b></li></ul>"
        "<h3>Choices</h3>"
        "<p>Choices are entered in the following ways:"
        "<ul><li>click on the \"Choices\" button to add a selection of files to the current <b>choices</b></li>"
        "<li>Go to \"File->Choices->Choices from Directory\" menu to add files from a selected folder to the current <b>choices</b></li>"
        "<li>Go to \"File->Choices->Choices from Clipboard\" menu to add files or folders from clipboard to the current <b>choices</b></li>"
        "<li>Drag files or folders into application panel and choose \"Choices\" to add those to the current <b>choices</b></li>"
        "<li>Paste (Ctrl+V) into application panel and choose \"Choices\" to add the files or folders in clipboard to the current <b>choices</b></li></ul>"
        "<h3>Filters</h3>"
        "<p>To ease the <b>matching</b> process, filters can be applied to <b>sources</b> and <b>choices</b> before they are compared.</p>"
        "<p>E.g. <b>source</b> is <font color=\"blue\">c:/foo/The Amaryllis.png</font> and <b>choice</b> is <font color=\"red\">d:/bar/Amaryllidinae, The.txt</font>. It would be smart to clean the <b>sources</b> and <b>choices</b> by ignoring all articles before trying to find the <b>most similar choice</b>.</p>"
        "<p>To achieve this, the application uses <b>filters</b>.</p>"
        "<p>The filters are using Python regular expression patterns with capture groups (). The captured groups are replaced by a given expression (usually empty to clean a string). This is applied to both <b>sources</b> and <b>choices</b> when <b>matching</b> occurs.</p>"
        "<p>Filters are only applied for the <b>matching</b> process, original unfiltered files are used otherwise.</p>"
        "<p>For example, to clean articles of <b>source</b> and <b>choice</b> file, a filter with the pattern '(^the\b|, the)' with an empty replacement ' ' could be used:<br>"
        "<ol>"
        "<li><b>Filtering source</b>: <font color=\"blue\">c:/foo/The Amaryllis.png</font> &#11106; <font color=\"blue\">Amaryllis</font></li>"
        "<li><b>Filtering choice</b>: <font color=\"red\">d:/bar/Amaryllidinae, The.txt</font> &#11106; <font color=\"red\">Amaryllidinae</font></li>"
        "<li><b>Matching</b>: <font color=\"blue\">The Amaryllis</font> &#11106; <font color=\"red\">Amaryllidinae, The</font></li>"
        "<li><b>Renaming</b>: <font color=\"blue\">c:/foo/The Amaryllis.png</font> &#11106; <font color=\"blue\">c:/foo/</font><font color=\"red\">Amaryllidinae, The</font><font color=\"blue\">.png</font></li>"
        "</ol>"
        "<p>Filters creation, addition, deletion, re-ordering is available from \"Masks &amp; Filters\" button.</p>"
        "<ul>"
        "<li>Edition of the filter name, pattern and replace is done directly by cliking on the filter list cells</li>"
        "<li>Deletion of filters is done by pressing the [DELETE] key on some selected filter items or from the context menu on selected filter items.</li>"
        "<li>Addition of a filter is done from the context menu on filter list.</li>"
        "<li>Re-ordering a filter is done by dragging and dropping the filter item across the filter list.</li>"
        "</ul>"
        "<h3>Masks</h3>"
        "<p>Sometimes, it can be interesting to ignore some leading and/or trailing parts from a <b>source</b> in the <b>matching</b> process and restore them after the <b>renaming</b> process. It is particularly important in order to enhance <b>matching</b> when <b>choices</b> don't contain these parts.</p>"
        "<p>E.g. <b>source</b> is <font color=\"blue\">c:/foo/(1983-06-22) Amaryllis [Russia].png</font>, and we want to ignore the date <font color=\"blue\">(1983-06-22)</font> and the country <font color=\"blue\">[Russia]</font> during <b>matching</b> but we need to restore them when <b>renaming</b>, "
        " then if <b>most similar choice</b> is <font color=\"red\">d:/bar/Amaryllidinae.jpg</font>, the <b>renamed source</b> should be <font color=\"blue\">c:/foo/(1983-06-22) </font><font color=\"red\">Amaryllidinae</font><font color=\"blue\"> [Russia].png</font></p>"
        "<p>To achieve this, the application uses <b>masks</b>.</p>"
        "<p>The masks are using Python regular expression patterns. They are removed from <b>sources</b> strings before <b>filtering</b> and <b>matching</b> occur."
        "It is used to remove leading and trailing expressions (year, disk#...) before <b>matching</b> and restore them after <b>renaming</b>.</p>"
        "<p>For example, to preserve the Disk number at the end of a <b>source</b> file, a mask with the pattern '(\\s?disk\\d)$' could be used:<br>"
        "<ol>"
        "<li><b>Masking</b>: <font color=\"blue\">c:/foo/The Wiiire Disk1.rom</font> &#11106; <font color=\"blue\">The Wiiire</font> + Trailing mask = <font color=\"green\"> Disk1</font></li>"
        "<li><b>Matching</b>: <font color=\"blue\">The Wiiire</font> &#11106; <font color=\"red\">The Wire</font></li>"
        "<li><b>Renaming</b>: <font color=\"blue\">c:/foo/The Wiiire.rom</font> &#11106; <font color=\"blue\">c:/foo/</font><font color=\"red\">The Wire</font><font color=\"blue\">.rom</font></li>"
        "<li><b>Unmkasking</b>: <font color=\"blue\">c:/foo/The Wiiire.rom</font> &#11106; <font color=\"blue\">c:/foo/The Wire<font color=\"green\"> Disk1</font>.rom</font></li>"
        "</ol>"
        "<p>Masks creation, addition, deletion, re-ordering is available from \"Masks &amp; Filters\" button.</p>"
        "<ul>"
        "<li>Edition of the mask name and pattern is done directly by cliking on the mask list cells</li>"
        "<li>Deletion of masks is done by pressing the [DELETE] key on some selected mask items or from the context menu on selected mask items.</li>"
        "<li>Addition of a mask is done from the context menu on mask list.</li>"
        "<li>Re-ordering a mask is done by dragging and dropping the mask item across the mask list.</li>"
        "</ul>")


Quit_16_PNG = PyEmbeddedImage("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAVklEQVQ4jWNgYGCoYGBgWEIkXsrAwBDKgAaWoAvgARoMDAw1owZQZoAAAwODEQMDQzYDA4MCIQPEGBgYAnDgNAYGhmswQ2hmAMVewAYGPhYGqQEUZWcALdEnU4lzkXYAAAAASUVORK5CYII=")
Clipboard_16_PNG = PyEmbeddedImage("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAtklEQVQ4jcXSLQoCURiF4SdYpk+1WLS4ATEKYtA2zQUYzTLRLGaNioILcQtux+AHyjB3dJIfvOXcw3t/uKQnwznIGnq1M8IRi+AYWeMUuMWOD8wwDGaRnaNT1AnWmKLEHfnHWh5ZGZ11SrDEHltcvd/gGtk+Oo2CsuGa5a+CPk4V+m0E/z9Bx+vlP+m0EfSwq9BrI8gwqJC1EXSxqdD9VXDAOMHhm2CC1RcmKcEcF+/vm+ISXfAEy/NDr/2o1MAAAAAASUVORK5CYII=")
AddFile_16_PNG = PyEmbeddedImage("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAv0lEQVQ4jeXTsUvCQRjG8Q+KYhFEUnuD4W90aHZtjf4dUxpyc3QQQTCTIGpJh/6KxD/JwfdHFL/qcvWB43mP5/i+d8cd1PCC+R9jiroCHWFUFHzTEm9FkFTAAkN84HAXQBOXmOB8F0Cu+z0GXOAGT/8FVDFGH9foxfpyKuAO7aivwtsYpAJm0S2zfUwZKnhOBcxxgFusw4/xgJII3/38iVY+L60bfoLHX5p+0Rle0YqjtGLeSAXkkF5su4PTPNgARiAq9du6DoYAAAAASUVORK5CYII=")
AddFolder_16_PNG = PyEmbeddedImage("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAArklEQVQ4je3SMQuBYRTF8Z9FMSgxG4zKKj6ChdikzD6CL2AXpQy2txSDUiZfzuAmKXles1N3uMP5n/M8XVgge5kDWnIoe9sruKD2KwCauL41e531N0Cu0D8gHVBED2Oc8gLaOGOOEY4YpAKKYS6hig4KWKGbAuhFchX9MDZQxzYFMI7anTDfMEMZO1j6fLKZx4cdo3YjzDDB9Ev4U0NsonY5zPuAJqvr8eZdJBfgDs5MKn5hEi99AAAAAElFTkSuQmCC")
ProcessMatch_16_PNG = PyEmbeddedImage("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAApklEQVQ4je3RMQ4BURSF4S9BZwWjIlGpZDqFEoUtmMQuTDVEopmShkRiDzaoeAoS7w29vz33nntyLu9MUeGGErkv6eKCDYZoY4QDanSaDM4YR7QFdqnl6fNyiiMGMbESYqeYoYiJN7QaDPrYx8RSKCzFEquYmAttp7iilxqoMY9oa2wbDugIrzoJhfWF2Nfn8h1ZkwnhVYVQ2OoldvaLSYy/yWeTyQNeOBiZybXdVAAAAABJRU5ErkJggg==")
Rename_16_PNG = PyEmbeddedImage("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAQklEQVQ4jWNgoBPgYWBgWMLAwLABSouQa9ASSl2C1YBJUAli8D00/iRSnYWudsmoAVQygOJoJAXQJiUSA6iWmTAAAFKsJvUTORWWAAAAAElFTkSuQmCC")
Rename_32_PNG = PyEmbeddedImage("iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAj0lEQVRYhe2XsQ2AIBBF3wq2dq7gAiziEI7jGC5jYmdpQ2JhQWtzBQ1BDYIk95JfEC7hBYrjQElLA4yBtDkEOmCVHMDprfscAj4TMOc+VAVeCRgpTJ0N2CM1BmAAnBinzCISoX0nZzMA9s5VPST2BFYFVEAFVEAFfiVQtBkVb8dfUc+PSAVSUnwwKT6a1ccFLuSbvR2v1tcAAAAASUVORK5CYII=")
Reset_16_PNG = PyEmbeddedImage("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAUklEQVQ4jaWTyREAIAgDtw5KsW0b9ONDxzOEd7IDAQAKEOgV3UsAVYQsHgVy1P5Anpqb4LvLnVDOaTRkQp4gKbMNsEawQrTWaB2Sdcr2M1nv3AAJSRotv+t5dgAAAABJRU5ErkJggg==")
Filters_16_PNG = PyEmbeddedImage("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAnElEQVQ4jc3OPQ4BURTF8R/xlZDYinJKdDQS6tkGk1gDralohkYvszyFJxERzIvCSU7y3rn3f3IhQxHpTHjEqvhJQYY0Ak6xun+2mFeAF9g8BjXsMPkCnobd2vOgjgOGb+AR9mH3pZo4IXkxS3BE49OJHZwxeMgGIWt/gu/qokQruAxZJeXoBedV4f8p6GOJdWzBBbMYGMZu57/VFRydH90nhFjmAAAAAElFTkSuQmCC")
Undo_16_PNG = PyEmbeddedImage("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAxElEQVQ4jaXSsUpCcRiG8V9J0eFEoEcIb6BNcLJBSAgOnCCdwkWn8BLcdHFqcDBwaWmpwcWKLqx7aDgNYh06+H/gXT54H74PPrhCAylq6CHGHUYYoo8LBbSQoI0zdHCCa2Q/GWCOD1wWicoQYYFZiAQm8rP25hAbVEMkGcYhghhPIQJ4DSmfYxkiuJc/3V7U8IbK9vCgZPkIL3ZeO8W0RLmJd3S3h218YYXHgjxjjQec7lojfOIG9T+S4Pi/1SLcljjhF9+1HBfjit47pQAAAABJRU5ErkJggg==")
Preview_16_PNG = PyEmbeddedImage("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAApklEQVQ4jd3STQrCMBAF4A8KihfSVXVlQV31CAXdCbrXY+gRRMVLunBCQ9EiuHPgkeQlbzJ//K0NUWEbqIL7SnjEFQ3GgSa4Y5+jKR6xwgaXwKbzpuyKV7hhlIl32f0O69iPcMcyXdY4ocgElzcR5lwRmvoXB+fkQITTl8L+TQqL7g+lV4FmcV5ri5jEMx+KmGyIg7aNk0Bq48GX8zDAXDtI8+D+0Z4L/CAYjFzsAAAAAABJRU5ErkJggg==")
Info_16_PNG = PyEmbeddedImage("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAvUlEQVQ4jaWTMQ7CMAxFX6QideEaGdlY2gGxMCP1KByhp0inniAj52PIL2pTp0D50l8S/2/HsWENB7RAD4xirzNnxC9wBiLwADxQiV5nUTEmOiAA9UaCWjGdlTkYgquYI8wrcSrNynwUrUqitLSk9+U4AU/gZtwhTQOpw74QdBcteGkZSZ3+1aCSdrfBYTL4+wmlJn4yeDdx6xtLBotvhPIgXcQcA8ZIfzvKA8YozyvZvUwTHKk5+To3GOv8AnPjI1AbZiwoAAAAAElFTkSuQmCC")
Help_16_PNG = PyEmbeddedImage("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAA+klEQVQ4ja3TMVLDQAwF0OeCVHTgMfcgjD2h4wq5TVzmCmYwpVvT5RbuciQKy5PFLJkUaGaLlf5fSX8lfluBVxwxxDmGr8jgf9gLTphQ4z5OHb5TYLK2x4gSn6iS2FP4ysDsc5nH1f2ARzygxXMSH9NKiiitTABvOKOLcw7fYmVwCmZxpihxG8APbBLCBn3EtoGdsGNWuI6eD5Htbt1jPHIOTIUmuAaz0qLnLkNerDNrIjjDvzyQttBGmZsMeWmhXbewiNi7iNi7LmIvEfHaN7674Ru5bZC2SfxLZqSvjXIVZf85ymnmZZkal2Vq3LBMixVmcdbrvJNZ52/umT0spYP52gAAAABJRU5ErkJggg==")

if __name__ == '__main__':

    config_dict = read_config()

    app = wx.App(False)
    frame = MainFrame()
    app.SetTopWindow(frame)

    app.MainLoop()

#!/usr/bin/python

import argparse
import os
import io
import time
import re
import sys
import logging
import os.path
import wx
import wx.adv
import wx.aui
import wx.lib.mixins.listctrl as listmix
from wx.lib.embeddedimage import PyEmbeddedImage
from pathlib import Path
import configparser
import fuzzywuzzy.fuzz, fuzzywuzzy.process
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

default_filters = '+Strip brackets\n'+ \
                  r'" ?[\(\[\{][^\)\]\}]+[\)\]\}]"'+'\n'+ \
                  r'" "'+'\n'+ \
                 '+Strip articles\n'+ \
                  r'"([\W]|\b\d\b|^(the|a)\b|, the)"'+'\n'+ \
                  r'" "'+'\n'+ \
                 '+Strip non alphanumeric\n'+ \
                  r'"(?ui)\W"'+'\n'+ \
                  r'" "'

def strip_illegal_chars(s):
    s = re.sub(r'(?<=\S)[' + illegal_chars + r'](?=\S)', '-', s)
    s = re.sub(r'\s?[' + illegal_chars + r']\s?', ' ', s)
    return s

def strip_extra_whitespace(s):
    return ' '.join(s.split()).strip()
    
def mySimilarityScorer(s1, s2):
    return fuzzywuzzy.fuzz.WRatio(s1, s2, force_ascii=False, full_process=False)

def filename_clean_process(file, regexps):
    ret = file.stem
    # convert to lowercase.
    ret = ret.lower()
    # remove leading and trailing whitespaces.
    ret = ret.strip()
    # apply regexps
    for regexp in regexps:
        ret = regexp[0].sub(regexp[1], ret)
    ret = ' '.join(ret.split())
    if file.stem != ret:
        wx.LogMessage('String cleaned : %s --> %s' %(file.stem, ret))
    return ret
    
def fuzz_processor(file):
    return file.cleaned

def get_matches(sources):
    ret = []
    Qmatch_firstletter = config_dict['match_firstletter']
    for f in sources:
        if not candidates:
            ret.append(None)
            continue
        f_cleaned = FileCleaned(f)
        if not f_cleaned:
            ret.append(None)
            continue
        if Qmatch_firstletter:
            first_letter = f_cleaned.cleaned[0]
            if first_letter in candidates.keys():
                ret.append(FileMatch(f, fuzzywuzzy.process.extract(f_cleaned, candidates[first_letter], scorer = mySimilarityScorer, processor = fuzz_processor, limit = 10)))
            else:
                ret.append(None)
        else:
            ret.append(FileMatch(f, fuzzywuzzy.process.extract(f_cleaned, candidates['all'], scorer = mySimilarityScorer, processor = fuzz_processor, limit = 10)))
    return ret

def get_match(source):
    ret = None
    if not candidates:
        return ret
    f_cleaned = FileCleaned(source)
    if not f_cleaned:
        return ret
        
    if config_dict['match_firstletter']:
        first_letter = f_cleaned.cleaned[0]
        if first_letter in candidates.keys():
            ret = fuzzywuzzy.process.extract(f_cleaned, candidates[first_letter], scorer = mySimilarityScorer, processor = fuzz_processor, limit = 10)
    else:
        ret = fuzzywuzzy.process.extract(f_cleaned, candidates['all'], scorer = mySimilarityScorer, processor = fuzz_processor, limit = 10)
    return ret
    
def getRenamePreview(input, match):
    if not match:
        return None
    Qkeep_match_ext = config_dict['keep_match_ext']
    match_clean = strip_extra_whitespace(strip_illegal_chars(match.stem))
    if Qkeep_match_ext:
        match_clean += match.suffix
    return Path(os.path.join(str(input.parent), match_clean) + input.suffix)

def RefreshCandidates():
    global candidates
    candidates.clear()
    candidates['all'] = [FileCleaned(f) for f in glob_choices]
    if config_dict['match_firstletter']:
        for word in candidates['all']:
            first_letter = word.cleaned[0]
            if first_letter in candidates.keys():
                candidates[first_letter].append(word)
            else:
                candidates[first_letter] = [word]
    
class FileMatch:
    def __init__(self, file, match_results):
        self.file = file
        self.match_results = match_results

class FileCleaned:
    regexps = []
    def __init__(self, file):
        self.file = file
        self.cleaned = filename_clean_process(file, FileCleaned.regexps)
        
    def CompileRegexps(config):
        FileCleaned.regexps.clear()
        lines = config.splitlines()
        it = iter(lines)
        for l1,l2,l3 in zip(it,it,it):
            if l1.startswith('+'):
                FileCleaned.regexps.append((re.compile(l2.strip()[1:-1]), l3.strip()[1:-1]))

########################################################################
class FuzzyRenamerFileDropTarget(wx.FileDropTarget):
    def __init__(self, window):
        wx.FileDropTarget.__init__(self)
        self.window = window
        
    def OnDropFiles(self, x, y, filenames):
        Qsources = self.SourcesOrChoices(self.window)
        files = []
        for f in filenames:
            fp = Path(f)
            if fp.is_file():
                files.append(f)
            elif fp.is_dir():
                for fp2 in fp.resolve().glob('*'):
                    if fp2.is_file():
                        files.append(str(fp2))
        if Qsources:
            self.window.AddSourceFromFiles(files)
        else:
            self.window.AddChoicesFromFiles(files)
        return True
        
    def SourcesOrChoices(self, parent, question = "Add the files to source or choice list?", caption = 'Drag&Drop question'):
        dlg = wx.MessageDialog(parent, question, caption, wx.YES_NO | wx.ICON_QUESTION)
        dlg.SetYesNoLabels('Sources','Choices')
        result = dlg.ShowModal() == wx.ID_YES
        dlg.Destroy()
        return result        

########################################################################
class FuzzyRenamerListCtrl(wx.ListCtrl, listmix.ColumnSorterMixin):
 
    def __init__(self, parent, ID=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.ColumnSorterMixin.__init__(self, 4)
        self.EnableCheckBoxes()
        self.Bind(wx.EVT_CHAR, self.onKeyPress)
        self.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnBeginLabelEdit)
        self.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnEndLabelEdit)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.RightClickCb)

        self.InsertColumn(0, 'Source Name', width=300)
        self.InsertColumn(1, 'Similarity(%)', width=80)
        self.InsertColumn(2, 'Closest Match', width=300)
        self.InsertColumn(3, 'Renaming Preview', width=300)

        self.listdata = {}
        self.itemDataMap = self.listdata

    def onKeyPress( self, event ):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_SPACE:
            index = self.GetFirstSelected()
            check = True
            if index != -1:
                if self.IsItemChecked(index):
                    check = False
            if self.GetSelectedItemCount() == 1 :
                check = not check
            while index != -1:
                self.CheckItem(index, check)
                index = self.GetNextSelected(index)
        elif keycode == wx.WXK_F2:
            if self.GetSelectedItemCount() == 1 :
                index = self.GetFirstSelected()
        elif keycode == wx.WXK_CONTROL_A:
            item = -1
            while 1:
                item = self.GetNextItem(item)
                if item == -1:
                    break
                self.SetItemState(item, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
        elif keycode == wx.WXK_DELETE:
            l = []
            row_id = -1
            while True: # find all the selected items and put them in a list
                row_id = self.GetNextItem(row_id, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
                if row_id == -1:
                    break
                l.append(row_id)
 
            l.reverse() # Delete all the items, starting with the last item
            for row_id in l:
                pos = self.GetItemData(row_id) # 0-based unsorted index
                data = self.listdata[pos]
                filepath = str(data[data_struct.FILENAME])
                self.DeleteItem(row_id)
                del self.listdata[pos]

        if keycode:
            event.Skip()

    def RightClickCb( self, event ):
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
                menu.Append( id.GetValue(), "[%d%%] %s" % (match[1], match[0].file.stem))
                self.Bind(wx.EVT_MENU, self.MenuSelectionCb, id=id)
                forced_match_id[id] = (event.GetIndex(), match[0].file)

            self.PopupMenu( menu, event.GetPoint() )
            menu.Destroy()
        
    def MenuSelectionCb( self, event ):
        row_id, forced_match = forced_match_id[event.GetId()]
        forced_match_id.clear()
        pos = self.GetItemData(row_id) # 0-based unsorted index
        similarity = mySimilarityScorer(FileCleaned(self.listdata[pos][data_struct.FILENAME]).cleaned, FileCleaned(forced_match).cleaned)
        self.listdata[pos][data_struct.MATCH_SCORE] = similarity
        self.listdata[pos][data_struct.MATCHNAME] = forced_match
        self.listdata[pos][data_struct.PREVIEW] = getRenamePreview(self.listdata[pos][data_struct.FILENAME],forced_match)

        Qview_fullpath = config_dict['show_fullpath']
        Qhide_extension = config_dict['hide_extension']
        self.SetItem(row_id, data_struct.MATCH_SCORE, str(self.listdata[pos][data_struct.MATCH_SCORE]))
        self.SetItem(row_id, data_struct.MATCHNAME, str(self.listdata[pos][data_struct.MATCHNAME]) if Qview_fullpath else (self.listdata[pos][data_struct.MATCHNAME].stem if Qhide_extension else self.listdata[pos][data_struct.MATCHNAME].name))
        self.SetItem(row_id, data_struct.PREVIEW, str(self.listdata[pos][data_struct.PREVIEW]) if Qview_fullpath else (self.listdata[pos][data_struct.PREVIEW].stem if Qhide_extension else self.listdata[pos][data_struct.PREVIEW].name))

    def OnBeginLabelEdit( self, event ):
        event.Allow()
        if config_dict['show_fullpath']:
            d = Path(event.GetLabel())
            (self.GetEditControl()).SetValue(d.name)

    def OnEndLabelEdit(self, event):
        if event.IsEditCancelled() or not event.GetLabel():
            event.Veto()
            return
        row_id = event.GetIndex()
        pos = self.GetItemData(row_id) # 0-based unsorted index
        new_name = event.GetLabel()
        old_path = self.listdata[pos][data_struct.FILENAME]
        old_name = old_path.name
        new_name_clean = strip_extra_whitespace(strip_illegal_chars(new_name))

        event.Veto() # do not allow further process as we will edit ourself the item label

        if new_name != new_name_clean:
            wx.LogMessage('String cleaned : %s --> %s' %(new_name, new_name_clean))

        if new_name_clean != old_name:
            old_file = str(old_path)
            new_file = os.path.join(str(old_path.parent), new_name_clean)
            new_path = Path(new_file)

            try:
                os.rename(old_file, new_file)
                wx.LogMessage('Renaming : %s --> %s' %(old_file, new_file))

                Qview_fullpath = config_dict['show_fullpath']
                Qhide_extension = config_dict['hide_extension']

                new_match = get_match(new_path)
                if new_match:
                    self.listdata[pos] = [new_path, new_match[0][1], new_match[0][0].file, getRenamePreview(new_path, new_match[0][0].file), old_path]
                    self.SetItem(row_id, data_struct.MATCH_SCORE, str(self.listdata[pos][data_struct.MATCH_SCORE]))
                    self.SetItem(row_id, data_struct.MATCHNAME, str(self.listdata[pos][data_struct.MATCHNAME]) if Qview_fullpath else (self.listdata[pos][data_struct.MATCHNAME].stem if Qhide_extension else self.listdata[pos][data_struct.MATCHNAME].name))
                    self.SetItem(row_id, data_struct.PREVIEW, str(self.listdata[pos][data_struct.PREVIEW]) if Qview_fullpath else (self.listdata[pos][data_struct.PREVIEW].stem if Qhide_extension else self.listdata[pos][data_struct.PREVIEW].name))
                else:
                    self.listdata[pos] = [new_path, None, None, None, old_path]
                    self.SetItem(row_id, data_struct.MATCH_SCORE, '')
                    self.SetItem(row_id, data_struct.MATCHNAME, '')
                    self.SetItem(row_id, data_struct.PREVIEW, '')

                self.SetItem(row_id, data_struct.FILENAME, str(self.listdata[pos][data_struct.FILENAME]) if Qview_fullpath else (self.listdata[pos][data_struct.FILENAME].stem if Qhide_extension else self.listdata[pos][data_struct.FILENAME].name))

            except (OSError, IOError):
                wx.LogMessage('Error when renaming : %s --> %s' %(old_file, new_file))
        else:
            wx.LogMessage('Not renaming %s (same name)' %(old_name))

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
            pos = self.GetItemData(row_id) # 0-based unsorted index
            data = self.listdata[pos]
            filepath = str(data[data_struct.FILENAME])
            self.SetItem(row_id, data_struct.FILENAME, filepath if Qview_fullpath else (data[data_struct.FILENAME].stem if Qhide_extension else data[data_struct.FILENAME].name))
            if data[data_struct.MATCHNAME]:
                self.SetItem(row_id, data_struct.MATCH_SCORE, str(data[data_struct.MATCH_SCORE]))
                self.SetItem(row_id, data_struct.MATCHNAME, str(data[data_struct.MATCHNAME]) if Qview_fullpath else (data[data_struct.MATCHNAME].stem if Qhide_extension else data[data_struct.MATCHNAME].name))
                self.SetItem(row_id, data_struct.PREVIEW, str(data[data_struct.PREVIEW]) if Qview_fullpath else (data[data_struct.PREVIEW].stem if Qhide_extension else data[data_struct.PREVIEW].name))
            else:
                self.SetItem(row_id, data_struct.MATCH_SCORE, '')
                self.SetItem(row_id, data_struct.MATCHNAME, '')
                self.SetItem(row_id, data_struct.PREVIEW, '')

    def AddToList(self, newdata):
        Qview_fullpath = config_dict['show_fullpath']
        Qhide_extension = config_dict['hide_extension']
        
        index = 0 if not self.listdata else sorted(self.listdata.keys())[-1]+1 # start indexing after max index 
        row_id = self.GetItemCount()
        
        for data in newdata:

            filepath = str(data[data_struct.FILENAME])
            
            # Treat duplicate file
            item_name = str(data[data_struct.FILENAME]) if Qview_fullpath else (data[data_struct.FILENAME].stem if Qhide_extension else data[data_struct.FILENAME].name)
            found = self.FindItem(-1, item_name)
            if found != -1:
                continue

            self.InsertItem(row_id, item_name)
            if data[data_struct.MATCHNAME]:
                self.SetItem(row_id, data_struct.MATCH_SCORE, str(data[data_struct.MATCH_SCORE]))
                self.SetItem(row_id, data_struct.MATCHNAME, str(data[data_struct.MATCHNAME]) if Qview_fullpath else (data[data_struct.MATCHNAME].stem if Qhide_extension else data[data_struct.MATCHNAME].name))
                self.SetItem(row_id, data_struct.PREVIEW, str(data[data_struct.PREVIEW]) if Qview_fullpath else (data[data_struct.PREVIEW].stem if Qhide_extension else data[data_struct.PREVIEW].name))
            self.SetItemData(row_id, index)
            self.CheckItem(row_id, True)
            self.listdata[index] = data
            row_id += 1
            index += 1
        
########################################################################
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

        btn_filters = wx.Button(panel_listbutton, label="Filters")
        btn_filters.SetBitmap(Filters_16_PNG.GetBitmap(), wx.LEFT)
        btn_filters.SetToolTip("Edit string filters")

        btn_ren = wx.Button(panel_listbutton, label="Rename")
        btn_ren.SetBitmap(Rename_16_PNG.GetBitmap(), wx.LEFT)
        btn_ren.SetToolTip("Rename sources")

        btn_undo = wx.Button(panel_listbutton, label="Undo")
        btn_undo.SetBitmap(Undo_16_PNG.GetBitmap(), wx.LEFT)
        btn_undo.SetToolTip("Undo last rename")

        panel_listbutton_sizer = wx.BoxSizer(wx.HORIZONTAL)
        panel_listbutton_sizer.Add(btn_add_source_from_files, 0, wx.ALL, 1)
        panel_listbutton_sizer.Add(btn_add_choice_from_file, 0, wx.ALL, 1)
        panel_listbutton_sizer.Add(btn_run, 0, wx.ALL, 1)
        panel_listbutton_sizer.Add(btn_reset, 0, wx.ALL, 1)
        panel_listbutton_sizer.Add(btn_filters, 0, wx.ALL, 1)
        panel_listbutton_sizer.Add(btn_ren, 0, wx.ALL, 1)
        panel_listbutton_sizer.Add(btn_undo, 0, wx.ALL, 1)
        panel_listbutton.SetSizer(panel_listbutton_sizer)
        
        self.list_ctrl = FuzzyRenamerListCtrl(panel_list, size=(-1,-1), style=wx.LC_REPORT|wx.BORDER_SUNKEN|wx.LC_EDIT_LABELS)

        file_drop_target = FuzzyRenamerFileDropTarget(self)
        self.SetDropTarget(file_drop_target)

        panel_list_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_list_sizer.Add(panel_listbutton, 0, wx.EXPAND|wx.ALL, 0)
        panel_list_sizer.Add(self.list_ctrl, 1, wx.EXPAND|wx.ALL, 0)
        panel_list.SetSizer(panel_list_sizer)
       
        panel_log = wx.Panel(parent=self)

        log = wx.TextCtrl(panel_log, -1, style = wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
        wx.Log.SetActiveTarget(wx.LogTextCtrl(log))
        
        log_sizer = wx.BoxSizer()
        log_sizer.Add(log, 1, wx.EXPAND|wx.ALL, 5)
        panel_log.SetSizer(log_sizer)
        
        self.mgr.AddPane(panel_top, wx.aui.AuiPaneInfo().Name("pane_list").CenterPane())
        self.mgr.AddPane(panel_log, wx.aui.AuiPaneInfo().CloseButton(True).Name("pane_log").Caption("Log").FloatingSize(-1,200).BestSize(-1,200).MinSize(-1,120).Bottom())
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

    def OnSelectFilters(self, event):
        dia = filtersFrame(None, -1, "Filters")
        if dia.ShowModal() == wx.ID_OK:
            pass

    def OnAddSourceFromDir(self, evt):
        with wx.DirDialog (self, "Choose source directory", config_dict['folder_sources'], wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST) as dirDialog:

            if dirDialog.ShowModal() == wx.ID_CANCEL:
                return
                
            self.AddSourceFromDir(dirDialog.GetPath())
            
    def AddSourceFromDir(self, directory):
        global config_dict
        config_dict['folder_sources'] = directory
        write_config(config_dict)
        newdata = []
        for f in Path(directory).resolve().glob('*'):
            if f.is_file():
                newdata.append([f, None, None, None, f])
        self.list_ctrl.AddToList(newdata)

    def OnAddSourceFromFiles(self, evt):
        with wx.FileDialog (self, "Choose source files", config_dict['folder_sources'], style=wx.FD_DEFAULT_STYLE | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            self.AddSourceFromFiles(fileDialog.GetPaths())
            
    def AddSourceFromFiles(self, files):
        global config_dict

        newdata = []
        first = True
        for f in files:
            fp = Path(f)
            if fp.is_file():
                if first:
                    first = False
                    config_dict['folder_sources'] = str(fp.parent)
                    write_config(config_dict)
                newdata.append([fp, None, None, None, fp])
        self.list_ctrl.AddToList(newdata)
            
    def OnAddSourceFromClipboard(self, evt):
        text_data = wx.TextDataObject()
        if wx.TheClipboard.Open():
            success = wx.TheClipboard.GetData(text_data)
            wx.TheClipboard.Close()
        if success:
            newdata = []
            lines = text_data.GetText().splitlines()
            for line in lines:
                f = Path(line)
                if f.is_file():
                    newdata.append([f, None, None, None, f])
            self.list_ctrl.AddToList(newdata)

    def OnAddChoicesFromDir(self, evt):
        with wx.DirDialog (self, "Choose choice directory", config_dict['folder_choices'], wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST) as dirDialog:

            if dirDialog.ShowModal() == wx.ID_CANCEL:
                return
            self.AddChoicesFromDir(dirDialog.GetPath())

    def AddChoicesFromDir(self, directory):
        global glob_choices, config_dict
        config_dict['folder_choices'] = directory
        write_config(config_dict)
        for f in Path(directory).resolve().glob('*'):
            if f.is_file():
                glob_choices.add(f)
        RefreshCandidates()

    def OnAddChoicesFromFiles(self, evt):
        with wx.FileDialog (self, "Choose choice files", config_dict['folder_choices'], style=wx.FD_DEFAULT_STYLE | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            self.AddChoicesFromFiles(fileDialog.GetPaths())
                    
    def AddChoicesFromFiles(self, files):
        global glob_choices, config_dict
        first = True
        for f in files:
            fp = Path(f)
            if first:
                first = False
                config_dict['folder_choices'] = str(fp.parent)
                write_config(config_dict)
            if fp.is_file():
                glob_choices.add(fp)
        RefreshCandidates()

    def OnAddChoicesFromClipboard(self, evt):
        global glob_choices
        text_data = wx.TextDataObject()
        if wx.TheClipboard.Open():
            success = wx.TheClipboard.GetData(text_data)
            wx.TheClipboard.Close()
        if success:
            for line in text_data.GetText().splitlines():
                f = Path(line)
                if f.is_file():
                    glob_choices.add(f)
            RefreshCandidates()

    def OnRun(self, evt):
        if not glob_choices:
            return
        
        sources = []
        row_id = -1
        while True: # loop all the checked items
            row_id = self.list_ctrl.GetNextItem(row_id)
            if row_id == -1:
                break
            if self.list_ctrl.IsItemChecked(row_id):
                pos = self.list_ctrl.GetItemData(row_id) # 0-based unsorted index
                sources.append(self.list_ctrl.listdata[pos][data_struct.FILENAME])

        matches = get_matches(sources)
        row_id = -1
        count = 0
        while True: # loop all the checked items
            row_id = self.list_ctrl.GetNextItem(row_id)
            if row_id == -1:
                break
            if self.list_ctrl.IsItemChecked(row_id):
                pos = self.list_ctrl.GetItemData(row_id) # 0-based unsorted index
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
        dia = filtersDialog(None, -1, "Filters")
        res = dia.ShowModal()
        if res == wx.ID_OK:
            config_dict['regexps'] = dia.GetFilters()
            FileCleaned.CompileRegexps(config_dict['regexps'])
            write_config(config_dict)

        dia.Destroy()
        
    def OnRename(self, evt):
        Qview_fullpath = config_dict['show_fullpath']
        Qhide_extension = config_dict['hide_extension']
        row_id = -1
        while True: # loop all the checked items
            row_id = self.list_ctrl.GetNextItem(row_id)
            if row_id == -1:
                break
            if self.list_ctrl.IsItemChecked(row_id):
                pos = self.list_ctrl.GetItemData(row_id) # 0-based unsorted index

                old_path = self.list_ctrl.listdata[pos][data_struct.FILENAME]
                preview_path = self.list_ctrl.listdata[pos][data_struct.PREVIEW]
                if preview_path:
                    if old_path != preview_path:
                        old_file = str(old_path)
                        new_file = str(preview_path)
                        try:
                            os.rename(old_file, new_file)
                            wx.LogMessage('Renaming : %s --> %s' %(old_file, new_file))
                            new_path = Path(new_file)
                            new_match = get_match(new_path)
                            if new_match:
                                self.list_ctrl.listdata[pos] = [new_path, new_match[0][1], new_match[0][0].file, getRenamePreview(new_path, new_match[0][0].file), old_path]
                                self.list_ctrl.SetItem(row_id, data_struct.MATCH_SCORE, str(self.list_ctrl.listdata[pos][data_struct.MATCH_SCORE]))
                                self.list_ctrl.SetItem(row_id, data_struct.MATCHNAME, str(self.list_ctrl.listdata[pos][data_struct.MATCHNAME]) if Qview_fullpath else (self.list_ctrl.listdata[pos][data_struct.MATCHNAME].stem if Qhide_extension else self.list_ctrl.listdata[pos][data_struct.MATCHNAME].name))
                                self.list_ctrl.SetItem(row_id, data_struct.PREVIEW, str(self.list_ctrl.listdata[pos][data_struct.PREVIEW]) if Qview_fullpath else (self.list_ctrl.listdata[pos][data_struct.PREVIEW].stem if Qhide_extension else self.list_ctrl.listdata[pos][data_struct.PREVIEW].name))
                            else:
                                self.list_ctrl.listdata[pos] = [new_path, None, None, None, old_path]
                                self.list_ctrl.SetItem(row_id, data_struct.MATCH_SCORE, '')
                                self.list_ctrl.SetItem(row_id, data_struct.MATCHNAME, '')
                                self.list_ctrl.SetItem(row_id, data_struct.PREVIEW, '')

                            self.list_ctrl.SetItem(row_id, data_struct.FILENAME, str(self.list_ctrl.listdata[pos][data_struct.FILENAME]) if Qview_fullpath else (self.list_ctrl.listdata[pos][data_struct.FILENAME].stem if Qhide_extension else self.list_ctrl.listdata[pos][data_struct.FILENAME].name))
                        
                        except (OSError, IOError):
                            wx.LogMessage('Error when renaming : %s --> %s' %(old_file, new_file))
                    else:
                        wx.LogMessage('Not renaming %s (same name)' %(old_path.name))
                else:
                    wx.LogMessage('Not renaming %s (no match)' %(old_path.name))

    def OnUndo(self, evt):
        Qview_fullpath = config_dict['show_fullpath']
        Qhide_extension = config_dict['hide_extension']
        row_id = -1
        while True: # loop all the checked items
            row_id = self.list_ctrl.GetNextItem(row_id)
            if row_id == -1:
                break
            pos = self.list_ctrl.GetItemData(row_id) # 0-based unsorted index

            currrent_path = self.list_ctrl.listdata[pos][data_struct.FILENAME]
            previous_path = self.list_ctrl.listdata[pos][data_struct.PREVIOUS_FILENAME]

            if currrent_path != previous_path:
                old_file = str(currrent_path)
                new_file = str(previous_path)
                try:
                    os.rename(old_file, new_file)
                    wx.LogMessage('Renaming : %s --> %s' %(old_file, new_file))
                    new_path = Path(new_file)
                    new_match = get_match(new_path)
                    if new_match:
                        self.list_ctrl.listdata[pos] = [new_path, new_match[0][1], new_match[0][0].file, getRenamePreview(new_path, new_match[0][0].file), new_path]
                        self.list_ctrl.SetItem(row_id, data_struct.MATCH_SCORE, str(self.list_ctrl.listdata[pos][data_struct.MATCH_SCORE]))
                        self.list_ctrl.SetItem(row_id, data_struct.MATCHNAME, str(self.list_ctrl.listdata[pos][data_struct.MATCHNAME]) if Qview_fullpath else (self.list_ctrl.listdata[pos][data_struct.MATCHNAME].stem if Qhide_extension else self.list_ctrl.listdata[pos][data_struct.MATCHNAME].name))
                        self.list_ctrl.SetItem(row_id, data_struct.PREVIEW, str(self.list_ctrl.listdata[pos][data_struct.PREVIEW]) if Qview_fullpath else (self.list_ctrl.listdata[pos][data_struct.PREVIEW].stem if Qhide_extension else self.list_ctrl.listdata[pos][data_struct.PREVIEW].name))
                    else:
                        self.list_ctrl.listdata[pos] = [new_path, None, None, None, new_path]
                        self.list_ctrl.SetItem(row_id, data_struct.MATCH_SCORE, '')
                        self.list_ctrl.SetItem(row_id, data_struct.MATCHNAME, '')
                        self.list_ctrl.SetItem(row_id, data_struct.PREVIEW, '')

                    self.list_ctrl.SetItem(row_id, data_struct.FILENAME, str(self.list_ctrl.listdata[pos][data_struct.FILENAME]) if Qview_fullpath else (self.list_ctrl.listdata[pos][data_struct.FILENAME].stem if Qhide_extension else self.list_ctrl.listdata[pos][data_struct.FILENAME].name))
                
                except (OSError, IOError):
                    wx.LogMessage('Error when renaming : %s --> %s' %(old_file, new_file))
            else:
                wx.LogMessage('Not renaming %s (same name)' %(currrent_path.name))
        
    def OnClose(self, event):
        # deinitialize the frame manager
        self.mgr.UnInit()
        # delete the frame
        self.Destroy()

class filtersDialog(wx.Dialog):
    def __init__(self, parent, id, label):
        wx.Dialog.__init__(self, parent, id, label, size=(350,300), style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        self.panel = filtersPanel(self)
        # Buttonsizer:
        btns = self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.APPLY)
        default_button = wx.FindWindowById(wx.ID_APPLY, self)
        default_button.SetLabel('Reset Filters')
        
        default_button.Bind(wx.EVT_BUTTON, self.OnReset)

        # Lay it all out:
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(self.panel, 1, wx.ALL|wx.EXPAND, 0)
        mainSizer.Add(btns, 0, wx.ALL|wx.EXPAND, 5)
        self.SetSizer(mainSizer)
        self.Fit()
        
    def GetFilters(self):
        ret = ''
        row_id = -1
        while 1:
            row_id = self.panel.list_ctrl.GetNextItem(row_id)
            if row_id == -1:
                break
            ret += '+' if self.panel.list_ctrl.IsItemChecked(row_id) else '-'
            ret += self.panel.list_ctrl.GetItemText(row_id,1) +'\n'
            ret += '"'+self.panel.list_ctrl.GetItemText(row_id, 2) +'"\n'
            ret += '"'+self.panel.list_ctrl.GetItemText(row_id, 3) +'"\n'
        return ret
        
    def OnReset(self, event):
        self.panel.list_ctrl.PopulateFilters(default_filters)

class filtersPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS)
        self.list_ctrl = FilterListCtrl(self, size=(-1,-1), style=wx.LC_REPORT|wx.BORDER_SUNKEN)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list_ctrl, 1, wx.ALL|wx.EXPAND)
        self.SetSizer(sizer)

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
            l = pickle.loads(ldata)
            # Add videos to this playlist
            self.dv._insert(x, y, l)
        return wx.DragMove

    def OnDragOver(self, x, y, d):
        return wx.DragMove
        
class FilterListCtrl(wx.ListCtrl, listmix.TextEditMixin):
 
    def __init__(self, parent, ID=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.TextEditMixin.__init__(self)
        self.EnableCheckBoxes()
        self.Bind(wx.EVT_CHAR, self.onKeyPress)
        self.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnBeginLabelEdit)
        self.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnEndLabelEdit)
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self._startDrag)

        self.InsertColumn(0, '#', width=35)
        self.InsertColumn(1, 'Filter Name', width=150)
        self.InsertColumn(2, 'Pattern', width=150)
        self.InsertColumn(3, 'Replace', width=150)

        dt = FilterListCtrlDropTarget(self)
        dt.SetDefaultAction(wx.DragMove)
        self.SetDropTarget(dt)
        
        self.PopulateFilters(config_dict['regexps'])

    def PopulateFilters(self, filters):
        self.DeleteAllItems()
        lines = filters.splitlines()
        it = iter(lines)
        row_id = 0
        index = 0
        for l1,l2,l3 in zip(it,it,it):
            data = (l1.strip()[1:], l2.strip()[1:-1], l3.strip()[1:-1])
            self.InsertItem(row_id, "%2d" % (int(index)+1))
            self.SetItem(row_id, 1, data[0])
            self.SetItem(row_id, 2, data[1])
            self.SetItem(row_id, 3, data[2])
            self.SetItemData(row_id, index)
            if (l1.strip()[0]) == '+':
                self.CheckItem(row_id, True)
            else:
                self.CheckItem(row_id, False)
            
            row_id += 1
            index += 1
        
    def onKeyPress( self, event ):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_DELETE:
            l = []
            row_id = -1
            while True: # find all the selected items and put them in a list
                row_id = self.GetNextItem(row_id, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
                if row_id == -1:
                    break
                l.append(row_id)
 
            l.reverse() # Delete all the items, starting with the last item
            for row_id in l:
                self.DeleteItem(row_id)
                
            # renumbering
            row_id = -1
            while 1:
                row_id = self.GetNextItem(row_id)
                if row_id == -1:
                    break
                self.SetItemData(row_id, row_id)
                self.SetItemText(row_id, "%2d" % (int(row_id)+1))

        if keycode:
            event.Skip()

    def OnBeginLabelEdit( self, event ):
        if event.GetColumn() == 0:
            event.Veto()
            row_id = event.GetIndex()
            self.CheckItem(row_id, not self.IsItemChecked(row_id))
        else:
            event.Skip()
                
    def OnEndLabelEdit(self, event):
        if event.IsEditCancelled():
            event.Veto()
        
    def getItemInfo(self, idx):
        """Collect all relevant data of a listitem, and put it in a list"""
        l = []
        l.append(idx) # We need the original index, so it is easier to eventualy delete it
        l.append(self.GetItemData(idx)) # Itemdata
        l.append(self.IsItemChecked(idx)) # check
        l.append(self.GetItemText(idx)) # Text first column
        for i in range(1, self.GetColumnCount()): # Possible extra columns
            l.append(self.GetItem(idx, i).GetText())
        return l

    def _startDrag(self, e):
        l = []
        row_id = -1
        while True: # find all the selected items and put them in a list
            row_id = self.GetNextItem(row_id, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
            if row_id == -1:
                break
            l.append(self.getItemInfo(row_id))
        
        # Pickle the items list.
        itemdata = pickle.dumps(l)
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
            l.reverse() # Delete all the items, starting with the last item
            for i in l:
                index = self.FindItem(i[0], i[3])
                self.DeleteItem(index)
                
            # renumbering
            row_id = -1
            while 1:
                row_id = self.GetNextItem(row_id)
                if row_id == -1:
                    break
                self.SetItemData(row_id, row_id)
                self.SetItemText(row_id, "%2d" % (int(row_id)+1))

    def _insert(self, x, y, seq):
        """ Insert text at given x, y coordinates --- used with drag-and-drop. """

        # Find insertion point.
        index, flags = self.HitTest((x, y))

        if index == wx.NOT_FOUND: # not clicked on an item
            if flags & (wx.LIST_HITTEST_NOWHERE|wx.LIST_HITTEST_ABOVE|wx.LIST_HITTEST_BELOW): # empty list or below last item
                index = self.GetItemCount() # append to end of list
            elif self.GetItemCount() > 0:
                if y <= self.GetItemRect(0).y: # clicked just above first item
                    index = 0 # append to top of list
                else:
                    index = self.GetItemCount() + 1 # append to end of list
        else: # clicked on an item
            # Get bounding rectangle for the item the user is dropping over.
            rect = self.GetItemRect(index)

            # If the user is dropping into the lower half of the rect, we want to insert _after_ this item.
            # Correct for the fact that there may be a heading involved
            if y > rect.y + rect.height/2:
                index += 1
        
        for i in seq: # insert the item data
            idx = self.InsertItem(index, i[3])
            self.SetItemData(idx, i[1])
            self.CheckItem(idx, i[2])
            for j in range(1, self.GetColumnCount()):
                try: # Target list can have more columns than source
                    self.SetItem(idx, j, i[3+j])
                except:
                    pass # ignore the extra columns
            index += 1
        
########################################################################
class MainFrame(wx.Frame):
 
    #----------------------------------------------------------------------
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, "PyFuzzy renamer",
                          pos = wx.Point(-10,0), size = wx.Size(1000,800))
 
        menubar = wx.MenuBar()
        self.statusbar = self.CreateStatusBar()
        files = wx.Menu()
        sources = wx.Menu()
        sources_= wx.MenuItem(files, 100, '&Sources', 'Select sources (to rename)')
        sources_.SetSubMenu(sources)

        source_from_dir = wx.MenuItem(sources, 102, '&Sources from Directory\tCtrl+S', 'Select sources from directory')
        source_from_dir.SetBitmap(AddFolder_16_PNG.GetBitmap())
        sources.Append(source_from_dir)

        source_from_clipboard = wx.MenuItem(sources, 103, 'Sources from &Clipboard\tCtrl+C', 'Select sources from clipboard')
        source_from_clipboard.SetBitmap(Clipboard_16_PNG.GetBitmap())
        sources.Append(source_from_clipboard)

        choices = wx.Menu()
        choices_= wx.MenuItem(files, 101, '&Choices', 'Select choices (to match)')
        choices_.SetSubMenu(choices)

        target_from_dir = wx.MenuItem(choices, 105, '&Choices from Directory\tCtrl+T', 'Select choices from directory')
        target_from_dir.SetBitmap(AddFolder_16_PNG.GetBitmap())
        choices.Append(target_from_dir)

        choices_from_clipboard = wx.MenuItem(choices, 106, 'Choices from &Clipboard\tCtrl+V', 'Select choices from clipboard')
        choices_from_clipboard.SetBitmap(Clipboard_16_PNG.GetBitmap())
        choices.Append(choices_from_clipboard)

        quit = wx.MenuItem(files, 104, '&Quit\tCtrl+Q', 'Quit the Application')
        quit.SetBitmap(Quit_16_PNG.GetBitmap())

        options = wx.Menu()
        view_fullpath = options.AppendCheckItem(202, '&View full path', 'View full path')
        view_fullpath.Check(config_dict['show_fullpath'])

        self.hide_extension = options.AppendCheckItem(203, '&Hide extension', 'Hide extension')
        self.hide_extension.Check(config_dict['hide_extension'])
        self.hide_extension.Enable(not config_dict['show_fullpath'])

        self.keep_match_ext = options.AppendCheckItem(201, '&Keep matched file extension', 'Keep matched file extension')
        self.keep_match_ext.Check(config_dict['keep_match_ext'])
        
        self.match_firstletter = options.AppendCheckItem(204, '&Always matched first letter', 'Always matched first letter')
        self.match_firstletter.Check(config_dict['match_firstletter'])
        
        files.Append(sources_)
        files.Append(choices_)
        files.Append(quit)

        menubar.Append(files, '&File')
        menubar.Append(options, '&Options')
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

        self.Show(True)

    def OnQuit(self, event):
        event.Skip()
        self.panel.mgr.UnInit()
        self.Destroy()

def read_config():
    #default
    config_dict = {
                   'show_fullpath': False,
                   'hide_extension': False,
                   'match_firstletter': False,
                   'keep_match_ext': False,
                   'folder_sources': os.getcwd(),
                   'folder_choices': os.getcwd(),
                   'regexps': default_filters
                   }

    INI_show_fullpath_val = config_dict['show_fullpath']
    INI_hide_extension_val = config_dict['hide_extension']
    INI_keep_match_ext_val = config_dict['keep_match_ext']
    INI_match_firstletter_val = config_dict['match_firstletter']
    INI_folder_sources_val = config_dict['folder_sources']
    INI_folder_choices_val = config_dict['folder_choices']
    INI_regexps_val = config_dict['regexps']
    
    # read config file
    try:
        config_file = os.sep.join([os.getcwd(), 'config.ini'])
        config = configparser.ConfigParser()
        cfg_file = config.read(config_file, encoding='utf-8-sig')
        if not len(cfg_file):
            return config_dict
        try:
            INI_global_cat = config['global']
        except KeyError as e:
            pass
        try:
            INI_recent_cat = config['recent']
        except KeyError as e:
            pass
        try:
            INI_matching_cat = config['matching']
        except KeyError as e:
            pass

        try:
            INI_show_fullpath_val = True if INI_global_cat['show_fullpath'] == 'True' else False
        except KeyError as e:
            pass
        try:
            INI_hide_extension_val = True if INI_global_cat['hide_extension'] == 'True' else False
        except KeyError as e:
            pass
        try:
            INI_keep_match_ext_val = True if INI_global_cat['keep_match_ext'] == 'True' else False
        except KeyError as e:
            pass
        try:
            INI_match_firstletter_val = True if INI_global_cat['match_firstletter'] == 'True' else False
        except KeyError as e:
            pass
        try:
            INI_folder_sources_val = INI_recent_cat['folder_sources']
        except KeyError as e:
            pass
        try:
            INI_folder_choices_val = INI_recent_cat['folder_choices']
        except KeyError as e:
            pass
        try:
            INI_regexps_val = INI_matching_cat['regexps']
        except KeyError as e:
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
    config_dict['regexps'] = INI_regexps_val
    FileCleaned.CompileRegexps(config_dict['regexps'])
    
    return config_dict

def write_config(config_dict):
    config_file = os.sep.join([os.getcwd(), 'config.ini'])
    config = configparser.ConfigParser()
    config['global'] = {'show_fullpath': \
                            config_dict['show_fullpath'],
                        'hide_extension': \
                            config_dict['hide_extension'],
                        'keep_match_ext': \
                            config_dict['keep_match_ext'],
                        'match_firstletter': \
                            config_dict['match_firstletter']
                       }
    config['matching'] = {'regexps': \
                            config_dict['regexps']
                       }
    config['recent'] = {'folder_sources': \
                            config_dict['folder_sources'],
                        'folder_choices': \
                            config_dict['folder_choices']
                        }

    with open(config_file, 'w') as configfile:
        config.write(configfile)
        
Quit_16_PNG = PyEmbeddedImage("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAVklEQVQ4jWNgYGCoYGBgWEIkXsrAwBDKgAaWoAvgARoMDAw1owZQZoAAAwODEQMDQzYDA4MCIQPEGBgYAnDgNAYGhmswQ2hmAMVewAYGPhYGqQEUZWcALdEnU4lzkXYAAAAASUVORK5CYII=")
Clipboard_16_PNG = PyEmbeddedImage("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAtklEQVQ4jcXSLQoCURiF4SdYpk+1WLS4ATEKYtA2zQUYzTLRLGaNioILcQtux+AHyjB3dJIfvOXcw3t/uKQnwznIGnq1M8IRi+AYWeMUuMWOD8wwDGaRnaNT1AnWmKLEHfnHWh5ZGZ11SrDEHltcvd/gGtk+Oo2CsuGa5a+CPk4V+m0E/z9Bx+vlP+m0EfSwq9BrI8gwqJC1EXSxqdD9VXDAOMHhm2CC1RcmKcEcF+/vm+ISXfAEy/NDr/2o1MAAAAAASUVORK5CYII=")
AddFile_16_PNG = PyEmbeddedImage("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAv0lEQVQ4jeXTsUvCQRjG8Q+KYhFEUnuD4W90aHZtjf4dUxpyc3QQQTCTIGpJh/6KxD/JwfdHFL/qcvWB43mP5/i+d8cd1PCC+R9jiroCHWFUFHzTEm9FkFTAAkN84HAXQBOXmOB8F0Cu+z0GXOAGT/8FVDFGH9foxfpyKuAO7aivwtsYpAJm0S2zfUwZKnhOBcxxgFusw4/xgJII3/38iVY+L60bfoLHX5p+0Rle0YqjtGLeSAXkkF5su4PTPNgARiAq9du6DoYAAAAASUVORK5CYII=")
AddFolder_16_PNG = PyEmbeddedImage("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAArklEQVQ4je3SMQuBYRTF8Z9FMSgxG4zKKj6ChdikzD6CL2AXpQy2txSDUiZfzuAmKXles1N3uMP5n/M8XVgge5kDWnIoe9sruKD2KwCauL41e531N0Cu0D8gHVBED2Oc8gLaOGOOEY4YpAKKYS6hig4KWKGbAuhFchX9MDZQxzYFMI7anTDfMEMZO1j6fLKZx4cdo3YjzDDB9Ev4U0NsonY5zPuAJqvr8eZdJBfgDs5MKn5hEi99AAAAAElFTkSuQmCC")
ProcessMatch_16_PNG = PyEmbeddedImage("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAApklEQVQ4je3RMQ4BURSF4S9BZwWjIlGpZDqFEoUtmMQuTDVEopmShkRiDzaoeAoS7w29vz33nntyLu9MUeGGErkv6eKCDYZoY4QDanSaDM4YR7QFdqnl6fNyiiMGMbESYqeYoYiJN7QaDPrYx8RSKCzFEquYmAttp7iilxqoMY9oa2wbDugIrzoJhfWF2Nfn8h1ZkwnhVYVQ2OoldvaLSYy/yWeTyQNeOBiZybXdVAAAAABJRU5ErkJggg==") 
Rename_16_PNG = PyEmbeddedImage("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAQklEQVQ4jWNgoBPgYWBgWMLAwLABSouQa9ASSl2C1YBJUAli8D00/iRSnYWudsmoAVQygOJoJAXQJiUSA6iWmTAAAFKsJvUTORWWAAAAAElFTkSuQmCC")
Reset_16_PNG = PyEmbeddedImage("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAUklEQVQ4jaWTyREAIAgDtw5KsW0b9ONDxzOEd7IDAQAKEOgV3UsAVYQsHgVy1P5Anpqb4LvLnVDOaTRkQp4gKbMNsEawQrTWaB2Sdcr2M1nv3AAJSRotv+t5dgAAAABJRU5ErkJggg==")
Filters_16_PNG = PyEmbeddedImage("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAnElEQVQ4jc3OPQ4BURTF8R/xlZDYinJKdDQS6tkGk1gDralohkYvszyFJxERzIvCSU7y3rn3f3IhQxHpTHjEqvhJQYY0Ak6xun+2mFeAF9g8BjXsMPkCnobd2vOgjgOGb+AR9mH3pZo4IXkxS3BE49OJHZwxeMgGIWt/gu/qokQruAxZJeXoBedV4f8p6GOJdWzBBbMYGMZu57/VFRydH90nhFjmAAAAAElFTkSuQmCC")
Undo_16_PNG = PyEmbeddedImage("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAxElEQVQ4jaXSsUpCcRiG8V9J0eFEoEcIb6BNcLJBSAgOnCCdwkWn8BLcdHFqcDBwaWmpwcWKLqx7aDgNYh06+H/gXT54H74PPrhCAylq6CHGHUYYoo8LBbSQoI0zdHCCa2Q/GWCOD1wWicoQYYFZiAQm8rP25hAbVEMkGcYhghhPIQJ4DSmfYxkiuJc/3V7U8IbK9vCgZPkIL3ZeO8W0RLmJd3S3h218YYXHgjxjjQec7lojfOIG9T+S4Pi/1SLcljjhF9+1HBfjit47pQAAAABJRU5ErkJggg==")
Preview_16_PNG = PyEmbeddedImage("iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAApklEQVQ4jd3STQrCMBAF4A8KihfSVXVlQV31CAXdCbrXY+gRRMVLunBCQ9EiuHPgkeQlbzJ//K0NUWEbqIL7SnjEFQ3GgSa4Y5+jKR6xwgaXwKbzpuyKV7hhlIl32f0O69iPcMcyXdY4ocgElzcR5lwRmvoXB+fkQITTl8L+TQqL7g+lV4FmcV5ri5jEMx+KmGyIg7aNk0Bq48GX8zDAXDtI8+D+0Z4L/CAYjFzsAAAAAABJRU5ErkJggg==")

if __name__ == '__main__':

    config_dict = read_config()

    app = wx.App(False)
    frame = MainFrame()
    app.SetTopWindow(frame)

    app.MainLoop()

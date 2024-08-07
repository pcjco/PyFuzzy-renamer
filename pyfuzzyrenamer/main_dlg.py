import copy
import os
import os.path
import pickle as pickle
import operator
import wx
import wx.lib.agw.aui as aui
import wx.lib.agw.persist as PM
import wx.html
import wx.lib.busy
from collections import defaultdict, OrderedDict
from multiprocessing import cpu_count, freeze_support
from pathlib import Path

from . import __version__
from pyfuzzyrenamer import (
    args,
    bottom_notebook,
    config,
    filters,
    main_listctrl,
    icons,
    masks,
    masksandfilters_dlg,
    match,
    rename,
    undo,
    utils,
)
from pyfuzzyrenamer.config import get_config
from pyfuzzyrenamer.args import get_args

# candidates =
# {
#    "all" :
#    {
#        candidate1_masked : [ candidate1_filtered1, candidate1_filtered2, ... ],
#        candidate2_masked : [ candidate2_filtered1, candidate2_filtered2, ... ],
#        ...
#    },
#    "a" :
#    {
#        candidate_starting_with1_masked : [ candidate1_filtered1, candidate1_filtered2, ... ],
#        ...
#    },
#    "b" :
#    {
#        ...
#    },
#    ...
# }
candidates = {}
aliases = {}

# glob_choices =
# {
#    choice1 : alias1|None,
#    choice2 : alias2|None,
#    ...
# }
glob_choices = OrderedDict()

def getRenamePreview(input, matches):
    # input : list of Path or Strings
    # matches : list of Path or Strings

    Qinput_as_path = get_config()["input_as_path"]

    # replace matches value by alias if any
    if Qinput_as_path:
        matches = [match if not str(match) in aliases else Path(aliases[str(match)]) for match in matches]
    else:
        matches = [match if not match in aliases else aliases[match] for match in matches]
    
    Qrename_choice = get_config()["rename_choice"]
    if Qrename_choice:
        a = input
        input = matches
        matches = a
    
    ret = [[] for i in range(len(input))]
    Qkeep_match_ext = get_config()["keep_match_ext"]
    Qsource_w_multiple_choice = get_config()["source_w_multiple_choice"]
    if matches:
        f_masked = masks.FileMasked(matches[0], useFilter=False)
        stem, suffix = utils.GetFileStemAndSuffix(matches[0])
        if Qinput_as_path:
            match_clean = utils.strip_extra_whitespace(utils.strip_illegal_chars(f_masked.masked[1]))
        else:
            match_clean = utils.strip_extra_whitespace(f_masked.masked[1])

    done_in_last = -1
    already_used = set()
    for i in range(len(input)):
        inp = input[i]
        if matches:
            inp_masked = masks.FileMasked(inp, useFilter=False)
            stem_masked, suffix_masked = utils.GetFileStemAndSuffix(inp)
            inp_has_masked = inp_masked.masked[0] or inp_masked.masked[2]
            if inp_has_masked:
                preview_name = inp_masked.masked[0] + match_clean + inp_masked.masked[2]
                if Qinput_as_path:
                    ret[i] = [
                        Path(
                            os.path.join(
                                get_config()["folder_output"] if get_config()["folder_output"] else inp.parent,
                                preview_name + (suffix if Qkeep_match_ext else ""),
                            )
                            + suffix_masked
                        )
                    ]
                else:
                    ret[i] = [preview_name]
                already_used.add(preview_name)
            else:
                done_in_last = i

    if done_in_last != -1:
        ret2 = []
        inp = input[done_in_last]
        stem_masked, suffix_masked = utils.GetFileStemAndSuffix(inp)
        if Qsource_w_multiple_choice:
            for f in matches:
                f_masked = masks.FileMasked(f, useFilter=False)
                stem, suffix = utils.GetFileStemAndSuffix(f)
                if Qinput_as_path:
                    match_clean = utils.strip_extra_whitespace(utils.strip_illegal_chars(f_masked.masked[1]))
                else:
                    match_clean = utils.strip_extra_whitespace(f_masked.masked[1])
                preview_name = f_masked.masked[0] + match_clean + f_masked.masked[2]
                if not preview_name in already_used:
                    if Qinput_as_path:
                        ret2.append(
                            Path(
                                os.path.join(
                                    get_config()["folder_output"] if get_config()["folder_output"] else inp.parent,
                                    preview_name + (suffix if Qkeep_match_ext else ""),
                                )
                                + suffix_masked
                            )
                        )
                    else:
                        ret2.append(preview_name)
        else:
            if Qinput_as_path:
                ret2.append(
                    Path(
                        os.path.join(
                            get_config()["folder_output"] if get_config()["folder_output"] else inp.parent,
                            match_clean + (suffix if Qkeep_match_ext else ""),
                        )
                        + suffix_masked
                    )
                )
            else:
                ret2.append(match_clean)
        ret[done_in_last] = ret2
    return ret


def RefreshCandidates():
    global candidates, aliases
    candidates.clear()
    aliases.clear()

    if not glob_choices:
        return

    candidates = defaultdict(lambda: defaultdict(list))

    if get_config()["input_as_path"]:
        # get suffix counters
        suffix_counts = dict()

        wSuffix = 0
        woSuffix = 0
        for f in glob_choices:
            suffix_counts[f.suffix] = suffix_counts.get(f.suffix, 0) + 1
            if f.suffix:
                wSuffix += 1
            else:
                woSuffix += 1
        if woSuffix > wSuffix:
            # get most common suffix
            frequent_suffix = max(suffix_counts.items(), key=operator.itemgetter(1))[0]

        for f, alias in glob_choices.items():
            # add fake extension if non standard extension found
            if f.suffix and woSuffix > wSuffix and f.suffix != frequent_suffix:
                f = Path(str(f) + ".noext")
            key = masks.FileMasked(f, useFilter=True).masked[1]
            item = filters.FileFiltered(f)
            candidates["all"][key.lower()].append(item)
            if alias:
                aliases[str(f)] = alias
    else:
        # glob_choices are strings
        for f, alias in glob_choices.items():
            key = masks.FileMasked(f, useFilter=True).masked[1]
            item = filters.FileFiltered(f)
            candidates["all"][key.lower()].append(item)
            if alias:
                aliases[f] = alias

    if get_config()["match_firstletter"]:
        for key, value in candidates["all"].items():
            candidates[key[0].lower()][key] = value

    wx.LogMessage("Choices : %d" % len(candidates["all"]))

class FuzzyRenamerDropTarget(wx.DropTarget):
    def __init__(self, window):
        wx.DropTarget.__init__(self)
        self.window = window
        self.data = wx.DataObjectComposite()
        self.data.Add(wx.FileDataObject(), True)
        self.data.Add(wx.TextDataObject())
        self.SetDataObject(self.data)
        
    def OnDrop(self, x, y):
        return True

    def OnDropFiles(self, filenames, mode = 0):
        Qinput_as_path = get_config()["input_as_path"]
        if not mode:
            Qsources = self.SourcesOrChoices(self.window)
        else:
            Qsources = (mode == 1)
        files = []
        if Qinput_as_path:
            for f in filenames:
                try:
                    fp = Path(f)
                    if fp.is_dir():
                        for fp2 in fp.resolve().glob("*"):
                            if fp2.is_file():
                                files.append(str(fp2))
                    else:
                        files.append(f)
                except (OSError, IOError):
                    pass
        else:
            files = filenames
        
        if files:
            if Qsources:
                self.window.AddSourcesFromFiles(files)
            else:
                self.window.AddChoicesFromFiles(files)
        return True

    def OnData(self, x, y, d):
        if not self.GetData():
            return wx.DragNone

        dataobjComp = self.GetDataObject()
        format = dataobjComp.GetReceivedFormat()
        dataobj = dataobjComp.GetObject(format)
        
        filenames = []
        if format.GetType() == wx.DF_TEXT or format.GetType() == wx.DF_UNICODETEXT:
            filenames = dataobj.GetText().splitlines()
        elif format.GetType() == wx.DF_FILENAME:
            filenames = dataobj.GetFilenames()
        self.OnDropFiles(filenames)
        return wx.DragCopy
        
    def SourcesOrChoices(
        self, parent, question="Add content to source or choice list?", caption="Drag&Drop question",
    ):
        paste_default = get_config()["paste_forced"]
        if not paste_default:
            dlg = wx.RichMessageDialog(parent, question, caption, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
            dlg.SetYesNoLabels("Sources", "Choices")
            dlg.ShowCheckBox("Remember my choice")
            Qsources = (dlg.ShowModal() == wx.ID_YES)
            if dlg.IsCheckBoxChecked():
                get_config()["paste_forced"] = 1 if Qsources else 2
                self.GetParent().GetParent().GetParent().mnu_source_from_clipboard_default.Check(Qsources)
                self.GetParent().GetParent().GetParent().mnu_choices_from_clipboard_default.Check(not Qsources)
            dlg.Destroy()
        else:
            Qsources = (paste_default == 1)
        return Qsources

class MainPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, name="mainpanel", style=wx.WANTS_CHARS)

        self.parent = parent

        self.mgr = aui.AuiManager()
        self.mgr.SetManagedWindow(self)

        panel_top = wx.Panel(parent=self)
        self.panel_list = wx.Panel(parent=panel_top)
        panel_listbutton = wx.Panel(parent=self.panel_list)

        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_sizer.Add(self.panel_list, 1, wx.EXPAND)
        panel_top.SetSizer(top_sizer)

        btn_add_source_from_files = wx.Button(panel_listbutton, label="Sources...")
        btn_add_source_from_files.SetBitmap(icons.AddFile_16_PNG.GetBitmap(), wx.LEFT)
        btn_add_source_from_files.SetToolTip("Add sources from files")

        btn_add_choice_from_file = wx.Button(panel_listbutton, label="Choices...")
        btn_add_choice_from_file.SetBitmap(icons.AddFile_16_PNG.GetBitmap(), wx.LEFT)
        btn_add_choice_from_file.SetToolTip("Add choices from files")

        btn_run = wx.Button(panel_listbutton, label="Best match")
        btn_run.SetBitmap(icons.ProcessMatch_16_PNG.GetBitmap(), wx.LEFT)
        btn_run.SetToolTip("Find best choice for each source")

        btn_reset = wx.Button(panel_listbutton, label="Reset")
        btn_reset.SetBitmap(icons.Reset_16_PNG.GetBitmap(), wx.LEFT)
        btn_reset.SetToolTip("Reset source and choice lists")

        btn_filters = wx.Button(panel_listbutton, label="Masks && Filters...")
        btn_filters.SetBitmap(icons.Filters_16_PNG.GetBitmap(), wx.LEFT)
        btn_filters.SetToolTip("Edit list of masks and filters")

        self.btn_ren = wx.Button(panel_listbutton, label="Rename")
        self.btn_ren.SetBitmap(icons.Rename_16_PNG.GetBitmap(), wx.LEFT)
        self.btn_ren.SetToolTip("Rename sources")

        self.btn_undo = wx.Button(panel_listbutton, label="Undo Rename")
        self.btn_undo.SetBitmap(icons.Undo_16_PNG.GetBitmap(), wx.LEFT)
        self.btn_undo.SetToolTip("Undo last rename")

        btn_duplicate = wx.Button(panel_listbutton, label="Duplicate")
        btn_duplicate.SetBitmap(icons.Exclamation_16_PNG.GetBitmap(), wx.LEFT)
        btn_duplicate.SetToolTip("Log renamed duplicates")

        panel_listbutton_sizer = wx.BoxSizer(wx.HORIZONTAL)
        panel_listbutton_sizer.Add(btn_add_source_from_files, 0, wx.ALL, 1)
        panel_listbutton_sizer.Add(btn_add_choice_from_file, 0, wx.ALL, 1)
        panel_listbutton_sizer.Add(btn_filters, 0, wx.ALL, 1)
        panel_listbutton_sizer.Add(btn_run, 0, wx.ALL, 1)
        panel_listbutton_sizer.Add(btn_reset, 0, wx.ALL, 1)
        panel_listbutton_sizer.Add(btn_duplicate, 0, wx.ALL, 1)
        panel_listbutton_sizer.Add(self.btn_ren, 0, wx.ALL, 1)
        panel_listbutton_sizer.Add(self.btn_undo, 0, wx.ALL, 1)
        panel_listbutton.SetSizer(panel_listbutton_sizer)

        self.list_ctrl = main_listctrl.FuzzyRenamerListCtrl(
            self.panel_list, size=(-1, -1), style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_EDIT_LABELS,
        )

        drop_target = FuzzyRenamerDropTarget(self)
        self.SetDropTarget(drop_target)

        panel_list_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_list_sizer.Add(panel_listbutton, 0, wx.EXPAND | wx.ALL, 0)
        panel_list_sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 0)
        self.panel_list.SetSizer(panel_list_sizer)

        self.bottom_notebook = bottom_notebook.bottomNotebook(self)
        self.bottom_notebook.AddPage(bottom_notebook.TabLog(parent=self.bottom_notebook), "Log")

        self.mgr.AddPane(panel_top, aui.AuiPaneInfo().Name("pane_list").CenterPane())
        self.mgr.AddPane(
            self.bottom_notebook,
            aui.AuiPaneInfo().CloseButton(True).Name("pane_output").Caption("Output").BestSize(-1, 200).Bottom(),
        )
        self.mgr.Update()

        self.mgr.Bind(aui.EVT_AUI_PANE_CLOSE, self.OnClosePane)
        btn_run.Bind(wx.EVT_BUTTON, self.OnRun)
        btn_duplicate.Bind(wx.EVT_BUTTON, self.OnLogDuplicate)
        self.btn_ren.Bind(wx.EVT_BUTTON, self.OnRename)
        btn_reset.Bind(wx.EVT_BUTTON, self.OnReset)
        btn_filters.Bind(wx.EVT_BUTTON, self.OnFilters)
        self.btn_undo.Bind(wx.EVT_BUTTON, self.OnUndo)
        btn_add_source_from_files.Bind(wx.EVT_BUTTON, self.OnAddSourcesFromFiles)
        btn_add_choice_from_file.Bind(wx.EVT_BUTTON, self.OnAddChoicesFromFiles)
        
        self.UpdateButtons()

    def UpdateButtons(self):
        Qinput_as_path = get_config()["input_as_path"]
        
        self.btn_undo.Show(Qinput_as_path)
        self.btn_ren.Show(Qinput_as_path)
        
        self.parent.mnu_rename_choice.Enable(Qinput_as_path)
        self.parent.mnu_view_fullpath.Enable(Qinput_as_path)
        self.parent.mnu_hide_extension.Enable(Qinput_as_path and not get_config()["show_fullpath"])
        self.parent.mnu_keep_match_ext.Enable(Qinput_as_path)
        self.parent.mnu_keep_original.Enable(Qinput_as_path)

        self.Layout()
    
    def OnToggleBottom(self, evt):
        item = self.parent.GetMenuBar().FindItemById(evt.GetId())
        get_config()["view_bottom"] = item.IsChecked()
        self.ToggleBottom()

    def ToggleBottom(self):
        # Show pane if hidden
        if get_config()["view_bottom"] and not self.mgr.GetPane(self.bottom_notebook).IsShown():
            self.mgr.ShowPane(self.bottom_notebook, show=True)
        # Hide pane if shown
        elif not get_config()["view_bottom"] and self.mgr.GetPane(self.bottom_notebook).IsShown():
            self.mgr.ShowPane(self.bottom_notebook, show=False)
        self.parent.mnu_show_log.Enable(get_config()["view_bottom"])

    def OnToggleLog(self, evt):
        item = self.parent.GetMenuBar().FindItemById(evt.GetId())
        get_config()["show_log"] = item.IsChecked()
        self.bottom_notebook.ToggleLog()

    def OnClosePane(self, evt):
        get_config()["view_bottom"] = False
        self.ToggleBottom()
        self.parent.mnu_view_bottom.Check(False)

    def OnViewFullPath(self, evt):
        item = self.parent.GetMenuBar().FindItemById(evt.GetId())
        get_config()["show_fullpath"] = item.IsChecked()
        self.parent.mnu_hide_extension.Enable(not get_config()["show_fullpath"])
        self.list_ctrl.RefreshList()

    def OnHideExtension(self, evt):
        item = self.parent.GetMenuBar().FindItemById(evt.GetId())
        get_config()["hide_extension"] = item.IsChecked()
        self.list_ctrl.RefreshList()

    def OnKeepMatchExtension(self, evt):
        item = self.parent.GetMenuBar().FindItemById(evt.GetId())
        get_config()["keep_match_ext"] = item.IsChecked()
        for index in self.list_ctrl.listdata.keys():
            self.list_ctrl.listdata[index][config.D_PREVIEW] = getRenamePreview(
                self.list_ctrl.listdata[index][config.D_FILENAME], self.list_ctrl.listdata[index][config.D_MATCHNAME],
            )
        self.list_ctrl.RefreshList()

    def OnRenameChoice(self, evt):
        item = self.parent.GetMenuBar().FindItemById(evt.GetId())
        get_config()["rename_choice"] = item.IsChecked()

    def OnKeepOriginal(self, evt):
        item = self.parent.GetMenuBar().FindItemById(evt.GetId())
        get_config()["keep_original"] = item.IsChecked()
        
    def OnFindBestAuto(self, evt):
        item = self.parent.GetMenuBar().FindItemById(evt.GetId())
        get_config()["best_auto"] = item.IsChecked()
        
    def OnDefaultPasteChoices(self, evt):
        item = self.parent.GetMenuBar().FindItemById(evt.GetId())
        if item.IsChecked():
            get_config()["paste_forced"] = 2            
            self.parent.mnu_source_from_clipboard_default.Check(False)
        else:
            get_config()["paste_forced"] = 0
            
    def OnDefaultPasteSource(self, evt):
        item = self.parent.GetMenuBar().FindItemById(evt.GetId())
        if item.IsChecked():
            get_config()["paste_forced"] = 1            
            self.parent.mnu_choices_from_clipboard_default.Check(False)
        else:
            get_config()["paste_forced"] = 0            

    def OnMatchFirstLetter(self, evt):
        item = self.parent.GetMenuBar().FindItemById(evt.GetId())
        get_config()["match_firstletter"] = item.IsChecked()
        RefreshCandidates()

    def OnSourceWMultipleChoice(self, evt):
        item = self.parent.GetMenuBar().FindItemById(evt.GetId())
        get_config()["source_w_multiple_choice"] = item.IsChecked()
        self.list_ctrl.RefreshList()

    def OnAddSourcesFromDir(self, evt):
        with wx.DirDialog(
            self, "Choose source directory", get_config()["folder_sources"], wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        ) as dirDialog:

            if dirDialog.ShowModal() == wx.ID_CANCEL:
                return
            self.AddSourcesFromDir(dirDialog.GetPath())

    def AddSourcesFromDir(self, directory):
        with wx.lib.busy.BusyInfo("Please wait...", wx.PyApp.GetMainTopWindow()):
            get_config()["folder_sources"] = directory
            Qinput_as_path = get_config()["input_as_path"]
            newdata = []
            if Qinput_as_path:
                for f in sorted(Path(directory).resolve().glob("*"), key=os.path.basename):
                    try:
                        if f.is_file():
                            newdata.append(f)
                    except (OSError, IOError):
                        pass
            else:
                for f in sorted(Path(directory).resolve().glob("*"), key=os.path.basename):
                    newdata.append(f)
            self.list_ctrl.AddToList(newdata)
            self.parent.UpdateRecentSources(directory)

    def OnAddSourcesFromFiles(self, evt):
        with wx.FileDialog(
            self,
            "Choose source files",
            get_config()["folder_sources"],
            style=wx.FD_DEFAULT_STYLE | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE,
        ) as self.fileDialog:

            if self.fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            self.AddSourcesFromFiles(self.fileDialog.GetPaths())

    def AddSourcesFromFiles(self, files):
        with wx.lib.busy.BusyInfo("Please wait...", wx.PyApp.GetMainTopWindow()):
            newdata = []
            Qinput_as_path = get_config()["input_as_path"]
            if Qinput_as_path:
                first = True
                for f in files:
                    if not f:
                        continue
                    try:
                        fp = Path(f)
                        if first:
                            first = False
                            get_config()["folder_sources"] = str(fp.parent)
                        newdata.append(fp)
                    except (OSError, IOError):
                        pass
            else:
                for f in files:
                    if not f:
                        continue
                    newdata.append(f)
            rowIds = self.list_ctrl.AddToList(newdata)

            # Special treatment for single source added : we focus on the item
            if len(rowIds) == 1:
                selected = utils.get_selected_items(self.list_ctrl)
                for row_id in selected:
                    self.list_ctrl.Select(row_id, on=False)
                self.list_ctrl.Select(max(rowIds), on=True)
                self.list_ctrl.Focus(max(rowIds))
                self.list_ctrl.EnsureVisible(max(rowIds))

    def OnAddSourcesFromClipboard(self, evt):
        files = utils.ClipBoardFiles(get_config()["input_as_path"])
        if files:
            self.AddSourcesFromFiles(files)

    def OnAddChoicesFromDir(self, evt):
        with wx.DirDialog(
            self, "Choose choice directory", get_config()["folder_choices"], wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        ) as dirDialog:

            if dirDialog.ShowModal() == wx.ID_CANCEL:
                return
            self.AddChoicesFromDir(dirDialog.GetPath())

    def AddChoicesFromDir(self, directory):
        with wx.lib.busy.BusyInfo("Please wait...", wx.PyApp.GetMainTopWindow()):
            get_config()["folder_choices"] = directory
            Qinput_as_path = get_config()["input_as_path"]
            if Qinput_as_path:
                for f in sorted(Path(directory).resolve().glob("*"), key=os.path.basename):
                    try:
                        if f.is_file():
                            glob_choices[f] = None
                    except (OSError, IOError):
                        pass
            else:
                for f in sorted(Path(directory).resolve().glob("*"), key=os.path.basename):
                    newdata.append(f)
            RefreshCandidates()
            self.parent.UpdateRecentChoices(directory)

    def OnAddChoicesFromFiles(self, evt):
        with wx.FileDialog(
            self,
            "Choose choice files",
            get_config()["folder_choices"],
            style=wx.FD_DEFAULT_STYLE | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE,
        ) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            self.AddChoicesFromFiles(fileDialog.GetPaths())

    def AddChoicesFromFiles(self, files):
        with wx.lib.busy.BusyInfo("Please wait...", wx.PyApp.GetMainTopWindow()):
            Qinput_as_path = get_config()["input_as_path"]
            if Qinput_as_path:
                first = True
                for f in files:
                    if not f:
                        continue
                    try:
                        fp = Path(f)
                        if first:
                            first = False
                            get_config()["folder_choices"] = str(fp.parent)
                        glob_choices[fp] = None
                    except (OSError, IOError):
                        pass
            else:
                for f in files:
                    if not f:
                        continue
                    glob_choices[f] = None
            RefreshCandidates()

    def OnAddChoicesFromClipboard(self, evt):
        files = utils.ClipBoardFiles(get_config()["input_as_path"])
        if files:
            self.AddChoicesFromFiles(files)

    def OnImportChoicesFromFile(self, evt):
        with wx.FileDialog(
            self, "Choose Choice file", wildcard="Excel files (*.xlsx)|*.xlsx|CSV files (*.csv)|*.csv|Text files (*.txt)|*.txt", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            self.ImportChoicesFromFile(fileDialog.GetPath())
            
    def ImportChoicesFromFile(self, file):
        with wx.lib.busy.BusyInfo("Please wait...", wx.PyApp.GetMainTopWindow()):
            fp = Path(file)
            if fp.suffix == ".xlsx":
                rows = utils.read_xlsx(file)
            elif fp.suffix == ".csv" or fp.suffix == ".txt" :
                rows = utils.read_csv(file)
            Qinput_as_path = get_config()["input_as_path"]
            for row in rows:
                f = row.get("A", None)
                alias = row.get("B", None)
                if not f:
                    continue
                if Qinput_as_path:
                    try:
                        fp2 = Path(f)
                        glob_choices[fp2] = alias
                    except (OSError, IOError):
                        pass
                else:
                    glob_choices[f] = alias
            RefreshCandidates()

        self.parent.UpdateRecentChoices(file)
        get_config()["folder_choices"] = str(fp.parent)

    def OnClearSource(self, event):
        self.list_ctrl.listdata.clear()
        self.list_ctrl.listdataname.clear()
        self.list_ctrl.listdatanameinv.clear()
        self.list_ctrl.DeleteAllItems()
    
    def OnClearChoices(self, event):
        glob_choices.clear()
        candidates.clear()
        aliases.clear()
        Qview_fullpath = get_config()["show_fullpath"]
        Qhide_extension = get_config()["hide_extension"]
        self.Freeze()
        row_id = -1
        while True:
            row_id = self.list_ctrl.GetNextItem(row_id)
            if row_id == -1:
                break
            self.list_ctrl.RefreshItem(
                row_id,
                score=0,
                matchnames=[],
                nbmatch=0,
                status=config.MatchStatus.NONE,
                Qview_fullpath=Qview_fullpath,
                Qhide_extension=Qhide_extension,
            )
            f = self.list_ctrl.GetItemFont(row_id)
            if not f.IsOk():
                f = self.list_ctrl.GetFont()
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            font.SetWeight(wx.FONTWEIGHT_NORMAL)
            font.SetStyle(f.GetStyle())
            self.list_ctrl.SetItemFont(row_id, font)
        self.Thaw()
 
    def OnSwap(self, event):
        sources = []
        row_id = -1
        while True:
            row_id = self.list_ctrl.GetNextItem(row_id)
            if row_id == -1:
                break
            pos = self.list_ctrl.GetItemData(row_id)  # 0-based unsorted index
            sources += self.list_ctrl.listdata[pos][config.D_FILENAME]
        choices = [str(key) for key in glob_choices]
        sources, choices = choices, sources
        self.OnReset(None)
        self.AddSourcesFromFiles(sources)
        self.AddChoicesFromFiles(choices)

    def OnOutputDirectory(self, evt):
        if self.parent.mnu_user_dir.IsChecked():
            self.parent.mnu_same_as_input.Check(False)
        else:
            self.parent.mnu_user_dir.Check(True)
        with wx.DirDialog(
            self, "Choose output directory", get_config()["folder_output"], wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        ) as dirDialog:

            if dirDialog.ShowModal() == wx.ID_CANCEL:
                return
            self.SetOutputDirectory(dirDialog.GetPath())
            
    def OnSameOutputDirectory(self, evt):
        if self.parent.mnu_same_as_input.IsChecked():
            self.parent.mnu_user_dir.Check(False)
            self.SetOutputDirectory("")
        else:
            self.parent.mnu_same_as_input.Check(True)

    def SetOutputDirectory(self, outdir):
        get_config()["folder_output"] = outdir
        for index in self.list_ctrl.listdata.keys():
            self.list_ctrl.listdata[index][config.D_PREVIEW] = getRenamePreview(
                self.list_ctrl.listdata[index][config.D_FILENAME], self.list_ctrl.listdata[index][config.D_MATCHNAME],
            )
        self.list_ctrl.RefreshList()

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
                sources.append(self.list_ctrl.listdata[pos][config.D_FILENAME])

        matches = match.get_matches(sources)
        row_id = -1
        count = 0
        Qview_fullpath = get_config()["show_fullpath"]
        Qhide_extension = get_config()["hide_extension"]
        self.list_ctrl.Freeze()
        while True:  # loop all the checked items
            if len(matches) < count + 1:
                break
            row_id = self.list_ctrl.GetNextItem(row_id)
            if row_id == -1:
                break
            if self.list_ctrl.IsItemChecked(row_id):
                f = self.list_ctrl.GetItemFont(row_id)
                if not f.IsOk():
                    f = self.list_ctrl.GetFont()
                font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
                font.SetWeight(wx.FONTWEIGHT_NORMAL)
                font.SetStyle(f.GetStyle())
                self.list_ctrl.SetItemFont(row_id, font)

                if matches[count]:
                    pos = self.list_ctrl.GetItemData(row_id)  # 0-based unsorted index
                    source = self.list_ctrl.listdata[pos][config.D_FILENAME]
                    nb_source = len(source)
                    matching_results = matches[count][0]["candidates"]
                    nb_match = len(matching_results)
                    self.list_ctrl.RefreshItem(
                        row_id,
                        score=matches[count][0]["score"],
                        matchnames=matching_results,
                        nbmatch=nb_match,
                        status=config.MatchStatus.MATCH,
                        Qview_fullpath=Qview_fullpath,
                        Qhide_extension=Qhide_extension,
                    )
                elif matches[count] is not None:
                    self.list_ctrl.RefreshItem(
                        row_id,
                        score=0,
                        matchnames=[],
                        nbmatch=0,
                        status=config.MatchStatus.NOMATCH,
                        Qview_fullpath=Qview_fullpath,
                        Qhide_extension=Qhide_extension,
                    )
                else:
                    break
                count += 1
        self.list_ctrl.Thaw()

    def OnReset(self, evt):
        glob_choices.clear()
        candidates.clear()
        aliases.clear()
        self.list_ctrl.listdata.clear()
        self.list_ctrl.listdataname.clear()
        self.list_ctrl.listdatanameinv.clear()
        self.list_ctrl.DeleteAllItems()

    def OnFilters(self, evt):
        dia = masksandfilters_dlg.masksandfiltersDialog(None, "Masks & Filters")
        res = dia.ShowModal()
        if res == wx.ID_OK:
            prev_filters = filters.FileFiltered.filters
            prev_masks = masks.FileMasked.masks
            get_config()["filters"] = dia.panel.filters_list.GetFilters()
            filters.FileFiltered.filters = filters.CompileFilters(get_config()["filters"])
            get_config()["masks"] = dia.panel.masks_list.GetMasks()
            masks.FileMasked.masks = masks.CompileMasks(get_config()["masks"])
            get_config()["filters_test"] = dia.panel.preview_filters.GetValue()
            get_config()["masks_test"] = dia.panel.preview_masks.GetValue()
            if prev_filters != filters.FileFiltered.filters or prev_masks != masks.FileMasked.masks:
                RefreshCandidates()

                # retrieve sources from list
                row_id = -1
                newdata = []
                while True:  # loop all the checked items
                    row_id = self.list_ctrl.GetNextItem(row_id)
                    if row_id == -1:
                        break
                    pos = self.list_ctrl.GetItemData(row_id)  # 0-based unsorted index
                    for f in self.list_ctrl.listdata[pos][config.D_FILENAME]:
                        newdata.append(f)
                self.list_ctrl.listdata.clear()
                self.list_ctrl.listdataname.clear()
                self.list_ctrl.listdatanameinv.clear()
                self.list_ctrl.DeleteAllItems()
                self.list_ctrl.AddToList(newdata)

        dia.Destroy()

    def OnRename(self, evt):
        # renaming is not applicable if inputs are not path
        if not get_config()["input_as_path"]:
            return
            
        Qview_fullpath = get_config()["show_fullpath"]
        Qhide_extension = get_config()["hide_extension"]
        Qrename_choice = get_config()["rename_choice"]

        rename.history.clear()
        old_pathes = []
        positions = []
        preview_pathes = []
        row_id = -1
        while True:  # loop all the checked items
            row_id = self.list_ctrl.GetNextItem(row_id)
            if row_id == -1:
                break
            if self.list_ctrl.IsItemChecked(row_id):
                pos = self.list_ctrl.GetItemData(row_id)  # 0-based unsorted index
                if Qrename_choice:
                    old_pathes.append(self.list_ctrl.listdata[pos][config.D_MATCHNAME])
                else:
                    old_pathes.append(self.list_ctrl.listdata[pos][config.D_FILENAME])
                preview_pathes.append(self.list_ctrl.listdata[pos][config.D_PREVIEW])
        renames = rename.get_renames(old_pathes, preview_pathes, simulate=(get_args().mode == "preview_rename"))

        row_id = -1
        count = 0
        errors = {}
        self.list_ctrl.Freeze()
        while True:  # loop all the checked items
            if len(renames) < count + 1:
                break
            row_id = self.list_ctrl.GetNextItem(row_id)
            if row_id == -1:
                break
            if self.list_ctrl.IsItemChecked(row_id):
                pos = self.list_ctrl.GetItemData(row_id)  # 0-based unsorted index
                if renames[count]:
                    Qfirst = True
                    for retcode, msg, h in zip(renames[count]["retcode"], renames[count]["msg"], renames[count]["history"]):
                        if retcode:
                            # add error
                            err = "Error : " + msg
                            if not pos in errors:
                                errors[pos] = [err]
                            else:
                                errors[pos].append(err)
                            if get_args().mode == "rename":
                                print(err)
                        else:
                            if Qfirst:
                                h["pos"] = pos
                                h["previous_data"] = copy.deepcopy(self.list_ctrl.listdata[pos])
                                Qfirst = False
                                previews = [y for p in self.list_ctrl.listdata[pos][config.D_PREVIEW] for y in p]
                                if Qrename_choice:
                                    self.list_ctrl.RefreshItem(
                                        row_id,
                                        matchnames=previews,
                                        score=100,
                                        status=config.MatchStatus.MATCH,
                                        Qview_fullpath=Qview_fullpath,
                                        Qhide_extension=Qhide_extension,
                                    )
                                else:
                                    self.list_ctrl.RefreshItem(
                                        row_id,
                                        filename_path=previews,
                                        score=100,
                                        status=config.MatchStatus.MATCH,
                                        Qview_fullpath=Qview_fullpath,
                                        Qhide_extension=Qhide_extension,
                                    )
                            else:
                                h["pos"] = pos
                                h["previous_data"] = None
                            rename.history.append(h)
                            wx.LogMessage(msg)
                            if get_args().mode == "rename" or get_args().mode == "preview_rename":
                                print(msg)
                else:
                    break
                count += 1
        self.list_ctrl.Thaw()

        # Log errors in bottom tab
        errorTabIdx = -1
        for idx in range(0, self.bottom_notebook.GetPageCount()):
            if self.bottom_notebook.GetPageText(idx) == "Errors":
                errorTabIdx = idx
                break

        if len(errors):
            if errorTabIdx != -1:
                self.bottom_notebook.SetSelection(errorTabIdx)
            else:
                self.tab_errors = bottom_notebook.TabListItemError(parent=self.bottom_notebook, mlist=self.list_ctrl)
                self.bottom_notebook.AddPage(self.tab_errors, "Errors", select=True)
                errorTabIdx = self.bottom_notebook.GetPageIndex(self.tab_errors)
                self.bottom_notebook.HidePage(errorTabIdx, hidden=False)
            self.tab_errors.SetItemsWithError(errors)
        else:
            if errorTabIdx != -1:
                self.bottom_notebook.DeletePage(errorTabIdx)

    def OnUndo(self, evt):
        Qview_fullpath = get_config()["show_fullpath"]
        Qhide_extension = get_config()["hide_extension"]

        undos = undo.get_undos()

        count = 0
        errors = {}
        self.list_ctrl.Freeze()
        for h in rename.history:
            if len(undos) < count + 1:
                break
            u = undos[count]
            if u:
                retcode = u["retcode"]
                pos = h["pos"]
                if retcode == 0:
                    if h["previous_data"]:
                        row_id = self.list_ctrl.FindItem(-1, pos)
                        if row_id != -1:
                            self.list_ctrl.listdata[pos] = h["previous_data"]
                            self.list_ctrl.RefreshItem(row_id, Qview_fullpath=Qview_fullpath, Qhide_extension=Qhide_extension)

                    for m in u["msg"]:
                        wx.LogMessage(m)
                else:
                    # add error
                    errors[pos] = u["msg"]
            else:
                break
            count += 1
        self.list_ctrl.Thaw()

        # Log errors in bottom tab
        errorTabIdx = -1
        for idx in range(0, self.bottom_notebook.GetPageCount()):
            if self.bottom_notebook.GetPageText(idx) == "Errors":
                errorTabIdx = idx
                break

        if len(errors):
            if errorTabIdx != -1:
                self.bottom_notebook.SetSelection(errorTabIdx)
            else:
                self.tab_errors = bottom_notebook.TabListItemError(parent=self.bottom_notebook, mlist=self.list_ctrl)
                self.bottom_notebook.AddPage(self.tab_errors, "Errors", select=True)
                errorTabIdx = self.bottom_notebook.GetPageIndex(self.tab_errors)
                self.bottom_notebook.HidePage(errorTabIdx, hidden=False)
            self.tab_errors.SetItemsWithError(errors)
        else:
            if errorTabIdx != -1:
                self.bottom_notebook.DeletePage(errorTabIdx)
        rename.history.clear()

    def OnLogDuplicate(self, evt):
        with wx.lib.busy.BusyInfo("Please wait...", wx.PyApp.GetMainTopWindow()):
            previews = [x[config.D_PREVIEW] for x in self.list_ctrl.listdata.values() if x[config.D_CHECKED]]
            # [[...], [...], ...] -> [...]
            all_previews = [
                p
                for previews_per_source in previews
                for previews_per_singlesource in previews_per_source
                for p in previews_per_singlesource
            ]
            Qinput_as_path = get_config()["input_as_path"]
            duplicates = defaultdict(list)
            for (key, source) in self.list_ctrl.listdata.items():
                all_previews_for_key = [
                    p for previews_per_singlesource in source[config.D_PREVIEW] for p in previews_per_singlesource
                ]
                if Qinput_as_path:
                    for v in all_previews_for_key:
                        if v and v.stem and all_previews.count(v) > 1:
                            duplicates[v].append(key)
                else:
                    for v in all_previews_for_key:
                        if v and all_previews.count(v) > 1:
                            duplicates[v].append(key)
            duplicates_key = [duplicates[sorted_key] for sorted_key in sorted(duplicates.keys())]
            a = []
            for d in duplicates_key:
                if not d in a:
                    a.append(d)
            duplicates_key = a

        duplicateTabIdx = -1
        for idx in range(0, self.bottom_notebook.GetPageCount()):
            if self.bottom_notebook.GetPageText(idx) == "Duplicates":
                duplicateTabIdx = idx
                break

        if len(duplicates_key):
            wx.LogMessage("Found %d duplicate(s)" % (len(duplicates_key)))
            if duplicateTabIdx != -1:
                self.bottom_notebook.SetSelection(duplicateTabIdx)
            else:
                self.tab_duplicates = bottom_notebook.TabDuplicates(parent=self.bottom_notebook, mlist=self.list_ctrl)
                self.bottom_notebook.AddPage(self.tab_duplicates, "Duplicates", select=True)
                duplicateTabIdx = self.bottom_notebook.GetPageIndex(self.tab_duplicates)
                self.bottom_notebook.HidePage(duplicateTabIdx, hidden=False)
            self.tab_duplicates.SetDuplicates(duplicates_key)
        else:
            wx.LogMessage("No duplicate found")
            if duplicateTabIdx != -1:
                self.bottom_notebook.DeletePage(duplicateTabIdx)

    def OnLogUnmatched(self, evt):
        with wx.lib.busy.BusyInfo("Please wait...", wx.PyApp.GetMainTopWindow()):
            all_matches = {
                match
                for source in self.list_ctrl.listdata.values()
                for match in source[config.D_MATCHNAME]
            }
        unmatched = sorted(set(glob_choices.keys()) - all_matches)

        TabIdx = -1
        for idx in range(0, self.bottom_notebook.GetPageCount()):
            if self.bottom_notebook.GetPageText(idx) == "Unmatched choices":
                TabIdx = idx
                break

        if len(unmatched):
            wx.LogMessage("Found %d unmatched choice(s)" % (len(unmatched)))
            if TabIdx != -1:
                self.bottom_notebook.SetSelection(TabIdx)
            else:
                self.tab_unmatched = bottom_notebook.TabUnmatched(parent=self.bottom_notebook)
                self.bottom_notebook.AddPage(self.tab_unmatched, "Unmatched choices", select=True)
                TabIdx = self.bottom_notebook.GetPageIndex(self.tab_unmatched)
                self.bottom_notebook.HidePage(TabIdx, hidden=False)
            self.tab_unmatched.SetUnmatched(unmatched)
        else:
            wx.LogMessage("No unmatched found")
            if TabIdx != -1:
                self.bottom_notebook.DeletePage(TabIdx)

    def OnLogMatched(self, evt):
        with wx.lib.busy.BusyInfo("Please wait...", wx.PyApp.GetMainTopWindow()):
            all_matches = {
                match
                for source in self.list_ctrl.listdata.values()
                for match in source[config.D_MATCHNAME]
            }
        matched = sorted(all_matches)

        TabIdx = -1
        for idx in range(0, self.bottom_notebook.GetPageCount()):
            if self.bottom_notebook.GetPageText(idx) == "Matched choices":
                TabIdx = idx
                break

        if len(matched):
            wx.LogMessage("Found %d matched choice(s)" % (len(matched)))
            if TabIdx != -1:
                self.bottom_notebook.SetSelection(TabIdx)
            else:
                self.tab_matched = bottom_notebook.TabMatched(parent=self.bottom_notebook)
                self.bottom_notebook.AddPage(self.tab_matched, "Matched choices", select=True)
                TabIdx = self.bottom_notebook.GetPageIndex(self.tab_matched)
                self.bottom_notebook.HidePage(TabIdx, hidden=False)
            self.tab_matched.SetMatched(matched)
        else:
            wx.LogMessage("No match found")
            if TabIdx != -1:
                self.bottom_notebook.DeletePage(TabIdx)


class aboutDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title="About PyFuzzy-renamer")
        html = wxHTML(self)

        html.SetPage(
            '<font size="30">PyFuzzy-renamer ' + __version__ + '</font><br><br>'
            '<u>Source</u> <a href ="https://github.com/pcjco/PyFuzzy-renamer">https://github.com/pcjco/PyFuzzy-renamer</a><br>'
            "<u>Authors</u><br>"
            "<ul><li>pcjco</li></ul>"
            "<u>Credits</u><br>"
            '<ul><li><a href ="https://wxpython.org">wxPython</a></li>'
            '<li><a href ="https://becrisdesign.com">Becris Design</a> (icons)</li>'
            '<li><a href ="https://www.waste.org/~winkles/fuzzyRename/">Fuzzy Rename</a> (original by jeff@silent.net)</li>'
            '<li><a href ="http://bitbucket.org/raz/wxautocompletectrl/">wxautocompletectrl</a> (by Toni Ruža &lt;toni.ruza@gmail.com&gt;)</li></ul>'
            "<u>License</u><br>"
            "<ul><li>MIT License</li>"
            "<li>Copyright (c) 2020 pcjco</li></ul>"
        )

        btns = self.CreateButtonSizer(wx.CLOSE)

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(html, 1, wx.ALL | wx.EXPAND, 0)
        mainSizer.Add(btns, 0, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(mainSizer)
        self.Fit()


class wxHTML(wx.html.HtmlWindow):
    def __init__(self, parent):
        wx.html.HtmlWindow.__init__(self, parent, size=(400, 300))

    def OnLinkClicked(self, link):
        wx.LaunchDefaultBrowser(link.GetHref())


class helpDialog(wx.Dialog):
    def __init__(self, parent, label):
        wx.Dialog.__init__(
            self, parent, title=label, size=(600, 300), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )

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


class MainFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(
            self,
            None,
            name="mainFrame",
            title="PyFuzzy-renamer " + __version__,
            pos=wx.Point(-10, 0),
            size=wx.Size(1000, 800),
        )
        freeze_support()

        bundle = wx.IconBundle()
        bundle.AddIcon(wx.Icon(icons.Rename_16_PNG.GetBitmap()))
        bundle.AddIcon(wx.Icon(icons.Rename_32_PNG.GetBitmap()))
        self.SetIcons(bundle)

        self.help = None
        self.statusbar = self.CreateStatusBar(2)

        menubar = wx.MenuBar()
        self.files = wx.Menu()
        view = wx.Menu()
        options = wx.Menu()
        help = wx.Menu()

        self.sources = wx.Menu()
        sources_ = wx.MenuItem(self.files, wx.ID_ANY, "&Sources", "Select sources (to rename)")
        sources_.SetSubMenu(self.sources)

        mnu_source_from_dir = wx.MenuItem(
            self.sources, wx.ID_ANY, "Sources from &Directory...\tCtrl+D", "Select sources from directory",
        )
        mnu_source_from_dir.SetBitmap(icons.AddFolder_16_PNG.GetBitmap())
        self.sources.Append(mnu_source_from_dir)

        mnu_source_from_clipboard = wx.MenuItem(
            self.sources, wx.ID_ANY, "Sources from &Clipboard", "Select sources from clipboard",
        )
        mnu_source_from_clipboard.SetBitmap(icons.Clipboard_16_PNG.GetBitmap())
        self.sources.Append(mnu_source_from_clipboard)

        self.mnu_source_from_clipboard_default = self.sources.AppendCheckItem(wx.ID_ANY, "Default Target for Drag && Drop and Pasting")
        
        mnu_source_clear = wx.MenuItem(
            self.sources, wx.ID_ANY, "Clear &All", "Clear All",
        )
        mnu_source_clear.SetBitmap(icons.Trash_16_PNG.GetBitmap())
        self.sources.Append(mnu_source_clear)
 
        self.mnu_recents_sources = []
        if get_config()["recent_sources"]:
            self.sources.AppendSeparator()
            for i in range(0, len(get_config()["recent_sources"])):
                new_mnu_recent_source = wx.MenuItem(
                    self.sources,
                    wx.ID_ANY,
                    "&" + str(i + 1) + ": " + utils.shorten_path(get_config()["recent_sources"][i], 64),
                    "",
                )
                self.sources.Append(new_mnu_recent_source)
                self.mnu_recents_sources.append(new_mnu_recent_source)
        
        self.choices = wx.Menu()
        choices_ = wx.MenuItem(self.files, wx.ID_ANY, "&Choices", "Select choices (to match)")
        choices_.SetSubMenu(self.choices)

        mnu_choices_from_dir = wx.MenuItem(
            self.choices, wx.ID_ANY, "Choices from &Directory...\tCtrl+T", "Select choices from directory",
        )
        mnu_choices_from_dir.SetBitmap(icons.AddFolder_16_PNG.GetBitmap())
        self.choices.Append(mnu_choices_from_dir)

        mnu_choices_from_clipboard = wx.MenuItem(
            self.choices, wx.ID_ANY, "Choices from &Clipboard", "Select choices from clipboard",
        )
        mnu_choices_from_clipboard.SetBitmap(icons.Clipboard_16_PNG.GetBitmap())
        self.choices.Append(mnu_choices_from_clipboard)
 
        mnu_choices_from_file = wx.MenuItem(
            self.choices, wx.ID_ANY, "Choices from &File", "Import choices from a file",
        )
        mnu_choices_from_file.SetBitmap(icons.Spreadsheet_16_PNG.GetBitmap())
        self.choices.Append(mnu_choices_from_file)

        self.mnu_choices_from_clipboard_default = self.choices.AppendCheckItem(wx.ID_ANY, "Default Target for Drag && Drop and Pasting")

        mnu_choices_clear = wx.MenuItem(
            self.choices, wx.ID_ANY, "Clear &All", "Clear All",
        )
        mnu_choices_clear.SetBitmap(icons.Trash_16_PNG.GetBitmap())
        self.choices.Append(mnu_choices_clear)

        self.mnu_recents_choices = []
        if get_config()["recent_choices"]:
            self.choices.AppendSeparator()
            for i in range(0, len(get_config()["recent_choices"])):
                new_mnu_recent_choice = wx.MenuItem(
                    self.choices,
                    wx.ID_ANY,
                    "&" + str(i + 1) + ": " + utils.shorten_path(get_config()["recent_choices"][i], 64),
                    "",
                )
                self.choices.Append(new_mnu_recent_choice)
                self.mnu_recents_choices.append(new_mnu_recent_choice)

        mnu_swap = wx.MenuItem(self.files, wx.ID_ANY, "Sources \u2194 Choices\tCtrl+W", "Swap sources and choices")
        mnu_swap.SetBitmap(icons.Swap_16_PNG.GetBitmap())
        
        output_dir = wx.Menu()
        output_dir_ = wx.MenuItem(self.files, wx.ID_ANY, "&Output Directory", "Select output directory")
        output_dir_.SetBitmap(icons.Folder_16_PNG.GetBitmap())
        output_dir_.SetSubMenu(output_dir)

        self.mnu_same_as_input = output_dir.AppendCheckItem(wx.ID_ANY, "&Same as source", "Same as source")
        self.mnu_user_dir = output_dir.AppendCheckItem(
            wx.ID_ANY, "&User-defined directory...", "Select User-defined directory"
        )

        mnu_listmatched = wx.MenuItem(self.files, wx.ID_ANY, "&List matched choices", "List choices matching a source")
        mnu_listunmatched = wx.MenuItem(self.files, wx.ID_ANY, "&List unmatched choices", "List choices not matching any source")

        mnu_open = wx.MenuItem(self.files, wx.ID_ANY, "&Load Session...\tCtrl+O", "Open...")
        mnu_open.SetBitmap(icons.Open_16_PNG.GetBitmap())

        mnu_save = wx.MenuItem(self.files, wx.ID_ANY, "&Save Session\tCtrl+S", "Save...")
        mnu_save.SetBitmap(icons.Save_16_PNG.GetBitmap())

        self.mnu_quit = wx.MenuItem(self.files, wx.ID_ANY, "&Exit\tAlt+F4", "Exit the Application")
        self.mnu_quit.SetBitmap(icons.Quit_16_PNG.GetBitmap())

        self.files.Append(sources_)
        self.files.Append(choices_)
        self.files.Append(output_dir_)
        self.files.Append(mnu_swap)
        self.files.Append(mnu_listmatched)
        self.files.Append(mnu_listunmatched)
        self.files.AppendSeparator()
        self.files.Append(mnu_open)
        self.files.Append(mnu_save)
        self.files.AppendSeparator()
        self.mnu_recents = []
        if get_config()["recent_session"]:
            for i in range(0, len(get_config()["recent_session"])):
                new_mnu_recent = wx.MenuItem(
                    self.files,
                    wx.ID_ANY,
                    "&" + str(i + 1) + ": " + utils.shorten_path(get_config()["recent_session"][i], 64),
                    "",
                )
                self.files.Append(new_mnu_recent)
                self.mnu_recents.append(new_mnu_recent)
            self.files.AppendSeparator()
        self.files.Append(self.mnu_quit)

        self.mnu_view_fullpath = view.AppendCheckItem(wx.ID_ANY, "&View full path", "View full path")
        self.mnu_hide_extension = view.AppendCheckItem(wx.ID_ANY, "&Hide suffix", "Hide suffix")
        self.mnu_view_bottom = view.AppendCheckItem(wx.ID_ANY, "View Output &Pane", "View Output Pane")
        self.mnu_show_log = view.AppendCheckItem(wx.ID_ANY, "&Show log", "Show log")

        # Input type
        input_type_menu = wx.Menu()
        input_type_menu_ = wx.MenuItem(
            options,
            wx.ID_ANY,
            "&Type of inputs",
            "Select the type of inputs",
        )
        self.mnu_types = []
        input_type_menu_.SetSubMenu(input_type_menu)
        new_mnu_type_file = input_type_menu.AppendRadioItem(wx.ID_ANY, "&1    Files", "")
        new_mnu_type_string = input_type_menu.AppendRadioItem(wx.ID_ANY, "&2    Strings", "")
        self.mnu_types.append(new_mnu_type_file)
        self.mnu_types.append(new_mnu_type_string)
        options.Append(input_type_menu_)
        self.mnu_types[0 if get_config()["input_as_path"] else 1].Check(True)

        self.mnu_rename_choice = options.AppendCheckItem(wx.ID_ANY, "&Rename choice instead of source", "Rename choice instead of source")
        self.mnu_keep_original = options.AppendCheckItem(wx.ID_ANY, "Keep &original on renaming", "Keep original on renaming")
        self.mnu_best_auto = options.AppendCheckItem(wx.ID_ANY, "Automatically find &best match", "Automatically find best match")
        self.mnu_keep_match_ext = options.AppendCheckItem(wx.ID_ANY, "&Keep matched file suffix", "Keep matched file suffix")
        self.mnu_match_firstletter = options.AppendCheckItem(
            wx.ID_ANY, "&Always match first letter", "Enforce choices that match the first letter of the source",
        )
        self.mnu_source_w_multiple_choice = options.AppendCheckItem(
            wx.ID_ANY, "Source can match &multiple choices", "Source can match multiple choices"
        )

        # Number of parallel workers
        workers = wx.Menu()
        workers_ = wx.MenuItem(
            options,
            wx.ID_ANY,
            "&Number of processes",
            "Select the number of parallel processes used during matching/renaming/undoing tasks",
        )
        self.mnu_procs = []
        workers_.SetSubMenu(workers)
        for i in range(2 * cpu_count()):
            new_mnu_proc = workers.AppendRadioItem(
                wx.ID_ANY,
                "&"
                + str(i + 1)
                + ("    (CPU count)" if i + 1 == cpu_count() else "")
                + ("    (no multiprocessing)" if i == 0 else ""),
                "",
            )
            self.mnu_procs.append(new_mnu_proc)
        options.Append(workers_)
        if get_config()["workers"] <= len(self.mnu_procs) and get_config()["workers"] > 0:
            self.mnu_procs[get_config()["workers"] - 1].Check(True)

        # Similarity Engine
        similarityscorers = wx.Menu()
        similarityscorers_ = wx.MenuItem(
            options,
            wx.ID_ANY,
            "&Similarity scorer",
            "Select the similarity algorithm used in matching process",
        )
        self.mnu_scorers = []
        similarityscorers_.SetSubMenu(similarityscorers)
        for i in range(7):
            new_mnu_scorer = similarityscorers.AppendRadioItem(
                wx.ID_ANY,
                "&"
                + str(i + 1) + "    "
                + (str(config.SimilarityScorer(i))),
                "",
            )
            self.mnu_scorers.append(new_mnu_scorer)
        options.Append(similarityscorers_)
        if get_config()["similarityscorer"] <= len(self.mnu_scorers) and get_config()["similarityscorer"] > 0:
            self.mnu_scorers[get_config()["similarityscorer"]].Check(True)

        mnu_doc = wx.MenuItem(help, wx.ID_ANY, "&Help...", "Help")
        mnu_doc.SetBitmap(icons.Help_16_PNG.GetBitmap())
        help.Append(mnu_doc)
        mnu_about = wx.MenuItem(help, wx.ID_ANY, "&About...", "About the application")
        mnu_about.SetBitmap(icons.Info_16_PNG.GetBitmap())
        help.Append(mnu_about)

        menubar.Append(self.files, "&File")
        menubar.Append(view, "&View")
        menubar.Append(options, "&Options")
        menubar.Append(help, "&Help")
        self.SetMenuBar(menubar)

        self.mnu_choices_from_clipboard_default.Check(get_config()["paste_forced"] == 2)
        self.mnu_source_from_clipboard_default.Check(get_config()["paste_forced"] == 1)

        if get_config()["folder_output"]:
            self.mnu_user_dir.Check(True)
        else:
            self.mnu_same_as_input.Check(True)

        self.mnu_view_bottom.Check(get_config()["view_bottom"])
        self.mnu_show_log.Check(get_config()["show_log"])

        self.mnu_view_fullpath.Check(get_config()["show_fullpath"])
        self.mnu_hide_extension.Check(get_config()["hide_extension"])
        self.mnu_hide_extension.Enable(not get_config()["show_fullpath"])
        self.mnu_rename_choice.Check(get_config()["rename_choice"])
        self.mnu_keep_original.Check(get_config()["keep_original"])
        self.mnu_best_auto.Check(get_config()["best_auto"])
        self.mnu_keep_match_ext.Check(get_config()["keep_match_ext"])
        self.mnu_match_firstletter.Check(get_config()["match_firstletter"])
        self.mnu_source_w_multiple_choice.Check(get_config()["source_w_multiple_choice"])

        # Add a panel so it looks the correct on all platforms
        self.panel = MainPanel(self)

        # Show/Hide the bottom pane according to config
        self.panel.ToggleBottom()

        # Show/Hide the log according to config
        self.panel.bottom_notebook.ToggleLog()

        # Persistent window config
        self.persistMgr = PM.PersistenceManager.Get()
        self.persistMgr.SetConfigurationHandler(config.get_persistent_config())
        self.persistMgr.Register(self)
        self.persistMgr.Register(self.panel)
        self.persistMgr.Restore(self)
        self.persistMgr.Restore(self.panel)

        self.Bind(wx.EVT_MENU, self.panel.OnAddSourcesFromDir, mnu_source_from_dir)
        self.Bind(wx.EVT_MENU, self.panel.OnAddSourcesFromClipboard, mnu_source_from_clipboard)
        self.Bind(wx.EVT_MENU, self.panel.OnAddChoicesFromDir, mnu_choices_from_dir)
        self.Bind(wx.EVT_MENU, self.panel.OnImportChoicesFromFile, mnu_choices_from_file)
        self.Bind(
            wx.EVT_MENU, self.panel.OnAddChoicesFromClipboard, mnu_choices_from_clipboard,
        )
        self.Bind(wx.EVT_MENU, self.panel.OnClearSource, mnu_source_clear)
        self.Bind(wx.EVT_MENU, self.panel.OnClearChoices, mnu_choices_clear)
        self.Bind(wx.EVT_MENU, self.panel.OnSwap, mnu_swap)
        self.Bind(wx.EVT_MENU, self.panel.OnLogUnmatched, mnu_listunmatched)
        self.Bind(wx.EVT_MENU, self.panel.OnLogMatched, mnu_listmatched)
        self.Bind(wx.EVT_MENU, self.panel.OnOutputDirectory, self.mnu_user_dir)
        self.Bind(wx.EVT_MENU, self.panel.OnSameOutputDirectory, self.mnu_same_as_input)
        self.Bind(wx.EVT_MENU, self.panel.OnToggleBottom, self.mnu_view_bottom)
        self.Bind(wx.EVT_MENU, self.panel.OnToggleLog, self.mnu_show_log)
        self.Bind(wx.EVT_MENU, self.panel.OnViewFullPath, self.mnu_view_fullpath)
        self.Bind(wx.EVT_MENU, self.panel.OnHideExtension, self.mnu_hide_extension)
        self.Bind(wx.EVT_MENU, self.panel.OnKeepMatchExtension, self.mnu_keep_match_ext)
        self.Bind(wx.EVT_MENU, self.panel.OnMatchFirstLetter, self.mnu_match_firstletter)
        self.Bind(wx.EVT_MENU, self.panel.OnSourceWMultipleChoice, self.mnu_source_w_multiple_choice)
        self.Bind(wx.EVT_MENU, self.panel.OnKeepOriginal, self.mnu_keep_original)
        self.Bind(wx.EVT_MENU, self.panel.OnFindBestAuto, self.mnu_best_auto)
        self.Bind(wx.EVT_MENU, self.panel.OnRenameChoice, self.mnu_rename_choice)
        self.Bind(wx.EVT_MENU, self.panel.OnDefaultPasteChoices, self.mnu_choices_from_clipboard_default)
        self.Bind(wx.EVT_MENU, self.panel.OnDefaultPasteSource, self.mnu_source_from_clipboard_default)
        self.Bind(wx.EVT_MENU, self.OnOpen, mnu_open)
        self.Bind(wx.EVT_MENU, self.OnSaveAs, mnu_save)
        self.Bind(wx.EVT_MENU, self.OnQuit, self.mnu_quit)
        self.Bind(wx.EVT_MENU, self.OnHelp, mnu_doc)
        self.Bind(wx.EVT_MENU, self.OnAbout, mnu_about)
        self.Bind(wx.EVT_CLOSE, self.OnQuit)

        for mnu_recent in self.mnu_recents:
            self.Bind(wx.EVT_MENU, self.OnOpenRecent, mnu_recent)
        for mnu_recent in self.mnu_recents_sources:
            self.Bind(wx.EVT_MENU, self.OnAddRecentSource, mnu_recent)
        for mnu_recent in self.mnu_recents_choices:
            self.Bind(wx.EVT_MENU, self.OnAddRecentChoice, mnu_recent)
        for mnu_proc in self.mnu_procs:
            self.Bind(wx.EVT_MENU, self.OnNumProc, mnu_proc)
        for mnu_scorer in self.mnu_scorers:
            self.Bind(wx.EVT_MENU, self.OnSimilarityScorer, mnu_scorer)
        for mnu_type_input in self.mnu_types:
            self.Bind(wx.EVT_MENU, self.OnChangeInputType, mnu_type_input)

        # arguments
        if get_args().sources:
            self.panel.AddSourcesFromDir(get_args().sources)
        if get_args().choices:
            self.panel.AddChoicesFromDir(get_args().choices)

        if not get_args().mode:
            self.Show(True)
        else:
            if get_args().mode == "rename" or get_args().mode == "preview_rename":
                self.panel.OnRun(None)
                self.panel.OnRename(None)
            elif get_args().mode == "report_match":
                self.panel.OnRun(None)

    def OnAbout(self, event):
        dia = aboutDialog(None)
        dia.ShowModal()
        dia.Destroy()

    def OnHelp(self, event):
        self.help = helpDialog(None, "Help")
        self.help.Show()

    def OnQuit(self, event):
        self.SaveUI()
        if self.help:
            self.help.Destroy()
        self.panel.mgr.UnInit()
        self.Destroy()

    def OnSaveAs(self, event):
        with wx.FileDialog(
            self, "Save file", wildcard="SAVE files (*.sav)|*.sav", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            # save the current contents in the file
            self.SaveSession(fileDialog.GetPath())

    def OnNumProc(self, event):
        menu = event.GetEventObject()
        menuItem = menu.FindItemById(event.GetId())
        get_config()["workers"] = self.mnu_procs.index(menuItem) + 1

    def OnSimilarityScorer(self, event):
        menu = event.GetEventObject()
        menuItem = menu.FindItemById(event.GetId())
        get_config()["similarityscorer"] = self.mnu_scorers.index(menuItem)

    def OnChangeInputType(self, event):
        menu = event.GetEventObject()
        menuItem = menu.FindItemById(event.GetId())

        get_config()["input_as_path"] = (self.mnu_types.index(menuItem) == 0)

        # Update Menus
        self.panel.UpdateButtons()
        
        # Update Inputs
        sources = []
        row_id = -1
        while True:
            row_id = self.panel.list_ctrl.GetNextItem(row_id)
            if row_id == -1:
                break
            pos = self.panel.list_ctrl.GetItemData(row_id)  # 0-based unsorted index
            sources += self.panel.list_ctrl.listdata[pos][config.D_FILENAME]
        choices = [str(key) for key in glob_choices]
        self.panel.OnReset(None)
        self.panel.AddSourcesFromFiles(sources)
        self.panel.AddChoicesFromFiles(choices)

    def OnOpenRecent(self, event):
        menu = event.GetEventObject()
        menuItem = menu.FindItemById(event.GetId())
        pathname = get_config()["recent_session"][self.mnu_recents.index(menuItem)]
        self.LoadSession(pathname)

    def OnOpen(self, event):
        with wx.FileDialog(
            self, "Open SAVE file", wildcard="SAVE files (*.sav)|*.sav", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            # Proceed loading the file chosen by the user
            self.LoadSession(fileDialog.GetPath())

    def UpdateRecentSession(self, pathname):
        if pathname in get_config()["recent_session"]:
            idx = get_config()["recent_session"].index(pathname)
            if idx:
                get_config()["recent_session"].insert(0, get_config()["recent_session"].pop(idx))
        else:
            get_config()["recent_session"].insert(0, pathname)
            get_config()["recent_session"] = get_config()["recent_session"][:8]

        # update file menu
        # - Remove all recent
        found_recent = False
        for mnu_recent in self.mnu_recents:
            found_recent = True
            self.files.Delete(mnu_recent)
        if not found_recent:
            item, pos = self.files.FindChildItem(self.mnu_quit.GetId())  # Search Exit button
            self.files.InsertSeparator(pos)

        # - Refresh recents
        self.mnu_recents.clear()
        for i in range(0, len(get_config()["recent_session"])):
            new_mnu_recent = wx.MenuItem(
                self.files, wx.ID_ANY, "&" + str(i + 1) + ": " + utils.shorten_path(get_config()["recent_session"][i], 64), "",
            )
            item, pos = self.files.FindChildItem(self.mnu_quit.GetId())  # Search Exit button
            self.files.Insert(pos - 1, new_mnu_recent)
            self.mnu_recents.append(new_mnu_recent)
            self.Bind(wx.EVT_MENU, self.OnOpenRecent, new_mnu_recent)

    def OnAddRecentSource(self, event):
        menu = event.GetEventObject()
        menuItem = menu.FindItemById(event.GetId())
        pathname = get_config()["recent_sources"][self.mnu_recents_sources.index(menuItem)]
        self.panel.AddSourcesFromDir(pathname)

    def UpdateRecentSources(self, pathname):
        if pathname in get_config()["recent_sources"]:
            idx = get_config()["recent_sources"].index(pathname)
            if idx:
                get_config()["recent_sources"].insert(0, get_config()["recent_sources"].pop(idx))
        else:
            get_config()["recent_sources"].insert(0, pathname)
            get_config()["recent_sources"] = get_config()["recent_sources"][:8]

        # update sources menu
        # - Remove all recent
        found_recent = False
        for mnu_recent in self.mnu_recents_sources:
            found_recent = True
            self.sources.Delete(mnu_recent)
        if not found_recent:
            self.sources.AppendSeparator()

        # - Refresh recents
        self.mnu_recents_sources.clear()
        for i in range(0, len(get_config()["recent_sources"])):
            new_mnu_recent = wx.MenuItem(
                self.sources, wx.ID_ANY, "&" + str(i + 1) + ": " + utils.shorten_path(get_config()["recent_sources"][i], 64), "",
            )
            self.sources.Append(new_mnu_recent)
            self.mnu_recents_sources.append(new_mnu_recent)
            self.Bind(wx.EVT_MENU, self.OnAddRecentSource, new_mnu_recent)

    def OnAddRecentChoice(self, event):
        menu = event.GetEventObject()
        menuItem = menu.FindItemById(event.GetId())
        pathname = get_config()["recent_choices"][self.mnu_recents_choices.index(menuItem)]
        p = Path(pathname)
        try:
            if p.is_dir():
                self.panel.AddChoicesFromDir(pathname)
            elif p.is_file():
                self.panel.ImportChoicesFromFile(pathname)
        except (OSError, IOError):
            pass

    def UpdateRecentChoices(self, pathname):
        if pathname in get_config()["recent_choices"]:
            idx = get_config()["recent_choices"].index(pathname)
            if idx:
                get_config()["recent_choices"].insert(0, get_config()["recent_choices"].pop(idx))
        else:
            get_config()["recent_choices"].insert(0, pathname)
            get_config()["recent_choices"] = get_config()["recent_choices"][:8]

        # update choices menu
        # - Remove all recent
        found_recent = False
        for mnu_recent in self.mnu_recents_choices:
            found_recent = True
            self.choices.Delete(mnu_recent)
        if not found_recent:
            self.choices.AppendSeparator()

        # - Refresh recents
        self.mnu_recents_choices.clear()
        for i in range(0, len(get_config()["recent_choices"])):
            new_mnu_recent = wx.MenuItem(
                self.choices, wx.ID_ANY, "&" + str(i + 1) + ": " + utils.shorten_path(get_config()["recent_choices"][i], 64), "",
            )
            self.choices.Append(new_mnu_recent)
            self.mnu_recents_choices.append(new_mnu_recent)
            self.Bind(wx.EVT_MENU, self.OnAddRecentChoice, new_mnu_recent)

    def SaveSession(self, pathname):
        try:
            with open(pathname, "wb") as file:
                pickle.dump(
                    {
                        "version": __version__,
                        "glob_choices": glob_choices,
                        "aliases": aliases,
                        "listdata": self.panel.list_ctrl.listdata,
                        "listdataname": self.panel.list_ctrl.listdataname,
                        "listdatanameinv": self.panel.list_ctrl.listdatanameinv,
                        "input_as_path": get_config()["input_as_path"],
                    },
                    file,
                )

            self.UpdateRecentSession(pathname)

        except IOError:
            wx.LogError("Cannot save current data in file '%s'." % pathname)

    def LoadSession(self, pathname):
        global glob_choices, aliases

        self.UpdateRecentSession(pathname)
        list = self.panel.list_ctrl
        need_refresh_button = False
        try:
            with open(pathname, "rb") as file:
                data = pickle.load(file)
                glob_choices = data["glob_choices"]
                list.listdata = data["listdata"]
                list.listdataname = data["listdataname"]
                list.listdatanameinv = data["listdatanameinv"]
                if utils.versiontuple(data["version"]) >= utils.versiontuple("0.2.2"):
                    aliases = data["aliases"]
                if utils.versiontuple(data["version"]) <= utils.versiontuple("0.2.3"):
                    # forcing setting to only choice known until 0.2.3 
                    if not get_config()["input_as_path"]:
                        get_config()["input_as_path"] = True
                        need_refresh_button = True
                else:
                    input_as_path = data["input_as_path"]
                    if input_as_path != get_config()["input_as_path"]:
                        get_config()["input_as_path"] = input_as_path
                        need_refresh_button = True
                    
        except IOError:
            wx.LogError("Cannot open file '%s'." % pathname)

        RefreshCandidates()
        list.DeleteAllItems()
        
        if need_refresh_button:
            self.panel.UpdateButtons()
            
        row_id = 0
        Qview_fullpath = get_config()["show_fullpath"]
        Qhide_extension = get_config()["hide_extension"]
        with wx.lib.busy.BusyInfo("Please wait...", wx.PyApp.GetMainTopWindow()):
            list.Freeze()
            for key, data in list.listdata.items():
                list.InsertItem(row_id, "", -1)
                list.SetItemData(row_id, key)
                list.RefreshItem(row_id, Qview_fullpath=Qview_fullpath, Qhide_extension=Qhide_extension)
                list.CheckItem(row_id, data[config.D_CHECKED])
                if not data[config.D_CHECKED]:
                    f = list.GetItemFont(row_id)
                    if not f.IsOk():
                        f = list.GetFont()
                    font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
                    font.SetStyle(wx.FONTSTYLE_ITALIC)
                    font.SetWeight(f.GetWeight())
                    list.SetItemFont(row_id, font)
                if data[config.D_STATUS] == config.MatchStatus.USRMATCH:
                    f = list.GetItemFont(row_id)
                    if not f.IsOk():
                        f = list.GetFont()
                    font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
                    font.SetWeight(wx.FONTWEIGHT_BOLD)
                    font.SetStyle(f.GetStyle())
                    list.SetItemFont(row_id, font)
                row_id += 1
            list.Thaw()
        list.itemDataMap = list.listdata

    def SaveUI(self):
        self.persistMgr.SaveAndUnregister()
        list = self.panel.list_ctrl
        for col in range(0, len(config.default_columns)):
            get_config()["col%d_order" % (col + 1)] = list.GetColumnOrder(col) if list.HasColumnOrderSupport() else col
            get_config()["col%d_size" % (col + 1)] = list.GetColumnWidth(col)


def getDoc():
    return (
        "<p>This application uses a list of input strings and will rename each one with the most similar string from another list of strings.<p>"
        "<h3>Terminology</h3>"
        "The following terminology is used in the application, and in this document:"
        "<ul>"
        "<li>The input strings to rename are called the <b>sources</b>;</li>"
        "<li>The strings used to search for similarity are called the <b>choices</b>;</li>"
        "<li>A <b>choice alias</b> is an alternative name that can be assigned to a <b>choice</b>. It is an optional string that will be used instead of the original <b>choice</b> when renaming a <b>source</b>;</b></li>"
        "<li>The process to search the most similar <b>choice</b> for a given <b>source</b> is referred here as <b>matching</b> process;</li>"
        "<li>When strings are coming from file paths, the following terminology is used:"
        "<ul>"
        "<li>A <b>file path</b> is composed of a <b>parent directory</b> and a <b>file name</b>;<br>for example, <b>file path</b>=<code>c:/foo/bar/setup.tar.gz</code>, <b>parent directory</b>=<code>c:/foo/bar</code>, <b>file name</b>=<code>setup.tar.gz</code></li>"
        "<li>A <b>file name</b> is composed of a <b>stem</b> and a <b>suffix</b>;<br>"
        "for example, <b>file name</b>=<code>setup.tar</code>, <b>stem</b>=<code>setup</code>, <b>suffix</b>=<code>.tar</code><br>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>file name</b>=<code>setup.tar.gz</code>, <b>stem</b>=<code>setup.tar</code>, <b>suffix</b>=<code>.gz</code></li>"
        "<li>A <b>suffix</b> can only contain alphanumeric characters after the dot, if it contains non-alphanumeric characters, the suffix is considered as part of the <b>stem</b>;<br>for example, <b>file name</b>=<code>A.Train III</code>, <b>stem</b>=<code>A.Train III</code>, <b>suffix</b>=<code>None</code></li>"
        "</ul></li>"
        "</ul>"
        "<h3>Principles</h3>"
        "<p>Here is the process applied to match and rename each <b>source</b>:</p>"
        "<pre>"
        ' <font color="red">Choices</font>────┐<br>'
        "            │<br>"
        "        ┌───┴────┐                     ┌────────┐<br>"
        ' <font color="blue">Source</font>─┤Matching├─<font color="red">Most Similar Choice</font>─┤Renaming├─<font color="red">Renamed</font> <font color="blue">Source</font><br>'
        "        └────────┘                     └────────┘"
        "</pre>"
        "<p>When searching for the most similar <b>choice</b>, only the <b>stems</b> of <b>choices</b> and <b>stem</b> of <b>source</b> are compared.</p>"
        "<p>When renaming a <b>source</b> file path, only the <b>stem</b> is renamed with the most similar <b>stem</b> among <b>choices</b> file paths.</p>"
        '<p>For example, if <b>source</b> is <code><font color="blue">c:/foo/Amaryllis.png</font></code>, and <b>most similar choice</b> is <code><font color="red">d:/bar/Amaryllidinae.jpg</font></code>, <b>renamed source</b> is <code><font color="blue">c:/foo/</font><font color="red">Amaryllidinae</font><font color="blue">.png</font></code></p>'
        "<p>If <b>choices</b> have <b>choice aliases</b> assigned, then, the <b>choices</b> are used to search the most similar, but the <b>choice alias</b> of best <b>choice</b> is used for renaming.</p>"
        '<p>For example, if <b>source</b> is <code><font color="blue">Amaryllis</font></code>, and <b>most similar choice</b> is <code><font color="red">Amaryllidinae</font></code>, which has been assigned the <b>choice alias</b> <code><font color="orange">amary</font></code>, <b>renamed source</b> is <code><font color="orange">amary</font></code> and not <code><font color="red">Amaryllidinae</font></code></p>'
        "<p>If <b>masks</b> and <b>filters</b> are applied, the process applied to match and rename each <b>source</b> is the following:</p>"
        "<pre>"
        "        ┌───────┐               ┌─────────┐<br>"
        ' <font color="red">Choices</font>┤Masking├─<font color="red">Masked Choices</font>┤Filtering├──<font color="red">Masked&Filtered Choices</font>───┐<br>'
        "        └───────┘               └─────────┘                            │<br>"
        "        ┌───────┐               ┌─────────┐                        ┌───┴────┐                     ┌────────┐                       ┌─────────┐<br>"
        ' <font color="blue">Source</font>─┤Masking├─<font color="blue">Masked Source</font>─┤Filtering├─<font color="blue">Masked&Filtered Source</font>─┤Matching├─<font color="red">Most Similar Choice</font>─┤Renaming├─<font color="blue">Masked</font> <font color="red">Renamed</font> <font color="blue">Source</font>─┤Unmasking├─<font color="green">Unmasked</font> <font color="red">Renamed</font> <font color="blue">Source</font><br>'
        "        └───┬───┘               └─────────┘                        └────────┘                     └────────┘                       └────┬────┘<br>"
        "            │                                                                                                                           │<br>"
        '            └────────────────────────────────────────── <font color="green">Leading & Trailing Masks</font> ───────────────────────────────────────────────────────┘'
        "</pre>"
        "<h3>Sources</h3>"
        "<p>Sources are entered in the following ways:"
        "<ul><li>click on the <code><b>Sources</b></code> button to add a selection of file paths to the current <b>sources</b>;</li>"
        "<li>Go to <code><b>File->Sources->Sources from Directory</b></code> menu to add file paths from a selected folder to the current <b>sources</b>;</li>"
        "<li>Go to <code><b>File->Sources->Sources from Clipboard</b></code> menu to add file paths or folders from clipboard to the current <b>sources</b>. If clipboard contains a folder, then the file paths of the files inside this folder are added;</li>"
        "<li>Go to <code><b>File->Sources</b></code> to add recently selected folders to the current <b>sources</b>;</li>"
        "<li>Drag files or folders into application panel and choose <code><b>Sources</b></code> to add file paths to the current <b>sources</b>. For folders, the file paths of the files inside folders are added;</li>"
        "<li>Paste (Ctrl+V) into application panel and choose <code><b>Sources</b></code> to add file paths of the files or folders in clipboard to the current <b>sources</b>. For folders, the file paths of the files inside folders are added</li></ul>"
        "<h3>Choices</h3>"
        "<p>Choices are entered in the following ways:"
        "<ul><li>click on the <code><b>Choices</b></code> button to add a selection of files paths to the current <b>choices</b>;</li>"
        "<li>Go to <code><b>File->Choices->Choices from Directory</b></code> menu to add files paths from a selected folder to the current <b>choices</b>;</li>"
        "<li>Go to <code><b>File->Choices->Choices from Clipboard</b></code> menu to add files paths from clipboard to the current <b>choices</b>. If clipboard contains a folder, then the file paths of the files inside this folder are added;</li>"
        "<li>Go to <code><b>File->Choices->Choices from File</b></code> menu to import <b>choices</b> from a CSV (or XLSX, TXT) file."
        "<ul>"
        "<li>Each row or line of the file defined one <b>choice</b>;</li>"
        "<li>A <b>choice</b> containing space characters must be surrounded by double-quotes;</li>"
        "<li>If a line contains a single value, this value is the <b>choice</b>;</li>"
        "<li>If a line contains two values separated by a comma, the first value is the <b>choice</b> (=string used for comparison) and the second one is the <b>choice alias</b> (=string used for renaming);<br>"
        "for example, if a candidate to rename is <code>3DWorldRunner.png</code> and best <b>choice</b> is <code>3-D Battles of World Runner, The</code> but one wants to rename the file as <code>3dbatworru.png</code>, then the CSV should contain a line like <code>\"3-D Battles of World Runner, The\", 3dbatworru</code>;</li>"
        "<li>It is possible to define the text of the tooltip shown when hovering over a matched <b>choice</b>. Just include the specific text between /* */ in the <b>choice</b> name;<br>"
        "for example, if the choice name is <code>\"Choice Name/*Tooltip text line 1\nTooltip text line 2*/\"</code>, the tooltip will show the lines <code>\"Tooltip text line 1\"</code> and <code>\"Tooltip text line 2\"</code> when hovering over this matched choice.</li>"
        "</ul>"

        "<li>Go to <code><b>File->Choices</b></code> to add recently selected folders to the current <b>choices</b>;</li>"
        "<li>Drag files or folders into application panel and choose <code><b>Choices</b></code> to add file paths to the current <b>choices</b>. For folders, the file paths of the files inside folders are added;</li>"
        "<li>Paste (Ctrl+V) into application panel and choose <code><b>Choices</b></code> to add file paths of the files or folders in clipboard to the current <b>choices</b>. For folders, the file paths of the files inside folders are added</li></ul>"
        "<h3>Filters</h3>"
        "<p>To ease the <b>matching</b> process, filters can be applied to <b>sources</b> and <b>choices</b> before they are compared.</p>"
        '<p>For example, <b>source</b> is <code><font color="blue">c:/foo/The Amaryllis.png</font></code> and <b>choice</b> is <code><font color="red">d:/bar/Amaryllidinae, The.txt</font></code>. It would be smart to clean the <b>sources</b> and <b>choices</b> by ignoring all articles before trying to find the <b>most similar choice</b>.</p>'
        "<p>To achieve this, the application uses <b>filters</b>.</p>"
        "<p>The filters are using Python regular expression patterns with capture groups (). The captured groups are replaced by a given expression (usually empty to clean a string). This is applied to both <b>sources</b> and <b>choices</b> when <b>matching</b> occurs.</p>"
        "<p>Filters are only applied for the <b>matching</b> process, original unfiltered files are used otherwise.</p>"
        "<p>For example, to clean articles of <b>source</b> and <b>choice</b> file, a filter with the pattern <code>(^the\\b|, the)</code> with an empty replacement <code> </code> could be used:<br>"
        "<ol>"
        '<li><b>Filtering source</b>: <code><font color="blue">c:/foo/The Amaryllis.png</font></code> &rarr; <code><font color="blue">Amaryllis</font></code></li>'
        '<li><b>Filtering choice</b>: <code><font color="red">d:/bar/Amaryllidinae, The.txt</font></code> &rarr; <code><font color="red">Amaryllidinae</font></code></li>'
        '<li><b>Matching</b>: <code><font color="blue">The Amaryllis</font></code> &rarr; <code><font color="red">Amaryllidinae, The</font></code></li>'
        '<li><b>Renaming</b>: <code><font color="blue">c:/foo/The Amaryllis.png</font></code> &rarr; <code><font color="blue">c:/foo/</font><font color="red">Amaryllidinae, The</font><font color="blue">.png</font></code></li>'
        "</ol>"
        "<p>Filters creation, addition, deletion, re-ordering is available from <code><b>Masks &amp; Filters</b></code> button.</p>"
        "<ul>"
        "<li>Edition of the filter name, pattern and replace is done directly by clicking on the filter list cells</li>"
        "<li>Deletion of filters is done by pressing the [DELETE] key on some selected filter items or from the context menu on selected filter items.</li>"
        "<li>Addition of a filter is done from the context menu on filter list.</li>"
        "<li>Re-ordering a filter is done by dragging and dropping the filter item across the filter list.</li>"
        "</ul>"
        "<h3>Masks</h3>"
        "<p>Sometimes, it can be interesting to ignore some leading and/or trailing parts from <b>sources</b> or <b>choices</b> in the <b>matching</b> process and restore them after the <b>renaming</b> process.</p>"
        '<p>For example, <b>source</b> is <code><font color="blue">c:/foo/(1983-06-22) Amaryllis [Russia].png</font></code>, and we want to ignore the date <code><font color="blue">(1983-06-22)</font></code> and the country <code><font color="blue">[Russia]</font></code> during <b>matching</b> but we need to restore them when <b>renaming</b>, '
        ' then if <b>most similar choice</b> is <code><font color="red">d:/bar/Amaryllidinae.jpg</font></code>, the <b>renamed source</b> should be <code><font color="blue">c:/foo/(1983-06-22) </font><font color="red">Amaryllidinae</font><font color="blue"> [Russia].png</font></code></p>'
        "<p>To achieve this, the application uses <b>masks</b>.</p>"
        "<p>The masks are using Python regular expression patterns. They are removed from <b>sources</b> and <b>choices</b> strings before <b>filtering</b> and <b>matching</b> occur."
        "It is used to remove leading and trailing expressions (year, disk#...) before <b>matching</b> and restore them after <b>renaming</b>.</p>"
        "<p>For example, to preserve the Disk number at the end of a <b>source</b> file, a mask with the pattern <code>(\\s?disk\\d)$</code> could be used:<br>"
        "<ol>"
        '<li><b>Masking source</b>: <code><font color="blue">c:/foo/The Wiiire Disk1.rom</font></code> &rarr; <code><font color="blue">The Wiiire</font></code> + Trailing mask = <code><font color="green"> Disk1</font></code></li>'
        '<li><b>Matching</b>: <code><font color="blue">The Wiiire</font></code> &rarr; <code><font color="red">The Wire</font></code></li>'
        '<li><b>Renaming</b>: <code><font color="blue">c:/foo/The Wiiire.rom</font></code> &rarr; <code><font color="blue">c:/foo/</font><font color="red">The Wire</font><font color="blue">.rom</font></code></li>'
        '<li><b>Unmkasking</b>: <code><font color="blue">c:/foo/</font><font color="red">The Wire</font><font color="blue">.rom</font></code> &rarr; <code><font color="blue">c:/foo/</font><font color="red">The Wire</font> <font color="green">Disk1</font><font color="blue">.rom</font></code></li>'
        "</ol>"
        "<p>It is also used to match a single <b>source</b> with multiple <b>choices</b> and generate multiple renamed files.</p>"
        "<p>For example, masking the pattern <font face=\"verdana\">'(\\s?disk\\d)$'</font>:<br>"
        "<ol>"
        '<li><b>Masking choices</b>: <code><font color="red">The Wire Disk1</font></code>, <code><font color="red">The Wire Disk2</font></code> &rarr; <code><font color="red">The Wire</font></code> + Trailing masks = <code><font color="green">[Disk1, Disk2]</font></code></li>'
        '<li><b>Matching</b>: <code><font color="blue">The Wiiire</font></code> &rarr; <code><font color="red">The Wire</font></code></li>'
        '<li><b>Renaming</b>: <code><font color="blue">c:/foo/The Wiiire.rom</font></code> &rarr; <code><font color="blue">c:/foo/</font><font color="red">The Wire</font><font color="blue">.rom</font></code></li>'
        '<li><b>Unmkasking</b>: <code><font color="blue">c:/foo/</font><font color="red">The Wire</font><font color="blue">.rom</font></code> &rarr; <code><font color="blue">c:/foo/</font><font color="red">The Wire</font> <font color="green">Disk1</font><font color="blue">.rom</font></code>, <code><font color="blue">c:/foo/</font><font color="red">The Wire</font> <font color="green">Disk2</font><font color="blue">.rom</font></code></li>'
        "</ol>"
        "<p>Masks creation, addition, deletion, re-ordering is available from <code><b>Masks &amp; Filters</b></code> button.</p>"
        "<ul>"
        "<li>Edition of the mask name and pattern is done directly by clicking on the mask list cells</li>"
        "<li>Deletion of masks is done by pressing the [DELETE] key on some selected mask items or from the context menu on selected mask items.</li>"
        "<li>Addition of a mask is done from the context menu on mask list.</li>"
        "<li>Re-ordering a mask is done by dragging and dropping the mask item across the mask list.</li>"
        "</ul>"
        "<h3>Output directory</h3>"
        "<p>When <b>source</b> strings are coming from file paths, the <b>renaming</b> process will modify the file paths.</p>"
        "<p>There are two options available:"
        "<ol>"
        "<li>Renaming in place : the <b>source</b> file is renamed to the <b>most similar choice</b> in the same directory<br>This is done by selecting <code><b>Output Directory->Same as input</b></code></li>"
        "<li>Renaming in another directory : the <b>source</b> file is kept and the renamed file is copied in another directory<br>This is done by selecting <code><b>Output Directory->User-defined directory</b></code></li>"
        "</ol>"
        "<h3>Options</h3>"
        "<ul>"
        "<li><b>Type of inputs</b><br><br>"
        "<ol>"
        '<li><b>Files</b>: Choices and Sources are representing files. This is the standard mode where renaming is applicable.</li>'
        '<li><b>Strings</b>: Choices and Sources are representing strings. Every options or actions related to files (renaming, deleting, full path, suffix) are not applicable.</li>'
        "</ol>"
        "<br><li><b>View full path</b><br><br>"
        "When <b>source</b> strings are coming from file paths, the full path of files are shown in the <code><b>Source Name</b></code> and <code><b>Renaming Preview</b></code> columns.<br>"
        "When <b>choices</b> strings are coming from file paths, the full path of files are shown in the <code><b>Closest Match</b></code> columns.</li>"
        "<br><li><b>Hide suffix</b><br><br>"
        "When <b>source</b> strings are coming from file paths, the suffixes are hidden in the <code><b>Source Name</b></code> and <code><b>Renaming Preview</b></code> columns.<br>"
        "When <b>choices</b> strings are coming from file paths, the suffixes are hidden in the <code><b>Closest Match</b></code> columns.</li>"
        "<br><li><b>Keep original on renaming</b><br><br>"
        "During <b>renaming</b>, the original file is kept."
        "<br><li><b>Keep matched file suffix</b><br><br>"
        "During <b>renaming</b>, the suffix of the <b>most similar choice</b> is used before suffix of the <b>source</b>.<br>"
        'For example, if <b>source</b> is <code><font color="blue">Amaryllis.png</font></code>, and <b>most similar choice</b> is <code><font color="red">Amaryllidinae.rom</font></code>, <b>renamed source</b> is <code><font color="red">Amaryllidinae.rom</font></code><code><font color="blue">.png</font></code>'
        "<br><li><b>Always match first letter</b><br><br>"
        "During <b>matching</b>, each <b>source</b> will search for the <b>most similar choice</b> among <b>choices</b> that start with the same letter only. This decreases greatly the processing time during <b>matching</b>."
        "<br><li><b>Source can match multiple choices</b><br><br>"
        "If a <b>source</b> matches a group of <b>choices</b> with different <b>masks</b>, then the renaming will create copies of this <b>source</b> for each <b>mask</b>.<br>"
        'For example, if <b>source</b> is <code><font color="blue">Amaryllis.png</font></code>, and <b>most similar choices</b> are <code><font color="red">Amaryllidinae[_disk1, disk2].rom</font></code>, <b>renamed sources</b> are <code><font color="red">Amaryllidinae_disk1</font><font color="blue">.png</font></code> and <code><font color="red">Amaryllidinae_disk2</font><font color="blue">.png</font></code>.<br>'
        '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;If option is unchecked <b>renamed source</b> is only <code><font color="red">Amaryllidinae</font><font color="blue">.png</font></code>.'
        "<br><li><b>Number of processes</b><br><br>"
        "Number of parallel processes used when launching matching/renaming/undoing tasks (=1 to not use parallel tasks)"
        "<br><li><b>Similarity scorer</b><br><br>"
        "Type of algorithm used for matching (see https://github.com/seatgeek/thefuzz)"
        "</ul>"
        "<h3>Available actions on <b>source</b> items</h3>"
        "<p>From the context menu on each <b>source</b> item in the main list, the following actions are available:"
        "<ul>"
        "<li><b>Delete source file(s)</b><br><br>"
        "Delete the file associated with the selected <b>source</b> string."
        "<br><li><b>Reset choice</b><br><br>"
        "Reset the <b>choice</b>."
        "<br><li><b>Best choice</b><br><br>"
        "Set the <b>choice</b> to the best match."
        "<br><li><b>Pick a match...</b><br><br>"
        "Change the <b>choice</b> by typing your own from the available <b>choices</b>."
        "<br><li><b>Alternate match</b><br><br>"
        "Change the <b>choice</b> by chosing one of the 10 best <b>choices</b> sorted by similarity score."
        "</ul>"
        "<h3>Sessions management</h3>"
        "<p>The current list of <b>sources</b> and <b>choices</b> as well as the current <b>most similar choice</b> can be saved to a file by using <code><b>File->Save Session</b></code>.</p>"
        "<p>A saved session is restored by using <code><b>File->Load Session</b></code>. When restoring a session, the current list of sources and choices is resetted first.</p>"
        "<p>The list of the 8 most recent saved session files can be loaded directly from the <code><b>File</b></code> menu.</p>"
        "<h3>Command line options</h3>"
        "<pre>"
        "usage: pyfuzzyrenamer [-h] [--sources SOURCES] [--choices CHOICES] {rename,report_match,preview_rename} ...<br>"
        "<br>"
        "positional arguments:<br>"
        "  {rename,report_match,preview_rename}<br>"
        "                        sub-command help<br>"
        "    rename              rename sources<br>"
        "    report_match        report best match<br>"
        "    preview_rename      preview renaming<br>"
        "<br>"
        "optional arguments:<br>"
        "  -h, --help            show this help message and exit<br>"
        "  --sources SOURCES     directory for sources<br>"
        "  --choices CHOICES     directory for choices<br>"
        "</pre>"
        "<h3>Licenses</h3>"
        "PyFuzzy-renamer is licensed under MIT license:"
        "<pre>Copyright (c) 2020 pcjco\n"
        "\n"
        "Permission is hereby granted, free of charge, to any person obtaining a copy\n"
        'of this software and associated documentation files (the "Software"), to deal\n'
        "in the Software without restriction, including without limitation the rights\n"
        "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n"
        "copies of the Software, and to permit persons to whom the Software is\n"
        "furnished to do so, subject to the following conditions:\n"
        "\n"
        "The above copyright notice and this permission notice shall be included in all\n"
        "copies or substantial portions of the Software.\n"
        "\n"
        'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n'
        "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n"
        "FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n"
        "AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n"
        "LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n"
        "OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE\n"
        "SOFTWARE.\n"
        "</pre>"
        "PyFuzzy-renamer includes works from third-party software<br>"
        '<ul><li><a href ="http://bitbucket.org/raz/wxautocompletectrl/">wxautocompletectrl</a> (by Toni Ruža &lt;toni.ruza@gmail.com&gt;)</li></ul>'
        "<pre>"
        "Copyright (c) 2008-2019, Toni Ruža, All rights reserved.\n"
        "Redistribution and use in source and binary forms, with or without\n"
        "modification, are permitted provided that the following conditions are met:\n"
        "\n"
        "* Redistributions of source code must retain the above copyright notice,\n"
        "  this list of conditions and the following disclaimer.\n"
        "* Redistributions in binary form must reproduce the above copyright notice,\n"
        "  this list of conditions and the following disclaimer in the documentation\n"
        "  and/or other materials provided with the distribution.\n"
        "\n"
        "THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 'AS IS'\n"
        "AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE\n"
        "IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE\n"
        "ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE\n"
        "LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR\n"
        "CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF\n"
        "SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS\n"
        "INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN\n"
        "CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)\n"
        "ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE\n"
        "POSSIBILITY OF SUCH DAMAGE.\n"
        "</pre>"
    )
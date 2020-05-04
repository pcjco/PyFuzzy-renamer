import os
import os.path
import pickle as pickle
import shutil
import wx
import wx.aui
import wx.html
from multiprocessing import cpu_count, freeze_support
from pathlib import Path

from . import __version__
from pyfuzzyrenamer import (
    config,
    filters,
    main_listctrl,
    icons,
    masks,
    masksandfilters_dlg,
    match,
    utils,
)
from pyfuzzyrenamer.config import get_config

candidates = {}
glob_choices = set()


def getRenamePreview(input, match):
    if not match.name:
        return Path()
    Qkeep_match_ext = get_config()["keep_match_ext"]
    stem, suffix = utils.GetFileStemAndSuffix(match)
    match_clean = utils.strip_extra_whitespace(utils.strip_illegal_chars(stem))
    if Qkeep_match_ext:
        match_clean += suffix
    f_masked = masks.FileMasked(input)
    stem, suffix = utils.GetFileStemAndSuffix(input)
    return Path(
        os.path.join(
            get_config()["folder_output"]
            if get_config()["folder_output"]
            else input.parent,
            f_masked.masked[0] + match_clean + f_masked.masked[2],
        )
        + suffix
    )


def RefreshCandidates():
    candidates.clear()
    candidates["all"] = [filters.FileFiltered(f) for f in glob_choices]
    if get_config()["match_firstletter"]:
        for word in candidates["all"]:
            first_letter = word.filtered[0]
            if first_letter in candidates.keys():
                candidates[first_letter].append(word)
            else:
                candidates[first_letter] = [word]


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
                    for fp2 in fp.resolve().glob("*"):
                        if fp2.is_file():
                            files.append(str(fp2))
            except (OSError, IOError):
                pass
        if Qsources:
            self.window.AddSourceFromFiles(files)
        else:
            self.window.AddChoicesFromFiles(files)
        return True

    def SourcesOrChoices(
        self,
        parent,
        question="Add the files to source or choice list?",
        caption="Drag&Drop question",
    ):
        dlg = wx.GenericMessageDialog(
            parent, question, caption, wx.YES_NO | wx.ICON_QUESTION
        )
        dlg.SetYesNoLabels("Sources", "Choices")
        result = dlg.ShowModal() == wx.ID_YES
        dlg.Destroy()
        return result


class MainPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, style=wx.WANTS_CHARS)

        self.parent = parent

        self.mgr = wx.aui.AuiManager()
        self.mgr.SetManagedWindow(self)

        panel_top = wx.Panel(parent=self)
        panel_list = wx.Panel(parent=panel_top)
        panel_listbutton = wx.Panel(parent=panel_list)

        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        top_sizer.Add(panel_list, 1, wx.EXPAND)
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

        btn_ren = wx.Button(panel_listbutton, label="Rename")
        btn_ren.SetBitmap(icons.Rename_16_PNG.GetBitmap(), wx.LEFT)
        btn_ren.SetToolTip("Rename sources")

        btn_undo = wx.Button(panel_listbutton, label="Undo")
        btn_undo.SetBitmap(icons.Undo_16_PNG.GetBitmap(), wx.LEFT)
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

        self.list_ctrl = main_listctrl.FuzzyRenamerListCtrl(
            panel_list,
            size=(-1, -1),
            style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_EDIT_LABELS,
        )

        file_drop_target = FuzzyRenamerFileDropTarget(self)
        self.SetDropTarget(file_drop_target)

        panel_list_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_list_sizer.Add(panel_listbutton, 0, wx.EXPAND | wx.ALL, 0)
        panel_list_sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 0)
        panel_list.SetSizer(panel_list_sizer)

        panel_log = wx.Panel(parent=self)

        log = wx.TextCtrl(
            panel_log, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL
        )
        wx.Log.SetActiveTarget(wx.LogTextCtrl(log))

        log_sizer = wx.BoxSizer()
        log_sizer.Add(log, 1, wx.EXPAND | wx.ALL, 5)
        panel_log.SetSizer(log_sizer)

        self.mgr.AddPane(panel_top, wx.aui.AuiPaneInfo().Name("pane_list").CenterPane())
        self.mgr.AddPane(
            panel_log,
            wx.aui.AuiPaneInfo()
            .CloseButton(True)
            .Name("pane_log")
            .Caption("Log")
            .FloatingSize(-1, 200)
            .BestSize(-1, 200)
            .MinSize(-1, 120)
            .Bottom(),
        )
        self.mgr.Update()
        btn_run.Bind(wx.EVT_BUTTON, self.OnRun)
        btn_ren.Bind(wx.EVT_BUTTON, self.OnRename)
        btn_reset.Bind(wx.EVT_BUTTON, self.OnReset)
        btn_filters.Bind(wx.EVT_BUTTON, self.OnFilters)
        btn_undo.Bind(wx.EVT_BUTTON, self.OnUndo)
        btn_add_source_from_files.Bind(wx.EVT_BUTTON, self.OnAddSourceFromFiles)
        btn_add_choice_from_file.Bind(wx.EVT_BUTTON, self.OnAddChoicesFromFiles)

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
                self.list_ctrl.listdata[index][config.D_FILENAME],
                self.list_ctrl.listdata[index][config.D_MATCHNAME],
            )
        self.list_ctrl.RefreshList()

    def OnKeepOriginal(self, evt):
        item = self.parent.GetMenuBar().FindItemById(evt.GetId())
        get_config()["keep_original"] = item.IsChecked()

    def OnMatchFirstLetter(self, evt):
        item = self.parent.GetMenuBar().FindItemById(evt.GetId())
        get_config()["match_firstletter"] = item.IsChecked()
        RefreshCandidates()

    def OnAddSourceFromDir(self, evt):
        with wx.DirDialog(
            self,
            "Choose source directory",
            get_config()["folder_sources"],
            wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        ) as dirDialog:

            if dirDialog.ShowModal() == wx.ID_CANCEL:
                return
            self.AddSourceFromDir(dirDialog.GetPath())

    def AddSourceFromDir(self, directory):
        get_config()["folder_sources"] = directory
        newdata = []
        for f in sorted(Path(directory).resolve().glob("*"), key=os.path.basename):
            try:
                if f.is_file():
                    newdata.append([f, 0, Path(), Path(), "Not processed", "True", f])
            except (OSError, IOError):
                pass
        self.list_ctrl.AddToList(newdata)

    def OnAddSourceFromFiles(self, evt):
        with wx.FileDialog(
            self,
            "Choose source files",
            get_config()["folder_sources"],
            style=wx.FD_DEFAULT_STYLE | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE,
        ) as self.fileDialog:

            if self.fileDialog.ShowModal() == wx.ID_CANCEL:
                return
            self.AddSourceFromFiles(self.fileDialog.GetPaths())

    def AddSourceFromFiles(self, files):
        newdata = []
        first = True
        for f in files:
            if not f:
                continue
            try:
                fp = Path(f)
                if first:
                    first = False
                    get_config()["folder_sources"] = str(fp.parent)
                newdata.append([fp, 0, Path(), Path(), "Not processed", "True", fp])
            except (OSError, IOError):
                pass
        self.list_ctrl.AddToList(newdata)

    def OnAddSourceFromClipboard(self, evt):
        files = utils.ClipBoardFiles()
        if files:
            self.AddSourceFromFiles(files)

    def OnAddChoicesFromDir(self, evt):
        with wx.DirDialog(
            self,
            "Choose choice directory",
            get_config()["folder_choices"],
            wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        ) as dirDialog:

            if dirDialog.ShowModal() == wx.ID_CANCEL:
                return
            self.AddChoicesFromDir(dirDialog.GetPath())

    def AddChoicesFromDir(self, directory):
        get_config()["folder_choices"] = directory
        for f in sorted(Path(directory).resolve().glob("*"), key=os.path.basename):
            try:
                if f.is_file():
                    glob_choices.add(f)
            except (OSError, IOError):
                pass
        RefreshCandidates()

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
        first = True
        for f in files:
            if not f:
                continue
            try:
                fp = Path(f)
                if first:
                    first = False
                    get_config()["folder_choices"] = str(fp.parent)
                glob_choices.add(fp)
            except (OSError, IOError):
                pass
        RefreshCandidates()

    def OnAddChoicesFromClipboard(self, evt):
        files = utils.ClipBoardFiles()
        if files:
            self.AddChoicesFromFiles(files)

    def OnOutputDirectory(self, evt):
        if self.parent.mnu_user_dir.IsChecked():
            self.parent.mnu_same_as_input.Check(False)
        else:
            self.parent.mnu_user_dir.Check(True)
        with wx.DirDialog(
            self,
            "Choose output directory",
            get_config()["folder_output"],
            wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
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
                self.list_ctrl.listdata[index][config.D_FILENAME],
                self.list_ctrl.listdata[index][config.D_MATCHNAME],
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

                pos = self.list_ctrl.GetItemData(row_id)  # 0-based unsorted index
                if matches[count]:
                    self.list_ctrl.listdata[pos][config.D_MATCH_SCORE] = matches[
                        count
                    ].match_results[0][1]
                    self.list_ctrl.listdata[pos][config.D_MATCHNAME] = (
                        matches[count].match_results[0][0].file
                    )
                    self.list_ctrl.listdata[pos][config.D_PREVIEW] = getRenamePreview(
                        self.list_ctrl.listdata[pos][config.D_FILENAME],
                        self.list_ctrl.listdata[pos][config.D_MATCHNAME],
                    )
                    self.list_ctrl.listdata[pos][config.D_STATUS] = "Matched"
                else:
                    self.list_ctrl.listdata[pos][config.D_MATCH_SCORE] = 0
                    self.list_ctrl.listdata[pos][config.D_MATCHNAME] = Path()
                    self.list_ctrl.listdata[pos][config.D_PREVIEW] = Path()
                    self.list_ctrl.listdata[pos][config.D_STATUS] = "No match"
                count += 1
        self.list_ctrl.RefreshList()

    def OnReset(self, evt):
        glob_choices.clear()
        candidates.clear()
        self.list_ctrl.listdata.clear()
        self.list_ctrl.DeleteAllItems()

    def OnFilters(self, evt):
        dia = masksandfilters_dlg.masksandfiltersDialog(None, "Masks & Filters")
        res = dia.ShowModal()
        if res == wx.ID_OK:
            get_config()["filters"] = dia.panel.filters_list.GetFilters()
            filters.FileFiltered.filters = filters.CompileFilters(
                get_config()["filters"]
            )
            get_config()["masks"] = dia.panel.masks_list.GetMasks()
            masks.FileMasked.masks = masks.CompileMasks(get_config()["masks"])
            get_config()["filters_test"] = dia.panel.preview_filters.GetValue()
            get_config()["masks_test"] = dia.panel.preview_masks.GetValue()

        dia.Destroy()

    def OnRename(self, evt):
        Qview_fullpath = get_config()["show_fullpath"]
        Qhide_extension = get_config()["hide_extension"]
        Qkeep_original = get_config()["keep_original"]
        row_id = -1
        while True:  # loop all the checked items
            row_id = self.list_ctrl.GetNextItem(row_id)
            if row_id == -1:
                break
            if self.list_ctrl.IsItemChecked(row_id):
                pos = self.list_ctrl.GetItemData(row_id)  # 0-based unsorted index

                old_path = self.list_ctrl.listdata[pos][config.D_FILENAME]
                preview_path = self.list_ctrl.listdata[pos][config.D_PREVIEW]
                if preview_path:
                    if old_path != preview_path:
                        old_file = str(old_path)
                        new_file = str(preview_path)
                        try:
                            if old_path.is_file():
                                if Qkeep_original:
                                    shutil.copy2(old_file, new_file)
                                    wx.LogMessage(
                                        "Copying : %s --> %s" % (old_file, new_file)
                                    )
                                else:
                                    os.rename(old_file, new_file)
                                    wx.LogMessage(
                                        "Renaming : %s --> %s" % (old_file, new_file)
                                    )
                                new_path = Path(new_file)
                                new_match = match.get_match(new_path)
                                if new_match:
                                    self.list_ctrl.listdata[pos] = [
                                        new_path,
                                        new_match[0][1],
                                        new_match[0][0].file,
                                        getRenamePreview(
                                            new_path, new_match[0][0].file
                                        ),
                                        "Matched",
                                        self.list_ctrl.listdata[pos][config.D_CHECKED],
                                        old_path if not Qkeep_original else None,
                                    ]
                                    self.list_ctrl.SetItem(
                                        row_id,
                                        config.D_MATCH_SCORE,
                                        str(
                                            self.list_ctrl.listdata[pos][
                                                config.D_MATCH_SCORE
                                            ]
                                        ),
                                    )
                                    stem, suffix = utils.GetFileStemAndSuffix(
                                        self.list_ctrl.listdata[pos][config.D_MATCHNAME]
                                    )
                                    self.list_ctrl.SetItem(
                                        row_id,
                                        config.D_MATCHNAME,
                                        str(
                                            self.list_ctrl.listdata[pos][
                                                config.D_MATCHNAME
                                            ]
                                        )
                                        if Qview_fullpath
                                        else (
                                            stem
                                            if Qhide_extension
                                            else self.list_ctrl.listdata[pos][
                                                config.D_MATCHNAME
                                            ].name
                                        ),
                                    )
                                    stem, suffix = utils.GetFileStemAndSuffix(
                                        self.list_ctrl.listdata[pos][config.D_PREVIEW]
                                    )
                                    self.list_ctrl.SetItem(
                                        row_id,
                                        config.D_PREVIEW,
                                        str(
                                            self.list_ctrl.listdata[pos][
                                                config.D_PREVIEW
                                            ]
                                        )
                                        if Qview_fullpath
                                        else (
                                            stem
                                            if Qhide_extension
                                            else self.list_ctrl.listdata[pos][
                                                config.D_PREVIEW
                                            ].name
                                        ),
                                    )
                                else:
                                    self.list_ctrl.listdata[pos] = [
                                        new_path,
                                        0,
                                        Path(),
                                        Path(),
                                        "No match",
                                        self.listdata[pos][config.D_CHECKED],
                                        old_path if not Qkeep_original else None,
                                    ]
                                    self.list_ctrl.SetItem(
                                        row_id, config.D_MATCH_SCORE, ""
                                    )
                                    self.list_ctrl.SetItem(
                                        row_id, config.D_MATCHNAME, ""
                                    )
                                    self.list_ctrl.SetItem(row_id, config.D_PREVIEW, "")

                                stem, suffix = utils.GetFileStemAndSuffix(
                                    self.list_ctrl.listdata[pos][config.D_FILENAME]
                                )
                                self.list_ctrl.SetItem(
                                    row_id,
                                    config.D_FILENAME,
                                    str(self.list_ctrl.listdata[pos][config.D_FILENAME])
                                    if Qview_fullpath
                                    else (
                                        stem
                                        if Qhide_extension
                                        else self.list_ctrl.listdata[pos][
                                            config.D_FILENAME
                                        ].name
                                    ),
                                )
                                self.list_ctrl.SetItem(
                                    row_id,
                                    config.D_STATUS,
                                    self.list_ctrl.listdata[pos][config.D_STATUS],
                                )

                        except (OSError, IOError):
                            wx.LogMessage(
                                "Error when renaming : %s --> %s" % (old_file, new_file)
                            )

    def OnUndo(self, evt):
        Qview_fullpath = get_config()["show_fullpath"]
        Qhide_extension = get_config()["hide_extension"]
        row_id = -1
        while True:  # loop all the checked items
            row_id = self.list_ctrl.GetNextItem(row_id)
            if row_id == -1:
                break
            pos = self.list_ctrl.GetItemData(row_id)  # 0-based unsorted index

            previous_path = self.list_ctrl.listdata[pos][config.D_PREVIOUS_FILENAME]
            if not previous_path:
                continue

            current_path = self.list_ctrl.listdata[pos][config.D_FILENAME]
            if current_path != previous_path:
                old_file = str(current_path)
                new_file = str(previous_path)

                try:
                    if current_path.is_file():
                        os.rename(old_file, new_file)
                    wx.LogMessage("Renaming : %s --> %s" % (old_file, new_file))
                    new_path = Path(new_file)
                    similarity = match.mySimilarityScorer(
                        masks.FileMasked(new_path).masked[1],
                        filters.FileFiltered(
                            self.list_ctrl.listdata[pos][config.D_MATCHNAME]
                        ).filtered,
                    )
                    self.list_ctrl.listdata[pos][config.D_FILENAME] = new_path
                    self.list_ctrl.listdata[pos][config.D_MATCH_SCORE] = similarity
                    self.list_ctrl.listdata[pos][config.D_PREVIEW] = getRenamePreview(
                        new_path, self.list_ctrl.listdata[pos][config.D_MATCHNAME]
                    )
                    self.list_ctrl.listdata[pos][config.D_PREVIOUS_FILENAME] = new_path
                    stem, suffix = utils.GetFileStemAndSuffix(
                        self.list_ctrl.listdata[pos][config.D_FILENAME]
                    )
                    self.list_ctrl.SetItem(
                        row_id,
                        config.D_FILENAME,
                        str(self.list_ctrl.listdata[pos][config.D_FILENAME])
                        if Qview_fullpath
                        else (
                            stem
                            if Qhide_extension
                            else self.list_ctrl.listdata[pos][config.D_FILENAME].name
                        ),
                    )
                    self.list_ctrl.SetItem(
                        row_id,
                        config.D_MATCH_SCORE,
                        str(self.list_ctrl.listdata[pos][config.D_MATCH_SCORE]),
                    )
                    stem, suffix = utils.GetFileStemAndSuffix(
                        self.list_ctrl.listdata[pos][config.D_PREVIEW]
                    )
                    self.list_ctrl.SetItem(
                        row_id,
                        config.D_PREVIEW,
                        str(self.list_ctrl.listdata[pos][config.D_PREVIEW])
                        if Qview_fullpath
                        else (
                            stem
                            if Qhide_extension
                            else self.list_ctrl.listdata[pos][config.D_PREVIEW].name
                        ),
                    )

                except (OSError, IOError):
                    wx.LogMessage(
                        "Error when renaming : %s --> %s" % (old_file, new_file)
                    )


class aboutDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title="About PyFuzzy-renamer")
        html = wxHTML(self)

        html.SetPage(
            '<font size="30">PyFuzzy-renamer ' + __version__ + "</font><br><br>"
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
            self,
            parent,
            title=label,
            size=(600, 300),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
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
            title="PyFuzzy-renamer " + __version__,
            pos=wx.Point(get_config()["window"][2], get_config()["window"][3]),
            size=wx.Size(get_config()["window"][0], get_config()["window"][1]),
        )
        freeze_support()

        bundle = wx.IconBundle()
        bundle.AddIcon(wx.Icon(icons.Rename_16_PNG.GetBitmap()))
        bundle.AddIcon(wx.Icon(icons.Rename_32_PNG.GetBitmap()))
        self.SetIcons(bundle)

        self.help = None
        self.statusbar = self.CreateStatusBar(2)

        # Add a panel so it looks the correct on all platforms
        self.panel = MainPanel(self)

        menubar = wx.MenuBar()
        self.files = wx.Menu()
        options = wx.Menu()
        help = wx.Menu()

        sources = wx.Menu()
        sources_ = wx.MenuItem(
            self.files, wx.ID_ANY, "&Sources", "Select sources (to rename)"
        )
        sources_.SetSubMenu(sources)

        mnu_source_from_dir = wx.MenuItem(
            sources,
            wx.ID_ANY,
            "Sources from &Directory...\tCtrl+D",
            "Select sources from directory",
        )
        mnu_source_from_dir.SetBitmap(icons.AddFolder_16_PNG.GetBitmap())
        sources.Append(mnu_source_from_dir)

        mnu_source_from_clipboard = wx.MenuItem(
            sources,
            wx.ID_ANY,
            "Sources from &Clipboard",
            "Select sources from clipboard",
        )
        mnu_source_from_clipboard.SetBitmap(icons.Clipboard_16_PNG.GetBitmap())
        sources.Append(mnu_source_from_clipboard)

        choices = wx.Menu()
        choices_ = wx.MenuItem(
            self.files, wx.ID_ANY, "&Choices", "Select choices (to match)"
        )
        choices_.SetSubMenu(choices)

        mnu_target_from_dir = wx.MenuItem(
            choices,
            wx.ID_ANY,
            "Choices from &Directory...\tCtrl+T",
            "Select choices from directory",
        )
        mnu_target_from_dir.SetBitmap(icons.AddFolder_16_PNG.GetBitmap())
        choices.Append(mnu_target_from_dir)

        mnu_choices_from_clipboard = wx.MenuItem(
            choices,
            wx.ID_ANY,
            "Choices from &Clipboard",
            "Select choices from clipboard",
        )
        mnu_choices_from_clipboard.SetBitmap(icons.Clipboard_16_PNG.GetBitmap())
        choices.Append(mnu_choices_from_clipboard)

        output_dir = wx.Menu()
        output_dir_ = wx.MenuItem(
            self.files, wx.ID_ANY, "&Output Directory", "Select output directory"
        )
        output_dir_.SetBitmap(icons.Folder_16_PNG.GetBitmap())
        output_dir_.SetSubMenu(output_dir)

        self.mnu_same_as_input = output_dir.AppendCheckItem(
            wx.ID_ANY, "&Same as source", "Same as source"
        )
        self.mnu_user_dir = output_dir.AppendCheckItem(
            wx.ID_ANY, "&User-defined directory...", "Select User-defined directory"
        )

        mnu_open = wx.MenuItem(
            self.files, wx.ID_ANY, "&Load Session...\tCtrl+O", "Open..."
        )
        mnu_open.SetBitmap(icons.Open_16_PNG.GetBitmap())

        mnu_save = wx.MenuItem(
            self.files, wx.ID_ANY, "&Save Session\tCtrl+S", "Save..."
        )
        mnu_save.SetBitmap(icons.Save_16_PNG.GetBitmap())

        self.mnu_quit = wx.MenuItem(
            self.files, wx.ID_ANY, "&Exit\tAlt+F4", "Exit the Application"
        )
        self.mnu_quit.SetBitmap(icons.Quit_16_PNG.GetBitmap())

        self.files.Append(sources_)
        self.files.Append(choices_)
        self.files.Append(output_dir_)
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
                    "&"
                    + str(i + 1)
                    + ": "
                    + utils.shorten_path(get_config()["recent_session"][i], 64),
                    "",
                )
                self.files.Append(new_mnu_recent)
                self.mnu_recents.append(new_mnu_recent)
            self.files.AppendSeparator()
        self.files.Append(self.mnu_quit)

        mnu_view_fullpath = options.AppendCheckItem(
            wx.ID_ANY, "&View full path", "View full path"
        )
        self.mnu_hide_extension = options.AppendCheckItem(
            wx.ID_ANY, "&Hide suffix", "Hide suffix"
        )
        self.mnu_keep_original = options.AppendCheckItem(
            wx.ID_ANY, "Keep &original on renaming", "Keep original on renaming"
        )
        self.mnu_keep_match_ext = options.AppendCheckItem(
            wx.ID_ANY, "&Keep matched file suffix", "Keep matched file suffix"
        )
        self.mnu_match_firstletter = options.AppendCheckItem(
            wx.ID_ANY,
            "&Always match first letter",
            "Enforce choices that match the first letter of the source",
        )

        workers = wx.Menu()
        workers_ = wx.MenuItem(
            options,
            wx.ID_ANY,
            "&Number of matching processes",
            "Select the number of parallel processes used during matching",
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
        if (
            get_config()["workers"] <= len(self.mnu_procs)
            and get_config()["workers"] > 0
        ):
            self.mnu_procs[get_config()["workers"] - 1].Check(True)

        mnu_doc = wx.MenuItem(help, wx.ID_ANY, "&Help...", "Help")
        mnu_doc.SetBitmap(icons.Help_16_PNG.GetBitmap())
        help.Append(mnu_doc)
        mnu_about = wx.MenuItem(help, wx.ID_ANY, "&About...", "About the application")
        mnu_about.SetBitmap(icons.Info_16_PNG.GetBitmap())
        help.Append(mnu_about)

        menubar.Append(self.files, "&File")
        menubar.Append(options, "&Options")
        menubar.Append(help, "&Help")
        self.SetMenuBar(menubar)

        if get_config()["folder_output"]:
            self.mnu_user_dir.Check(True)
        else:
            self.mnu_same_as_input.Check(True)

        mnu_view_fullpath.Check(get_config()["show_fullpath"])
        self.mnu_hide_extension.Check(get_config()["hide_extension"])
        self.mnu_hide_extension.Enable(not get_config()["show_fullpath"])
        self.mnu_keep_original.Check(get_config()["keep_original"])
        self.mnu_keep_match_ext.Check(get_config()["keep_match_ext"])
        self.mnu_match_firstletter.Check(get_config()["match_firstletter"])

        self.Bind(wx.EVT_MENU, self.panel.OnAddSourceFromDir, mnu_source_from_dir)
        self.Bind(
            wx.EVT_MENU, self.panel.OnAddSourceFromClipboard, mnu_source_from_clipboard
        )
        self.Bind(wx.EVT_MENU, self.panel.OnAddChoicesFromDir, mnu_target_from_dir)
        self.Bind(
            wx.EVT_MENU,
            self.panel.OnAddChoicesFromClipboard,
            mnu_choices_from_clipboard,
        )
        self.Bind(wx.EVT_MENU, self.panel.OnOutputDirectory, self.mnu_user_dir)
        self.Bind(wx.EVT_MENU, self.panel.OnSameOutputDirectory, self.mnu_same_as_input)
        self.Bind(wx.EVT_MENU, self.panel.OnViewFullPath, mnu_view_fullpath)
        self.Bind(wx.EVT_MENU, self.panel.OnHideExtension, self.mnu_hide_extension)
        self.Bind(wx.EVT_MENU, self.panel.OnKeepMatchExtension, self.mnu_keep_match_ext)
        self.Bind(
            wx.EVT_MENU, self.panel.OnMatchFirstLetter, self.mnu_match_firstletter
        )
        self.Bind(wx.EVT_MENU, self.panel.OnKeepOriginal, self.mnu_keep_original)
        self.Bind(wx.EVT_MENU, self.OnOpen, mnu_open)
        self.Bind(wx.EVT_MENU, self.OnSaveAs, mnu_save)
        self.Bind(wx.EVT_MENU, self.OnQuit, self.mnu_quit)
        self.Bind(wx.EVT_MENU, self.OnHelp, mnu_doc)
        self.Bind(wx.EVT_MENU, self.OnAbout, mnu_about)
        self.Bind(wx.EVT_CLOSE, self.OnQuit)

        for mnu_recent in self.mnu_recents:
            self.Bind(wx.EVT_MENU, self.OnOpenRecent, mnu_recent)
        for mnu_proc in self.mnu_procs:
            self.Bind(wx.EVT_MENU, self.OnNumProc, mnu_proc)

        self.Show(True)

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
            self,
            "Save file",
            wildcard="SAVE files (*.sav)|*.sav",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            # save the current contents in the file
            self.SaveSession(fileDialog.GetPath())

    def OnNumProc(self, event):
        menu = event.GetEventObject()
        menuItem = menu.FindItemById(event.GetId())
        get_config()["workers"] = self.mnu_procs.index(menuItem) + 1

    def OnOpenRecent(self, event):
        menu = event.GetEventObject()
        menuItem = menu.FindItemById(event.GetId())
        pathname = get_config()["recent_session"][self.mnu_recents.index(menuItem)]
        self.LoadSession(pathname)

    def OnOpen(self, event):
        with wx.FileDialog(
            self,
            "Open SAVE file",
            wildcard="SAVE files (*.sav)|*.sav",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            # Proceed loading the file chosen by the user
            self.LoadSession(fileDialog.GetPath())

    def UpdateRecentSession(self, pathname):
        if pathname in get_config()["recent_session"]:
            idx = get_config()["recent_session"].index(pathname)
            if idx:
                get_config()["recent_session"].insert(
                    0, get_config()["recent_session"].pop(idx)
                )
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
            item, pos = self.files.FindChildItem(
                self.mnu_quit.GetId()
            )  # Searh Exit button
            self.files.InsertSeparator(pos)

        # - Refresh recents
        self.mnu_recents.clear()
        for i in range(0, len(get_config()["recent_session"])):
            new_mnu_recent = wx.MenuItem(
                self.files,
                wx.ID_ANY,
                "&"
                + str(i + 1)
                + ": "
                + utils.shorten_path(get_config()["recent_session"][i], 64),
                "",
            )
            item, pos = self.files.FindChildItem(
                self.mnu_quit.GetId()
            )  # Searh Exit button
            self.files.Insert(pos - 1, new_mnu_recent)
            self.mnu_recents.append(new_mnu_recent)
            self.Bind(wx.EVT_MENU, self.OnOpenRecent, new_mnu_recent)

    def SaveSession(self, pathname):
        try:
            with open(pathname, "wb") as file:
                pickle.dump([glob_choices, self.panel.list_ctrl.listdata], file)

            self.UpdateRecentSession(pathname)

        except IOError:
            wx.LogError("Cannot save current data in file '%s'." % pathname)

    def LoadSession(self, pathname):
        global glob_choices

        self.UpdateRecentSession(pathname)
        list = self.panel.list_ctrl
        try:
            with open(pathname, "rb") as file:
                glob_choices, list.listdata = pickle.load(file)
        except IOError:
            wx.LogError("Cannot open file '%s'." % pathname)

        RefreshCandidates()
        list.DeleteAllItems()
        row_id = 0
        Qview_fullpath = get_config()["show_fullpath"]
        Qhide_extension = get_config()["hide_extension"]
        for key, data in list.listdata.items():
            stem, suffix = utils.GetFileStemAndSuffix(data[config.D_FILENAME])
            item_name = (
                str(data[config.D_FILENAME])
                if Qview_fullpath
                else (stem if Qhide_extension else data[config.D_FILENAME].name)
            )
            list.InsertItem(row_id, item_name)
            if data[config.D_MATCHNAME].name:
                list.SetItem(
                    row_id, config.D_MATCH_SCORE, str(data[config.D_MATCH_SCORE])
                )
                stem, suffix = utils.GetFileStemAndSuffix(data[config.D_MATCHNAME])
                list.SetItem(
                    row_id,
                    config.D_MATCHNAME,
                    str(data[config.D_MATCHNAME])
                    if Qview_fullpath
                    else (stem if Qhide_extension else data[config.D_MATCHNAME].name),
                )
                stem, suffix = utils.GetFileStemAndSuffix(data[config.D_PREVIEW])
                list.SetItem(
                    row_id,
                    config.D_PREVIEW,
                    str(data[config.D_PREVIEW])
                    if Qview_fullpath
                    else (stem if Qhide_extension else data[config.D_PREVIEW].name),
                )
            else:
                list.SetItem(row_id, config.D_MATCH_SCORE, "")
                list.SetItem(row_id, config.D_MATCHNAME, "")
                list.SetItem(row_id, config.D_PREVIEW, "")
            list.SetItem(row_id, config.D_STATUS, data[config.D_STATUS])
            list.SetItem(row_id, config.D_CHECKED, data[config.D_CHECKED])
            list.SetItemData(row_id, key)
            list.CheckItem(row_id, True if data[config.D_CHECKED] == "True" else False)
            if data[config.D_CHECKED] == "False":
                f = list.GetItemFont(row_id)
                if not f.IsOk():
                    f = list.GetFont()
                font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
                font.SetStyle(wx.FONTSTYLE_ITALIC)
                font.SetWeight(f.GetWeight())
                list.SetItemFont(row_id, font)
            if data[config.D_STATUS] == "User choice":
                f = list.GetItemFont(row_id)
                if not f.IsOk():
                    f = list.GetFont()
                font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
                font.SetWeight(wx.FONTWEIGHT_BOLD)
                font.SetStyle(f.GetStyle())
                list.SetItemFont(row_id, font)
            row_id += 1
        list.itemDataMap = list.listdata

    def SaveUI(self):
        list = self.panel.list_ctrl
        for col in range(0, len(config.default_columns)):
            get_config()["col%d_order" % (col + 1)] = (
                list.GetColumnOrder(col) if list.HasColumnOrderSupport() else col
            )
            get_config()["col%d_size" % (col + 1)] = list.GetColumnWidth(col)
        get_config()["window"] = [
            self.GetSize().x,
            self.GetSize().y,
            self.GetPosition().x,
            self.GetPosition().y,
        ]


def getDoc():
    return (
        "<p>This application uses a list of input strings and will rename each one with the most similar string from another list of strings.<p>"
        "<h3>Terminology</h3>"
        "The following terminology is used in the application, and in this document:"
        "<ul>"
        "<li>The input strings to rename are called the <b>sources</b>;</li>"
        "<li>The strings used to search for similarity are called the <b>choices</b>;</li>"
        "<li>The process to search the most similar <b>choice</b> for a given <b>source</b> is referred here as <b>matching</b> process;</li>"
        "<li>When strings are coming from file paths, the following terminology is used:"
        "<ul>"
        "<li>A <b>file path</b> is composed of a <b>parent directory</b> and a <b>file name</b>;<br>e.g. <b>file path</b>=<code>c:/foo/bar/setup.tar.gz</code>, <b>parent directory</b>=<code>c:/foo/bar</code>, <b>file name</b>=<code>setup.tar.gz</code></li>"
        "<li>A <b>file name</b> is composed of a <b>stem</b> and a <b>suffix</b>;<br>e.g. <b>file name</b>=<code>setup.tar.gz</code>, <b>stem</b>=<code>setup.tar</code>, <b>suffix</b>=<code>.gz</code></li>"
        "<li>A <b>suffix</b> can only contain alphanumeric characters after the dot, if it contains non-alphanumeric characters, the suffix is considered as part of the <b>stem</b>;<br>e.g. <b>file name</b>=<code>A.Train III</code>, <b>stem</b>=<code>A.Train III</code>, <b>suffix</b>=<code>None</code></li>"
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
        '<p>E.g. if <b>source</b> is <code><font color="blue">c:/foo/Amaryllis.png</font></code>, and <b>most similar choice</b> is <code><font color="red">d:/bar/Amaryllidinae.jpg</font></code>, <b>renamed source</b> is <code><font color="blue">c:/foo/</font><font color="red">Amaryllidinae</font><font color="blue">.png</font></code></p>'
        "<p>If <b>masks</b> and <b>filters</b> are applied, the process applied to match and rename each <b>source</b> is the following:</p>"
        "<pre>"
        "                                ┌─────────┐<br>"
        '                      <font color="red">Choices</font>───┤Filtering├────<font color="red">Filtered Choices</font>────────┐<br>'
        "                                └─────────┘                            │<br>"
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
        "<li>Drag files or folders into application panel and choose <code><b>Sources</b></code> to add file paths to the current <b>sources</b>. For folders, the file paths of the files inside folders are added;</li>"
        "<li>Paste (Ctrl+V) into application panel and choose <code><b>Sources</b></code> to add file paths of the files or folders in clipboard to the current <b>sources</b>. For folders, the file paths of the files inside folders are added</li></ul>"
        "<h3>Choices</h3>"
        "<p>Choices are entered in the following ways:"
        "<ul><li>click on the <code><b>Choices</b></code> button to add a selection of files paths to the current <b>choices</b>;</li>"
        "<li>Go to <code><b>File->Choices->Choices from Directory</b></code> menu to add files paths from a selected folder to the current <b>choices</b>;</li>"
        "<li>Go to <code><b>File->Choices->Choices from Clipboard</b></code> menu to add files paths from clipboard to the current <b>choices</b>. If clipboard contains a folder, then the file paths of the files inside this folder are added;</li>"
        "<li>Drag files or folders into application panel and choose <code><b>Choices</b></code> to add file paths to the current <b>choices</b>. For folders, the file paths of the files inside folders are added;</li>"
        "<li>Paste (Ctrl+V) into application panel and choose <code><b>Choices</b></code> to add file paths of the files or folders in clipboard to the current <b>choices</b>. For folders, the file paths of the files inside folders are added</li></ul>"
        "<h3>Filters</h3>"
        "<p>To ease the <b>matching</b> process, filters can be applied to <b>sources</b> and <b>choices</b> before they are compared.</p>"
        '<p>E.g. <b>source</b> is <code><font color="blue">c:/foo/The Amaryllis.png</font></code> and <b>choice</b> is <code><font color="red">d:/bar/Amaryllidinae, The.txt</font></code>. It would be smart to clean the <b>sources</b> and <b>choices</b> by ignoring all articles before trying to find the <b>most similar choice</b>.</p>'
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
        "<p>Sometimes, it can be interesting to ignore some leading and/or trailing parts from a <b>source</b> in the <b>matching</b> process and restore them after the <b>renaming</b> process. It is particularly important in order to enhance <b>matching</b> when <b>choices</b> don't contain these parts.</p>"
        '<p>E.g. <b>source</b> is <code><font color="blue">c:/foo/(1983-06-22) Amaryllis [Russia].png</font></code>, and we want to ignore the date <code><font color="blue">(1983-06-22)</font></code> and the country <code><font color="blue">[Russia]</font></code> during <b>matching</b> but we need to restore them when <b>renaming</b>, '
        ' then if <b>most similar choice</b> is <code><font color="red">d:/bar/Amaryllidinae.jpg</font></code>, the <b>renamed source</b> should be <code><font color="blue">c:/foo/(1983-06-22) </font><font color="red">Amaryllidinae</font><font color="blue"> [Russia].png</font></code></p>'
        "<p>To achieve this, the application uses <b>masks</b>.</p>"
        "<p>The masks are using Python regular expression patterns. They are removed from <b>sources</b> strings before <b>filtering</b> and <b>matching</b> occur."
        "It is used to remove leading and trailing expressions (year, disk#...) before <b>matching</b> and restore them after <b>renaming</b>.</p>"
        "<p>For example, to preserve the Disk number at the end of a <b>source</b> file, a mask with the pattern <code>(\\s?disk\\d)$</code> could be used:<br>"
        "<ol>"
        '<li><b>Masking</b>: <code><font color="blue">c:/foo/The Wiiire Disk1.rom</font></code> &rarr; <code><font color="blue">The Wiiire</font></code> + Trailing mask = <code><font color="green"> Disk1</font></code></li>'
        '<li><b>Matching</b>: <code><font color="blue">The Wiiire</font></code> &rarr; <code><font color="red">The Wire</font></code></li>'
        '<li><b>Renaming</b>: <code><font color="blue">c:/foo/The Wiiire.rom</font></code> &rarr; <code><font color="blue">c:/foo/</font><font color="red">The Wire</font><font color="blue">.rom</font></code></li>'
        '<li><b>Unmkasking</b>: <code><font color="blue">c:/foo/The Wiiire.rom</font></code> &rarr; <code><font color="blue">c:/foo/The Wire<font color="green"> Disk1</font>.rom</font></code></li>'
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
        "<li><b>View full path</b><br><br>"
        "When <b>source</b> strings are coming from file paths, the full path of files are shown in the <code><b>Source Name</b></code> and <code><b>Renaming Preview</b></code> columns.<br>"
        "When <b>choices</b> strings are coming from file paths, the full path of files are shown in the <code><b>Closest Match</b></code> columns.</li>"
        "<br><li><b>Hide suffix</b><br><br>"
        "When <b>source</b> strings are coming from file paths, the suffixes are hidden in the <code><b>Source Name</b></code> and <code><b>Renaming Preview</b></code> columns.<br>"
        "When <b>choices</b> strings are coming from file paths, the suffixes are hidden in the <code><b>Closest Match</b></code> columns.</li>"
        "<br><li><b>Keep original on renaming</b><br><br>"
        "During <b>renaming</b>, the original file is kept."
        "<br><li><b>Keep matched file suffix</b><br><br>"
        "During <b>renaming</b>, the suffix of the <b>most similar choice</b> is used before suffix of the <b>source</b>.<br>"
        'E.g. if <b>source</b> is <code><font color="blue">Amaryllis.png</font></code>, and <b>most similar choice</b> is <code><font color="red">Amaryllidinae.rom</font></code>, <b>renamed source</b> is <code><font color="red">Amaryllidinae.rom</font></code><code><font color="blue">.png</font></code>'
        "<br><li><b>Always match first letter</b><br><br>"
        "During <b>matching</b>, each <b>source</b> will search for the <b>most similar choice</b> among <b>choices</b> that start with the same letter only. This decreases greatly the processing time during <b>matching</b>."
        "</ul>"
        "<h3>Available actions on <b>source</b> items</h3>"
        "<p>From the context menu on each <b>source</b> item in the main list, the following actions are available:"
        "<ul>"
        "<li><b>Delete source file(s)</b><br><br>"
        "Delete the file associated with the selected <b>source</b> string."
        "<br><li><b>Reset choice</b><br><br>"
        "Reset the <b>choice</b>."
        "<br><li><b>Pick a match...</b><br><br>"
        "Change the <b>choice</b> by typing your own from the available <b>choices</b>."
        "<br><li><b>Alternate match</b><br><br>"
        "Change the <b>choice</b> by chosing one of the 10 best <b>choices</b> sorted by similarity score."
        "</ul>"
        "<h3>Sessions management</h3>"
        "<p>The current list of <b>sources</b> and <b>choices</b> as well as the current <b>most similar choice</b> can be saved to a file by using <code><b>File->Save Session</b></code>.</p>"
        "<p>A saved session is restored by using <code><b>File->Load Session</b></code>. When restoring a session, the current list of sources and choices is resetted first.</p>"
        "<p>The list of the 8 most recent saved session files can be loaded directly from the <code><b>File</b></code> menu.</p>"
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

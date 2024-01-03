import os
import os.path
import sys
import wx
import wx.lib.mixins.listctrl as listmix
from functools import partial
from pathlib import Path

from pyfuzzyrenamer import config, filters, main_dlg, icons, masks, match, utils
from pyfuzzyrenamer.config import get_config
from wxautocompletectrl.wxautocompletectrl import AutocompleteTextCtrl


def list_completer(a_list):
    def completer(query):
        formatted, unformatted = list(), list()
        if query:
            unformatted = [item for item in a_list if query.lower() in item.lower()]
            for item in unformatted:
                s = item.lower().find(query.lower())
                formatted.append("%s<b><u>%s</b></u>%s" % (item[:s], query, item[s + len(query) :]))

        return formatted, unformatted

    return completer


class PickCandidate(wx.MiniFrame):
    def __init__(self, parent, row_id, position, selectNextOnClose = False):
        wx.MiniFrame.__init__(self, parent, title="", pos=position, style=wx.RESIZE_BORDER)
        self.lst_c = [masks.FileMasked(w.file, useFilter=False).masked[1] for v in main_dlg.candidates["all"].values() for w in v]
        self.text = AutocompleteTextCtrl(self, size=(400, -1), completer=list_completer(self.lst_c))
        self.text.SetMinSize((400, -1))
        self.row_id = row_id
        self.selectNextOnClose = selectNextOnClose
        self.firstLose = False
        panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        panel_sizer.Add(self.text, 1, wx.EXPAND | wx.ALL, 0)
        self.SetSizerAndFit(panel_sizer)
        size = self.GetSize()
        self.SetSizeHints(minW=size.GetWidth(), minH=size.GetHeight(), maxH=size.GetHeight())
        self.Bind(wx.EVT_CHAR_HOOK, self.OnKeyUP)
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        self.text.Bind(wx.EVT_KILL_FOCUS, self.OnLoseFocus)
        self.text.Bind(wx.EVT_TEXT_ENTER, self.OnEnter)

    def OnLoseFocus(self, event):
        if not self.firstLose:
            self.firstLose = True
        else:
            self.OnCloseWindow(None)
            if self.selectNextOnClose:
                # Select next item
                list_ctrl = self.GetParent()
                list_ctrl.Select(self.row_id, on=False)
                list_ctrl.Select(self.row_id + 1, on=True)
                list_ctrl.Focus(self.row_id + 1)
                list_ctrl.EnsureVisible(self.row_id + 1)

    def OnCloseWindow(self, event):
        self.Destroy()

    def OnKeyUP(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_ESCAPE:
            self.selectNextOnClose = False
            self.Close(True)
        if keycode:
            event.Skip()

    def OnEnter(self, event):
        Qinput_as_path = get_config()["input_as_path"]
        forced_match = self.text.GetLineText(0).strip()
        input_filter = Path(forced_match) if Qinput_as_path else forced_match
        item = filters.FileFiltered(input_filter, alreadyStem=True)
        matching_results = main_dlg.candidates["all"][item.filtered]
        idx_file = -1
        for i in range(len(matching_results)):
            matched_file = matching_results[i].file.stem if Qinput_as_path else matching_results[i].file
            if matched_file == forced_match:
                    idx_file = i
                    break
        
        list_ctrl = self.GetParent()
        list_ctrl.MenuForceMatchCb(self.row_id, item.filtered, idx_file, None)
        if self.selectNextOnClose:
            # Select next item
            list_ctrl.Select(self.row_id, on=False)
            list_ctrl.Select(self.row_id + 1, on=True)
            list_ctrl.Focus(self.row_id + 1)
            list_ctrl.EnsureVisible(self.row_id + 1)
        self.Close(True)


class FuzzyRenamerListCtrl(wx.ListCtrl, listmix.ColumnSorterMixin):
    def __init__(self, parent, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, pos=pos, size=size, style=style)
        listmix.ColumnSorterMixin.__init__(self, len(config.default_columns))
        self.EnableCheckBoxes()
        self.Bind(wx.EVT_CHAR, self.onKeyPress)
        self.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnBeginLabelEdit)
        self.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnEndLabelEdit)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.ItemRightClickCb)
        self.Bind(wx.EVT_LIST_COL_RIGHT_CLICK, self.ColRightClickCb)
        self.Bind(wx.EVT_LIST_ITEM_CHECKED, self.CheckedCb)
        self.Bind(wx.EVT_LIST_ITEM_UNCHECKED, self.UncheckedCb)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.SelectCb)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.UnselectCb)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnDoubleClick)

        for col in range(0, len(config.default_columns)):
            self.InsertColumn(
                col, config.default_columns[col]["label"], width=get_config()["col%d_size" % (col + 1)],
            )

        if self.HasColumnOrderSupport():
            order = [get_config()["col%d_order" % (col + 1)] for col in range(0, len(config.default_columns))]
            self.SetColumnsOrder(order)

        imagelist = wx.ImageList(16, 16)
        self.img_red = imagelist.Add(icons.RedSquare_16_PNG.GetBitmap())
        self.img_yellow = imagelist.Add(icons.YellowSquare_16_PNG.GetBitmap())
        self.img_orange = imagelist.Add(icons.OrangeSquare_16_PNG.GetBitmap())
        self.img_green = imagelist.Add(icons.GreenSquare_16_PNG.GetBitmap())
        self.img_downarrow = imagelist.Add(icons.DownArrow_16_PNG.GetBitmap())
        self.img_uparrow = imagelist.Add(icons.UpArrow_16_PNG.GetBitmap())

        self.AssignImageList(imagelist, wx.IMAGE_LIST_SMALL)
            
        self.listdata = {}
        self.listdataname = {}
        self.listdatanameinv = {}
        self.itemDataMap = self.listdata

    def onKeyPress(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_SPACE:
            if self.GetSelectedItemCount() > 1:
                selected = utils.get_selected_items(self)
                focused = utils.get_focused_items(self)
                check = (
                    not self.IsItemChecked(selected[0]) if (not selected[0] in focused) else self.IsItemChecked(selected[0])
                )
                for index in selected:
                    #self.Focus(index)
                    if not index in focused:
                        self.CheckItem(index, check)
                for index in focused:
                    if not index in selected:
                        self.CheckItem(index, not check)
                event.Skip()
            elif self.GetSelectedItemCount() == 1:
                # Select next item
                row_id = self.GetFirstSelected()
                self.CheckItem(row_id, self.IsItemChecked(row_id))
                self.Select(row_id, on=False)
                self.Select(row_id + 1, on=True)
                self.Focus(row_id + 1)
                self.EnsureVisible(row_id + 1)
        elif keycode == wx.WXK_F2:
            if self.GetSelectedItemCount() == 1:
                index = self.GetFirstSelected()
                self.EditLabel(index)
            event.Skip()
        elif keycode == wx.WXK_CONTROL_A:
            self.Freeze()
            item = -1
            while 1:
                item = self.GetNextItem(item)
                if item == -1:
                    break
                self.SetItemState(item, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
            self.Thaw()
            event.Skip()
        elif keycode == wx.WXK_DELETE:
            if event.GetModifiers() == wx.MOD_SHIFT:
                self.DeleteSelectionCb(None)
            else:
                selected = utils.get_selected_items(self)

                selected.reverse()  # Delete all the items, starting with the last item
                self.Freeze()
                for row_id in selected:
                    pos = self.GetItemData(row_id)  # 0-based unsorted index
                    self.DeleteItem(row_id)
                    del self.listdata[pos]
                    key = self.listdatanameinv[pos]
                    del self.listdatanameinv[pos]
                    del self.listdataname[key]
                self.Thaw()
            event.Skip()
        elif keycode == wx.WXK_CONTROL_V:
            files = utils.ClipBoardFiles(get_config()["input_as_path"])
            if files:
                paste_default = get_config()["paste_forced"]
                if not paste_default:
                    dlg = wx.RichMessageDialog(
                        self.GetParent().GetParent(),
                        "Add the files to source or choice list?",
                        "Paste question",
                        wx.YES_NO | wx.ICON_QUESTION,
                    )
                    dlg.SetYesNoLabels("Sources", "Choices")
                    dlg.ShowCheckBox("Remember my choice")
                    Qsources = dlg.ShowModal() == wx.ID_YES
                    if dlg.IsCheckBoxChecked():
                        get_config()["paste_forced"] = 1 if Qsources else 2
                        self.GetParent().GetParent().GetParent().GetParent().mnu_source_from_clipboard_default.Check(Qsources)
                        self.GetParent().GetParent().GetParent().GetParent().mnu_choices_from_clipboard_default.Check(not Qsources)
                    dlg.Destroy()
                else:
                    Qsources = (paste_default == 1)
                if Qsources:
                    self.GetParent().GetParent().GetParent().AddSourcesFromFiles(files)
                else:
                    self.GetParent().GetParent().GetParent().AddChoicesFromFiles(files)
            event.Skip()
        elif keycode == wx.WXK_CONTROL_P:
            if self.GetSelectedItemCount() == 1:
                row_id = self.GetFirstSelected()
                pos_column_match = 0
                for i in self.GetColumnsOrder() if self.HasColumnOrderSupport() else range(0, len(config.default_columns)):
                    if i == 2:
                        break
                    pos_column_match += self.GetColumnWidth(i)
                rect = self.GetItemRect(row_id)
                position = self.ClientToScreen(rect.GetPosition())
                dia = PickCandidate(self, row_id, wx.Point(position.x + pos_column_match, position.y), selectNextOnClose=True)
                dia.Show()
                dia.text.SetFocus()
        elif keycode == wx.WXK_CONTROL_R:
            self.NoMatchSelectionCb(None)
            if self.GetSelectedItemCount() == 1:
                # Select next item
                row_id = self.GetFirstSelected()
                self.Select(row_id, on=False)
                self.Select(row_id + 1, on=True)
                self.Focus(row_id + 1)
                self.EnsureVisible(row_id + 1)
            event.Skip()
        elif keycode == wx.WXK_CONTROL_B:
            self.ReMatchSelectionCb(None)
            if self.GetSelectedItemCount() == 1:
                # Select next item
                row_id = self.GetFirstSelected()
                self.Select(row_id, on=False)
                self.Select(row_id + 1, on=True)
                self.Focus(row_id + 1)
                self.EnsureVisible(row_id + 1)
            event.Skip()
        elif keycode == wx.WXK_RETURN:
            selected = utils.get_selected_items(self)
            for row_id in selected:
                pos = self.GetItemData(row_id)  # 0-based unsorted index
                data = self.listdata[pos]
                filename_path = data[config.D_FILENAME]
                utils.open_file(str(filename_path[0]))
            event.Skip()
        elif keycode:
            event.Skip()

    def ColRightClickCb(self, event):
        menu = wx.Menu()
        for col in range(0, self.GetColumnCount()):
            mnu_col = menu.AppendCheckItem(col, self.GetColumn(col).GetText())
            mnu_col.Check(self.GetColumnWidth(col) > 0)
            self.Bind(wx.EVT_MENU, partial(self.MenuColumnCb, col), mnu_col)
        self.PopupMenu(menu, event.GetPoint())
        menu.Destroy()

    def MenuColumnCb(self, col, event):
        if event.IsChecked():
            self.SetColumnWidth(col, config.default_columns[col]["width"])
        else:
            self.SetColumnWidth(col, 0)

    def ItemRightClickCb(self, event):
        if not self.GetSelectedItemCount():
            return
        menu = wx.Menu()
        mnu_nomatch = wx.MenuItem(menu, wx.ID_ANY, "&Reset choice\tCtrl+R", "Reset choice")
        mnu_nomatch.SetBitmap(icons.NoMatch_16_PNG.GetBitmap())
        mnu_rematch = wx.MenuItem(menu, wx.ID_ANY, "&Best choice\tCtrl+B", "Best choice")
        mnu_rematch.SetBitmap(icons.ProcessMatch_16_PNG.GetBitmap())
        
        # Add access to file deletion if applicable
        if get_config()["input_as_path"]: 
            mnu_delete = wx.MenuItem(menu, wx.ID_ANY, "&Delete source file(s)\tShift+Del", "Delete source file(s)")
            mnu_delete.SetBitmap(icons.Delete_16_PNG.GetBitmap())
            menu.Append(mnu_delete)
            self.Bind(wx.EVT_MENU, self.DeleteSelectionCb, mnu_delete)

        menu.Append(mnu_nomatch)
        menu.Append(mnu_rematch)

        self.Bind(wx.EVT_MENU, self.NoMatchSelectionCb, mnu_nomatch)
        self.Bind(wx.EVT_MENU, self.ReMatchSelectionCb, mnu_rematch)

        # Add access to file launch/explorer if applicable
        if get_config()["input_as_path"] and sys.platform.startswith('win32'):
            mnu_open_source_explorer = wx.MenuItem(menu, wx.ID_ANY, "&Select source file(s) in Explorer", "Select source file(s) in Explorer")
            mnu_open_match_explorer = wx.MenuItem(menu, wx.ID_ANY, "Select &matched file(s) in Explorer", "Select matched file(s) in Explorer")
            menu.Append(mnu_open_source_explorer)
            menu.Append(mnu_open_match_explorer)
            self.Bind(wx.EVT_MENU, self.OpenSourceExplorerCb, mnu_open_source_explorer)
            self.Bind(wx.EVT_MENU, self.OpenMatchExplorerCb, mnu_open_match_explorer)

        if self.GetSelectedItemCount() == 1 and main_dlg.candidates:
            row_id = event.GetIndex()
            mnu_search = wx.MenuItem(menu, wx.ID_ANY, "&Pick a match...\tCtrl+P", "Pick a match")
            mnu_search.SetBitmap(icons.ProcessMatch_16_PNG.GetBitmap())
            menu.Append(mnu_search)
            self.Bind(
                wx.EVT_MENU, partial(self.SearchSelectionCb, row_id, self.ClientToScreen(event.GetPoint()),), mnu_search,
            )

            pos = self.GetItemData(row_id)  # 0-based unsorted index
            matches = match.get_match(self.listdata[pos][config.D_FILENAME])
            # [{"key": candidate_key_1, "candidates": [...], "score":score1}, {"key": candidate_key_2: "candidates": [...], "score":score2}, ...]
            if matches:
                menu.AppendSeparator()
                for match_ in matches:
                    for idx_file in range(len(match_["candidates"])):
                        f_masked = masks.FileMasked(match_["candidates"][idx_file], useFilter=False)
                        mnu_match = menu.Append(wx.ID_ANY, "[%d%%] %s" % (match_["score"], f_masked.masked[1]))
                        self.Bind(
                            wx.EVT_MENU, partial(self.MenuForceMatchCb, row_id, match_["key"], idx_file), mnu_match,
                        )

        self.PopupMenu(menu, event.GetPoint())
        menu.Destroy()

    def CheckedCb(self, event):
        row_id = event.GetIndex()
        f = self.GetItemFont(row_id)
        if not f.IsOk():
            f = self.GetFont()
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        font.SetStyle(wx.FONTSTYLE_NORMAL)
        font.SetWeight(f.GetWeight())
        self.SetItemFont(row_id, font)
        pos = self.GetItemData(row_id)  # 0-based unsorted index
        self.listdata[pos][config.D_CHECKED] = True
        self.SetItem(row_id, config.D_CHECKED, str(self.listdata[pos][config.D_CHECKED]))

    def UncheckedCb(self, event):
        row_id = event.GetIndex()
        f = self.GetItemFont(row_id)
        if not f.IsOk():
            f = self.GetFont()
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        font.SetStyle(wx.FONTSTYLE_ITALIC)
        font.SetWeight(f.GetWeight())
        self.SetItemFont(row_id, font)
        pos = self.GetItemData(row_id)  # 0-based unsorted index
        self.listdata[pos][config.D_CHECKED] = False
        self.SetItem(row_id, config.D_CHECKED, str(self.listdata[pos][config.D_CHECKED]))

    def SelectCb(self, event):
        nb = self.GetSelectedItemCount()
        self.currentItem = event.GetIndex()
        if nb:
            self.GetParent().GetParent().GetParent().GetParent().statusbar.SetStatusText(
                "%d item(s) selected" % self.GetSelectedItemCount(), 1
            )
        else:
            self.GetParent().GetParent().GetParent().GetParent().statusbar.SetStatusText("", 1)

    def UnselectCb(self, event):
        nb = self.GetSelectedItemCount()
        if nb:
            self.GetParent().GetParent().GetParent().GetParent().statusbar.SetStatusText(
                "%d item(s) selected" % self.GetSelectedItemCount(), 1
            )
        else:
            self.GetParent().GetParent().GetParent().GetParent().statusbar.SetStatusText("", 1)

    def SearchSelectionCb(self, row_id, position, event):
        dia = PickCandidate(self, row_id, position)
        dia.Show()
        dia.text.SetFocus()

    def DeleteSelectionCb(self, event):
        # File deletion not applicable if inputs are not path
        if not get_config()["input_as_path"]:
            return
            
        selected = utils.get_selected_items(self)
        selected.reverse()  # Delete all the items + source file, starting with the last item
        self.Freeze()
        for row_id in selected:
            pos = self.GetItemData(row_id)  # 0-based unsorted index
            for f in self.listdata[pos][config.D_FILENAME]:
                if f.is_file():
                    fpath = str(f)
                    try:
                        os.remove(fpath)
                        wx.LogMessage("Deleting : %s" % (fpath))
                    except (OSError, IOError):
                        wx.LogMessage("Error when deleting : %s" % (fpath))
            self.DeleteItem(row_id)
            del self.listdata[pos]
            key = self.listdatanameinv[pos]
            del self.listdatanameinv[pos]
            del self.listdataname[key]
        self.Thaw()

    def NoMatchSelectionCb(self, event):
        Qview_fullpath = get_config()["show_fullpath"]
        Qhide_extension = get_config()["hide_extension"]
        selected = utils.get_selected_items(self)
        self.Freeze()
        for row_id in selected:
            self.RefreshItem(
                row_id,
                score=0,
                matchnames=[],
                nbmatch=0,
                status=config.MatchStatus.NONE,
                Qview_fullpath=Qview_fullpath,
                Qhide_extension=Qhide_extension,
            )
            f = self.GetItemFont(row_id)
            if not f.IsOk():
                f = self.list_ctrl.GetFont()
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            font.SetWeight(wx.FONTWEIGHT_NORMAL)
            font.SetStyle(f.GetStyle())
            self.SetItemFont(row_id, font)
        self.Thaw()

    def ReMatchSelectionCb(self, event):
        selected = utils.get_selected_items(self)

        sources = []
        for row_id in selected:
            pos = self.GetItemData(row_id)  # 0-based unsorted index
            sources.append(self.listdata[pos][config.D_FILENAME])

        matches = match.get_matches(sources)

        Qview_fullpath = get_config()["show_fullpath"]
        Qhide_extension = get_config()["hide_extension"]
        count = 0
        self.Freeze()
        for row_id in selected:
            if len(matches) < count + 1:
                break
            f = self.GetItemFont(row_id)
            if not f.IsOk():
                f = self.list_ctrl.GetFont()
            font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
            font.SetWeight(wx.FONTWEIGHT_NORMAL)
            font.SetStyle(f.GetStyle())
            self.SetItemFont(row_id, font)

            if matches[count]:
                matching_results = matches[count][0]["candidates"]
                nb_match = len(matching_results)
                self.RefreshItem(
                    row_id,
                    score=matches[count][0]["score"],
                    matchnames=matching_results,
                    nbmatch=nb_match,
                    status=config.MatchStatus.MATCH,
                    Qview_fullpath=Qview_fullpath,
                    Qhide_extension=Qhide_extension,
                )
            else:
                self.RefreshItem(
                    row_id,
                    score=0,
                    matchnames=[],
                    nbmatch=0,
                    status=config.MatchStatus.NOMATCH,
                    Qview_fullpath=Qview_fullpath,
                    Qhide_extension=Qhide_extension,
                )
            count += 1
        self.Thaw()

    def MenuForceMatchCb(self, row_id, forced_match, idx_file, event):
        pos = self.GetItemData(row_id)  # 0-based unsorted index
        similarityscorer = get_config()["similarityscorer"]
        similarity = match.similarityScorers[similarityscorer](
            masks.FileMasked(self.listdata[pos][config.D_FILENAME][0]).masked[1], forced_match,
        )
        Qview_fullpath = get_config()["show_fullpath"]
        Qhide_extension = get_config()["hide_extension"]
        Qsource_w_multiple_choice = get_config()["source_w_multiple_choice"]
        if forced_match in main_dlg.candidates["all"]:
            matching_results = main_dlg.candidates["all"][forced_match]
            if Qsource_w_multiple_choice or idx_file == -1:
                nb_match = len(matching_results)
                self.RefreshItem(
                    row_id,
                    score=similarity,
                    matchnames=[result.file for result in matching_results],
                    nbmatch=nb_match,
                    status=config.MatchStatus.USRMATCH,
                    Qview_fullpath=Qview_fullpath,
                    Qhide_extension=Qhide_extension,
                )
            else:
                self.RefreshItem(
                    row_id,
                    score=similarity,
                    matchnames=[matching_results[idx_file].file],
                    nbmatch=1,
                    status=config.MatchStatus.USRMATCH,
                    Qview_fullpath=Qview_fullpath,
                    Qhide_extension=Qhide_extension,
                )
        else:
            self.RefreshItem(
                row_id,
                score=0,
                matchnames=[],
                nbmatch=0,
                status=config.MatchStatus.NOMATCH,
                Qview_fullpath=Qview_fullpath,
                Qhide_extension=Qhide_extension,
            )
        f = self.GetItemFont(row_id)
        if not f.IsOk():
            f = self.GetFont()
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        font.SetStyle(f.GetStyle())
        self.SetItemFont(row_id, font)

    def OpenSourceExplorerCb(self, event):
        # not relevant if not dealing with file path
        Qinput_as_path = get_config()["input_as_path"]
        if not Qinput_as_path:
            return
        
        pathes = []
        selected = utils.get_selected_items(self)
        for row_id in selected:
            pos = self.GetItemData(row_id)  # 0-based unsorted index
            data = self.listdata[pos]
            pathes += data[config.D_FILENAME]
        utils.launch_file_explorer(pathes)
        
    def OpenMatchExplorerCb(self, event):
        # not relevant if not dealing with file path
        Qinput_as_path = get_config()["input_as_path"]
        if not Qinput_as_path:
            return

        pathes = []
        selected = utils.get_selected_items(self)
        for row_id in selected:
            pos = self.GetItemData(row_id)  # 0-based unsorted index
            data = self.listdata[pos]
            pathes += data[config.D_MATCHNAME]
        utils.launch_file_explorer(pathes)

    def OnDoubleClick(self, event):
        # not relevant if not dealing with file path
        Qinput_as_path = get_config()["input_as_path"]
        if not Qinput_as_path:
            return

        start_match_col = 0
        end_match_col = 0
        for col in self.GetColumnsOrder() if self.HasColumnOrderSupport() else range(0, len(config.default_columns)):
            end_match_col += self.GetColumnWidth(col)
            if col == 2:
                break
            start_match_col = end_match_col
        start_source_col = 0
        end_source_col = 0
        for col in self.GetColumnsOrder() if self.HasColumnOrderSupport() else range(0, len(config.default_columns)):
            end_source_col += self.GetColumnWidth(col)
            if col == 0:
                break
            start_source_col = end_source_col

        row_id = self.currentItem
        pos = self.GetItemData(row_id)  # 0-based unsorted index
        data = self.listdata[pos]
        mouse_pos = wx.GetMousePosition()
        position = self.ScreenToClient(mouse_pos)
        if position.x >= start_source_col and position.x <= end_source_col:
            filename_path = data[config.D_FILENAME]
            utils.open_file(str(filename_path[0]))
        elif position.x >= start_match_col and position.x <= end_match_col:
            matchname = data[config.D_MATCHNAME]
            utils.open_file(str(matchname[0]))

    def OnBeginLabelEdit(self, event):
        start_match_col = 0
        end_match_col = 0
        for col in self.GetColumnsOrder() if self.HasColumnOrderSupport() else range(0, len(config.default_columns)):
            end_match_col += self.GetColumnWidth(col)
            if col == 2:
                break
            start_match_col = end_match_col

        mouse_pos = wx.GetMousePosition()
        position = self.ScreenToClient(mouse_pos)
        if position.x >= start_match_col and position.x <= end_match_col:
            event.Veto()
            row_id = event.GetIndex()
            dia = PickCandidate(self, row_id, wx.Point(mouse_pos.x - 10, mouse_pos.y - 20), selectNextOnClose=True)
            dia.Show()
            dia.text.SetFocus()
        else:
            event.Allow()
            Qinput_as_path = get_config()["input_as_path"]
            if Qinput_as_path:
                if get_config()["show_fullpath"]:
                    d = Path(event.GetLabel()).name
                else:
                    d = event.GetLabel()
                (self.GetEditControl()).SetValue(d)
                if not get_config()["hide_extension"]:
                    index_of_dot = d.rfind('.')
                    if index_of_dot > 0:
                        (self.GetEditControl()).SetSelection(0, index_of_dot)

    def OnEndLabelEdit(self, event):
        if event.IsEditCancelled() or not event.GetLabel():
            event.Veto()
            return
        Qinput_as_path = get_config()["input_as_path"]
        row_id = event.GetIndex()
        pos = self.GetItemData(row_id)  # 0-based unsorted index
        new_name = event.GetLabel()
        old_path = self.listdata[pos][config.D_FILENAME]
        if Qinput_as_path:
            old_name = old_path.name
            new_name_clean = utils.strip_extra_whitespace(utils.strip_illegal_chars(new_name))
        else:
            old_name = old_path
            new_name_clean = utils.strip_extra_whitespace(new_name)

        event.Veto()  # do not allow further process as we will edit ourself the item label

        if new_name_clean == old_name:
            return
        old_file = str(old_path)
        if Qinput_as_path:
            new_file = os.path.join(str(old_path.parent), new_name_clean)
            new_path = Path(new_file)
        else:
            new_file = new_name_clean
            new_path = new_file

        try:
            if Qinput_as_path:
                if not old_path.is_file():
                    return
                os.rename(old_file, new_file)
                wx.LogMessage("Renaming : %s --> %s" % (old_file, new_file))

            Qview_fullpath = get_config()["show_fullpath"]
            Qhide_extension = get_config()["hide_extension"]

            new_match = match.get_match(new_path)
            if new_match:
                matching_results = new_match[0]["candidates"]
                nb_match = len(matching_results)
                self.RefreshItem(
                    row_id,
                    score=new_match[0]["score"],
                    matchnames=matching_results,
                    nbmatch=nb_match,
                    status=config.MatchStatus.MATCH,
                    Qview_fullpath=Qview_fullpath,
                    Qhide_extension=Qhide_extension,
                )
            else:
                self.RefreshItem(
                    row_id,
                    score=0,
                    matchnames=[],
                    nbmatch=0,
                    status=config.MatchStatus.NOMATCH,
                    Qview_fullpath=Qview_fullpath,
                    Qhide_extension=Qhide_extension,
                )
        except (OSError, IOError):
            wx.LogMessage("Error when renaming : %s --> %s" % (old_file, new_file))

    def GetListCtrl(self):
        return self

    def RefreshItem(
        self,
        row_id,
        filename_path=None,
        score=None,
        matchnames=None,
        nbmatch=None,
        status=None,
        Qview_fullpath=False,
        Qhide_extension=False,
    ):
        pos = self.GetItemData(row_id)  # 0-based unsorted index
        data = self.listdata[pos]

        if filename_path is None:
            filename_path = data[config.D_FILENAME]
        else:
            data[config.D_FILENAME] = filename_path
        if score is None:
            score = data[config.D_MATCH_SCORE]
        else:
            data[config.D_MATCH_SCORE] = score
        if matchnames is None:
            matchnames = data[config.D_MATCHNAME]
        else:
            data[config.D_MATCHNAME] = matchnames
        if nbmatch is None:
            nbmatch = data[config.D_NBMATCH]
        else:
            data[config.D_NBMATCH] = nbmatch
        if status is None:
            status = data[config.D_STATUS]
        else:
            data[config.D_STATUS] = status

        data[config.D_PREVIEW] = main_dlg.getRenamePreview(filename_path, matchnames)
        parent, stem, suffix = utils.GetFileParentStemAndSuffix(filename_path[0])
        if len(filename_path) > 1:
            stem = masks.getmergedprepost(filename_path)
        self.SetItem(
            row_id,
            config.D_FILENAME,
            parent + stem + suffix if Qview_fullpath else (stem if Qhide_extension else stem + suffix),self.colorFromScore(score)
        )
        self.SetItem(row_id, config.D_STATUS, str(status))
        self.SetItem(row_id, config.D_CHECKED, str(data[config.D_CHECKED]))
        if data[config.D_NBMATCH]:
            self.SetItem(row_id, config.D_MATCH_SCORE, str(score))
            parent, stem, suffix = utils.GetFileParentStemAndSuffix(matchnames[0])
            if data[config.D_NBMATCH] > 1:
                stem = masks.getmergedprepost(matchnames)
            self.SetItem(
                row_id,
                config.D_MATCHNAME,
                parent + stem + suffix if Qview_fullpath else (stem if Qhide_extension else stem + suffix),
            )
            previews = [y for p in data[config.D_PREVIEW] for y in p]
            if previews:
                parent, stem, suffix = utils.GetFileParentStemAndSuffix(previews[0])
                if len(previews) > 1:
                    stem = masks.getmergedprepost(previews)
                self.SetItem(
                    row_id,
                    config.D_PREVIEW,
                    parent + stem + suffix if Qview_fullpath else (stem if Qhide_extension else stem + suffix),
                )
            self.SetItem(row_id, config.D_NBMATCH, str(nbmatch))
        else:
            self.SetItemImage(row_id, -1)
            self.SetItem(row_id, config.D_MATCH_SCORE, "")
            self.SetItem(row_id, config.D_MATCHNAME, "")
            self.SetItem(row_id, config.D_PREVIEW, "")
            self.SetItem(row_id, config.D_NBMATCH, "")

    def colorFromScore(self, score):
        if score == 100:
            return self.img_green
        if score >= 95:
            return self.img_yellow
        elif score >= 90:
            return self.img_orange
        return self.img_red
    
    def RefreshList(self):
        Qview_fullpath = get_config()["show_fullpath"]
        Qhide_extension = get_config()["hide_extension"]

        self.Freeze()
        row_id = -1
        while True:
            row_id = self.GetNextItem(row_id)
            if row_id == -1:
                break
            self.RefreshItem(row_id, Qview_fullpath=Qview_fullpath, Qhide_extension=Qhide_extension)
        self.Thaw()

    # Add source to the list,
    # Return Row Ids for new items
    def AddToList(self, newdata):
        Qview_fullpath = get_config()["show_fullpath"]
        Qhide_extension = get_config()["hide_extension"]
        Qbest_auto = get_config()["best_auto"]
        Qinput_as_path = get_config()["input_as_path"]

        index = 0 if not self.listdata else sorted(self.listdata.keys())[-1] + 1  # start indexing after max index
        row_id = self.GetItemCount()
        row_ids_to_match = set()
        row_ids_to_return = set()
        
        self.Freeze()
        for f in newdata:

            key = masks.FileMasked(f, useFilter=False).masked[1]
            if key in self.listdataname:
                pos = self.listdataname[key]
                row_id0 = self.FindItem(-1, pos)
                if row_id0 != -1:
                    row_ids_to_return.add(row_id0)
                    if not f in self.listdata[pos][config.D_FILENAME]:
                        self.listdata[pos][config.D_FILENAME].append(f)
                        self.RefreshItem(row_id0, Qview_fullpath=Qview_fullpath, Qhide_extension=Qhide_extension)
                        row_ids_to_match.add(row_id0)
            else:
                # Treat duplicate file
                stem, suffix = utils.GetFileStemAndSuffix(f)
                item_name = str(f) if (Qview_fullpath or not Qinput_as_path) else (stem if Qhide_extension else f.name)
                found = self.FindItem(-1, item_name)
                if found != -1:
                    row_ids_to_return.add(found)
                    continue

                self.listdataname[key] = index
                self.listdatanameinv[index] = key
                self.listdata[index] = [[f], 0, [], [], 0, config.MatchStatus.NONE, True]
                self.InsertItem(row_id, item_name, -1)
                self.SetItemData(row_id, index)
                self.RefreshItem(row_id, Qview_fullpath=Qview_fullpath, Qhide_extension=Qhide_extension)
                self.CheckItem(row_id, True)
                row_ids_to_match.add(row_id)
                row_ids_to_return.add(row_id)
                row_id += 1
                index += 1

        if row_ids_to_match:
            self.EnsureVisible(max(row_ids_to_match))

        # Automatically find best match
        if Qbest_auto:

            sources = []
            for row_id in row_ids_to_match:  # loop all the added items
                pos = self.GetItemData(row_id)  # 0-based unsorted index
                sources.append(self.listdata[pos][config.D_FILENAME])

            matches = match.get_matches(sources)

            count = 0
            for row_id in row_ids_to_match:  # loop all the added items
                if len(matches) < count + 1:
                    break
                f = self.GetItemFont(row_id)
                if not f.IsOk():
                    f = self.GetFont()
                font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
                font.SetWeight(wx.FONTWEIGHT_NORMAL)
                font.SetStyle(f.GetStyle())
                self.SetItemFont(row_id, font)

                if matches[count]:
                    pos = self.GetItemData(row_id)  # 0-based unsorted index
                    source = self.listdata[pos][config.D_FILENAME]
                    nb_source = len(source)
                    matching_results = matches[count][0]["candidates"]
                    nb_match = len(matching_results)
                    self.RefreshItem(
                        row_id,
                        score=matches[count][0]["score"],
                        matchnames=matching_results,
                        nbmatch=nb_match,
                        status=config.MatchStatus.MATCH,
                        Qview_fullpath=Qview_fullpath,
                        Qhide_extension=Qhide_extension,
                    )
                elif matches[count] is not None:
                    self.RefreshItem(
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
        self.Thaw()
        wx.LogMessage("Sources : %d" % self.GetItemCount())
        return row_ids_to_return

    def OnSortOrderChanged(self):
        row_id = self.GetFirstSelected()
        if row_id != -1:
            self.EnsureVisible(row_id)
        col_sorted, sort_type = self.GetSortState()
        for col in range(0, len(config.default_columns)):
            self.SetColumnImage(col, -1)
        self.SetColumnImage(col_sorted, self.img_uparrow if sort_type else self.img_downarrow)

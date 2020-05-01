import os
import os.path
import wx
import wx.lib.mixins.listctrl as listmix
from functools import partial
from pathlib import Path

from pyfuzzyrenamer import config, filters, main_dlg, icons, masks, match, utils


class PickCandidate(wx.MiniFrame):
    def __init__(self, parent, row_id, position):
        wx.MiniFrame.__init__(
            self, parent, title="", pos=position, style=wx.RESIZE_BORDER
        )
        self.text = wx.TextCtrl(self, size=(100, -1), style=wx.TE_PROCESS_ENTER)
        self.text.SetMinSize((200, -1))
        self.row_id = row_id
        panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
        panel_sizer.Add(self.text, 1, wx.EXPAND | wx.ALL, 0)
        self.SetSizerAndFit(panel_sizer)
        size = self.GetSize()
        self.SetSizeHints(
            minW=size.GetWidth(), minH=size.GetHeight(), maxH=size.GetHeight()
        )
        self.Bind(wx.EVT_CHAR_HOOK, self.OnKeyUP)
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
        self.text.Bind(wx.EVT_TEXT_ENTER, self.OnEnter)
        self.text.AutoComplete(CandidateCompleter())
        self.MakeModal()

    def OnCloseWindow(self, event):
        self.MakeModal(False)
        self.Destroy()

    def OnKeyUP(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_ESCAPE:
            self.Close(True)
        if keycode:
            event.Skip()

    def OnEnter(self, event):
        val = self.text.GetLineText(0).strip()
        for item in main_dlg.candidates["all"]:
            if item.file.name == val:
                list_ctrl = self.GetParent()
                forced_match = item.file
                pos = list_ctrl.GetItemData(self.row_id)  # 0-based unsorted index
                similarity = match.mySimilarityScorer(
                    masks.FileMasked(list_ctrl.listdata[pos][config.D_FILENAME]).masked[
                        1
                    ],
                    filters.FileFiltered(forced_match).filtered,
                )
                list_ctrl.listdata[pos][config.D_MATCH_SCORE] = similarity
                list_ctrl.listdata[pos][config.D_MATCHNAME] = forced_match
                list_ctrl.listdata[pos][config.D_PREVIEW] = main_dlg.getRenamePreview(
                    list_ctrl.listdata[pos][config.D_FILENAME], forced_match
                )
                list_ctrl.listdata[pos][config.D_STATUS] = "User choice"

                Qview_fullpath = config.theConfig["show_fullpath"]
                Qhide_extension = config.theConfig["hide_extension"]
                list_ctrl.SetItem(
                    self.row_id,
                    config.D_MATCH_SCORE,
                    str(list_ctrl.listdata[pos][config.D_MATCH_SCORE]),
                )
                stem, suffix = utils.GetFileStemAndSuffix(
                    list_ctrl.listdata[pos][config.D_MATCHNAME]
                )
                list_ctrl.SetItem(
                    self.row_id,
                    config.D_MATCHNAME,
                    str(list_ctrl.listdata[pos][config.D_MATCHNAME])
                    if Qview_fullpath
                    else (
                        stem
                        if Qhide_extension
                        else list_ctrl.listdata[pos][config.D_MATCHNAME].name
                    ),
                )
                stem, suffix = utils.GetFileStemAndSuffix(
                    list_ctrl.listdata[pos][config.D_PREVIEW]
                )
                list_ctrl.SetItem(
                    self.row_id,
                    config.D_PREVIEW,
                    str(list_ctrl.listdata[pos][config.D_PREVIEW])
                    if Qview_fullpath
                    else (
                        stem
                        if Qhide_extension
                        else list_ctrl.listdata[pos][config.D_PREVIEW].name
                    ),
                )
                list_ctrl.SetItem(
                    self.row_id,
                    config.D_STATUS,
                    str(list_ctrl.listdata[pos][config.D_STATUS]),
                )

                f = list_ctrl.GetItemFont(self.row_id)
                if not f.IsOk():
                    f = list_ctrl.GetFont()
                font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
                font.SetWeight(wx.FONTWEIGHT_BOLD)
                font.SetStyle(f.GetStyle())
                list_ctrl.SetItemFont(self.row_id, font)

        self.Close(True)

    def MakeModal(self, modal=True):
        if modal and not hasattr(self, "_disabler"):
            self._disabler = wx.WindowDisabler(self)
        if not modal and hasattr(self, "_disabler"):
            del self._disabler


class CandidateCompleter(wx.TextCompleter):
    def __init__(self):
        wx.TextCompleter.__init__(self)
        self._iLastReturned = wx.NOT_FOUND
        self._sPrefix = ""
        self.possibleValues = main_dlg.candidates["all"]
        self.lcPossibleValues = [
            x.file.name.lower() for x in main_dlg.candidates["all"]
        ]

    def Start(self, prefix):
        self._sPrefix = prefix.lower()
        self._iLastReturned = wx.NOT_FOUND
        for index, item in enumerate(self.lcPossibleValues):
            if item.startswith(self._sPrefix):
                self._iLastReturned = index
                return True
        # Nothing found
        return False

    def GetNext(self):
        for i in range(self._iLastReturned, len(self.lcPossibleValues)):
            if self.lcPossibleValues[i].startswith(self._sPrefix):
                self._iLastReturned = i + 1
                return self.possibleValues[i].file.name
        # No more corresponding item
        return ""


class FuzzyRenamerListCtrl(wx.ListCtrl, listmix.ColumnSorterMixin):
    def __init__(self, parent, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, pos=pos, size=size, style=style)
        listmix.ColumnSorterMixin.__init__(self, 6)
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

        for col in range(0, len(config.default_columns)):
            self.InsertColumn(
                col,
                config.default_columns[col][2],
                width=config.theConfig["col%d_size" % (col + 1)],
            )

        if self.HasColumnOrderSupport():
            order = [
                config.theConfig["col%d_order" % (col + 1)]
                for col in range(0, len(config.default_columns))
            ]
            self.SetColumnsOrder(order)

        self.listdata = {}
        self.itemDataMap = self.listdata

    def onKeyPress(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_SPACE:
            if self.GetSelectedItemCount() > 1:
                index = self.GetFirstSelected()
                second = self.GetNextSelected(index)
                check = not self.IsItemChecked(second)
                while index != -1:
                    self.CheckItem(index, check)
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
            selected = utils.get_selected_items(self)

            selected.reverse()  # Delete all the items, starting with the last item
            for row_id in selected:
                pos = self.GetItemData(row_id)  # 0-based unsorted index
                self.DeleteItem(row_id)
                del self.listdata[pos]
        elif keycode == wx.WXK_CONTROL_V:
            files = utils.ClipBoardFiles()
            if files:
                dlg = wx.GenericMessageDialog(
                    self.GetParent().GetParent(),
                    "Add the files to source or choice list?",
                    "Paste question",
                    wx.YES_NO | wx.ICON_QUESTION,
                )
                dlg.SetYesNoLabels("Sources", "Choices")
                Qsources = dlg.ShowModal() == wx.ID_YES
                dlg.Destroy()
                if Qsources:
                    self.GetParent().GetParent().GetParent().AddSourceFromFiles(files)
                else:
                    self.GetParent().GetParent().GetParent().AddChoicesFromFiles(files)
        elif keycode == wx.WXK_CONTROL_P:
            if self.GetSelectedItemCount() == 1:
                row_id = self.GetFirstSelected()
                pos_column_match = 0
                for i in (self.GetColumnsOrder() if self.HasColumnOrderSupport() else range(0, len(config.default_columns))):
                    if i == 2:
                        break
                    pos_column_match += self.GetColumnWidth(i)
                rect = self.GetItemRect(row_id)
                position = self.ClientToScreen(rect.GetPosition())
                dia = PickCandidate(
                    self, row_id, wx.Point(position.x + pos_column_match, position.y)
                )
                dia.Show()
                dia.text.SetFocus()
        elif keycode == wx.WXK_CONTROL_D:
            selected = utils.get_selected_items(self)

            selected.reverse()  # Delete all the items + source file, starting with the last item
            for row_id in selected:
                pos = self.GetItemData(row_id)  # 0-based unsorted index
                if self.listdata[pos][config.D_FILENAME].is_file():
                    fpath = str(self.listdata[pos][config.D_FILENAME])
                    try:
                        os.remove(fpath)
                        wx.LogMessage("Deleting : %s" % (fpath))
                    except (OSError, IOError):
                        wx.LogMessage("Error when deleting : %s" % (fpath))
                self.DeleteItem(row_id)
                del self.listdata[pos]
        elif keycode == wx.WXK_CONTROL_R:
            selected = utils.get_selected_items(self)

            for row_id in selected:
                pos = self.GetItemData(row_id)  # 0-based unsorted index
                self.listdata[pos][config.D_MATCH_SCORE] = 0
                self.listdata[pos][config.D_MATCHNAME] = Path()
                self.listdata[pos][config.D_PREVIEW] = Path()
                self.listdata[pos][config.D_STATUS] = "No match"
                self.SetItem(row_id, config.D_MATCH_SCORE, "")
                self.SetItem(row_id, config.D_MATCHNAME, "")
                self.SetItem(row_id, config.D_PREVIEW, "")
                self.SetItem(
                    row_id, config.D_STATUS, str(self.listdata[pos][config.D_STATUS]),
                )

        if keycode:
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
            self.SetColumnWidth(col, config.default_columns[col][1])
        else:
            self.SetColumnWidth(col, 0)

    def ItemRightClickCb(self, event):
        if not self.GetSelectedItemCount():
            return
        menu = wx.Menu()
        mnu_delete = wx.MenuItem(
            menu, wx.ID_ANY, "&Delete source file(s)\tCtrl+D", "Delete source file(s)"
        )
        mnu_delete.SetBitmap(icons.Delete_16_PNG.GetBitmap())
        mnu_nomatch = wx.MenuItem(
            menu, wx.ID_ANY, "&Reset choice\tCtrl+R", "Reset choice"
        )
        mnu_nomatch.SetBitmap(icons.NoMatch_16_PNG.GetBitmap())
        menu.Append(mnu_delete)
        menu.Append(mnu_nomatch)
        self.Bind(wx.EVT_MENU, self.DeleteSelectionCb, mnu_delete)
        self.Bind(wx.EVT_MENU, self.NoMatchSelectionCb, mnu_nomatch)

        if self.GetSelectedItemCount() == 1 and main_dlg.candidates:
            row_id = event.GetIndex()
            mnu_search = wx.MenuItem(
                menu, wx.ID_ANY, "&Pick a match...\tCtrl+P", "Pick a match"
            )
            mnu_search.SetBitmap(icons.ProcessMatch_16_PNG.GetBitmap())
            menu.Append(mnu_search)
            self.Bind(
                wx.EVT_MENU,
                partial(
                    self.SearchSelectionCb,
                    row_id,
                    self.ClientToScreen(event.GetPoint()),
                ),
                mnu_search,
            )

            pos = self.GetItemData(row_id)  # 0-based unsorted index
            matches = match.get_match(self.listdata[pos][config.D_FILENAME])
            if matches:
                menu.AppendSeparator()
                for match_ in matches:
                    stem, suffix = utils.GetFileStemAndSuffix(match_[0].file)
                    mnu_match = menu.Append(wx.ID_ANY, "[%d%%] %s" % (match_[1], stem))
                    self.Bind(
                        wx.EVT_MENU,
                        partial(self.MenuForceMatchCb, row_id, match_[0].file),
                        mnu_match,
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
        self.listdata[pos][config.D_CHECKED] = "True"
        self.SetItem(row_id, config.D_CHECKED, self.listdata[pos][config.D_CHECKED])

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
        self.listdata[pos][config.D_CHECKED] = "False"
        self.SetItem(row_id, config.D_CHECKED, self.listdata[pos][config.D_CHECKED])

    def SelectCb(self, event):
        nb = self.GetSelectedItemCount()
        if nb:
            self.GetParent().GetParent().GetParent().GetParent().statusbar.SetStatusText(
                "%d item(s) selected" % self.GetSelectedItemCount(), 1
            )
        else:
            self.GetParent().GetParent().GetParent().GetParent().statusbar.SetStatusText(
                "", 1
            )

    def UnselectCb(self, event):
        nb = self.GetSelectedItemCount()
        if nb:
            self.GetParent().GetParent().GetParent().GetParent().statusbar.SetStatusText(
                "%d item(s) selected" % self.GetSelectedItemCount(), 1
            )
        else:
            self.GetParent().GetParent().GetParent().GetParent().statusbar.SetStatusText(
                "", 1
            )

    def SearchSelectionCb(self, row_id, position, event):
        dia = PickCandidate(self, row_id, position)
        dia.Show()
        dia.text.SetFocus()

    def DeleteSelectionCb(self, event):
        selected = utils.get_selected_items(self)

        selected.reverse()  # Delete all the items + source file, starting with the last item
        for row_id in selected:
            pos = self.GetItemData(row_id)  # 0-based unsorted index
            if self.listdata[pos][config.D_FILENAME].is_file():
                fpath = str(self.listdata[pos][config.D_FILENAME])
                try:
                    os.remove(fpath)
                    wx.LogMessage("Deleting : %s" % (fpath))
                except (OSError, IOError):
                    wx.LogMessage("Error when deleting : %s" % (fpath))
            self.DeleteItem(row_id)
            del self.listdata[pos]

    def NoMatchSelectionCb(self, event):
        selected = utils.get_selected_items(self)

        for row_id in selected:
            pos = self.GetItemData(row_id)  # 0-based unsorted index
            self.listdata[pos][config.D_MATCH_SCORE] = 0
            self.listdata[pos][config.D_MATCHNAME] = Path()
            self.listdata[pos][config.D_PREVIEW] = Path()
            self.listdata[pos][config.D_STATUS] = "No match"
            self.SetItem(row_id, config.D_MATCH_SCORE, "")
            self.SetItem(row_id, config.D_MATCHNAME, "")
            self.SetItem(row_id, config.D_PREVIEW, "")
            self.SetItem(
                row_id, config.D_STATUS, str(self.listdata[pos][config.D_STATUS])
            )

    def MenuForceMatchCb(self, row_id, forced_match, event):
        pos = self.GetItemData(row_id)  # 0-based unsorted index
        similarity = match.mySimilarityScorer(
            masks.FileMasked(self.listdata[pos][config.D_FILENAME]).masked[1],
            filters.FileFiltered(forced_match).filtered,
        )
        self.listdata[pos][config.D_MATCH_SCORE] = similarity
        self.listdata[pos][config.D_MATCHNAME] = forced_match
        self.listdata[pos][config.D_PREVIEW] = main_dlg.getRenamePreview(
            self.listdata[pos][config.D_FILENAME], forced_match
        )
        self.listdata[pos][config.D_STATUS] = "User choice"

        Qview_fullpath = config.theConfig["show_fullpath"]
        Qhide_extension = config.theConfig["hide_extension"]
        self.SetItem(
            row_id, config.D_MATCH_SCORE, str(self.listdata[pos][config.D_MATCH_SCORE]),
        )
        stem, suffix = utils.GetFileStemAndSuffix(
            self.listdata[pos][config.D_MATCHNAME]
        )
        self.SetItem(
            row_id,
            config.D_MATCHNAME,
            str(self.listdata[pos][config.D_MATCHNAME])
            if Qview_fullpath
            else (
                stem if Qhide_extension else self.listdata[pos][config.D_MATCHNAME].name
            ),
        )
        stem, suffix = utils.GetFileStemAndSuffix(self.listdata[pos][config.D_PREVIEW])
        self.SetItem(
            row_id,
            config.D_PREVIEW,
            str(self.listdata[pos][config.D_PREVIEW])
            if Qview_fullpath
            else (
                stem if Qhide_extension else self.listdata[pos][config.D_PREVIEW].name
            ),
        )
        self.SetItem(row_id, config.D_STATUS, str(self.listdata[pos][config.D_STATUS]))

        f = self.GetItemFont(row_id)
        if not f.IsOk():
            f = self.GetFont()
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        font.SetStyle(f.GetStyle())
        self.SetItemFont(row_id, font)

    def OnBeginLabelEdit(self, event):
        start_match_col = 0
        end_match_col = 0
        for col in (self.GetColumnsOrder() if self.HasColumnOrderSupport() else range(0, len(config.default_columns))):
            end_match_col += self.GetColumnWidth(col)
            if col == 2:
                break
            start_match_col = end_match_col

        mouse_pos = wx.GetMousePosition()
        position = self.ScreenToClient(mouse_pos)
        if position.x >= start_match_col and position.x <= end_match_col:
            event.Veto()
            row_id = event.GetIndex()
            dia = PickCandidate(
                self, row_id, wx.Point(mouse_pos.x - 10, mouse_pos.y - 20)
            )
            dia.Show()
            dia.text.SetFocus()
        else:
            event.Allow()
            if config.theConfig["show_fullpath"]:
                d = Path(event.GetLabel())
                (self.GetEditControl()).SetValue(d.name)

    def OnEndLabelEdit(self, event):
        if event.IsEditCancelled() or not event.GetLabel():
            event.Veto()
            return
        row_id = event.GetIndex()
        pos = self.GetItemData(row_id)  # 0-based unsorted index
        new_name = event.GetLabel()
        old_path = self.listdata[pos][config.D_FILENAME]
        old_name = old_path.name
        new_name_clean = utils.strip_extra_whitespace(
            utils.strip_illegal_chars(new_name)
        )

        event.Veto()  # do not allow further process as we will edit ourself the item label

        if new_name_clean != old_name:
            old_file = str(old_path)
            new_file = os.path.join(str(old_path.parent), new_name_clean)
            new_path = Path(new_file)

            try:
                if old_path.is_file():
                    os.rename(old_file, new_file)
                    wx.LogMessage("Renaming : %s --> %s" % (old_file, new_file))

                    Qview_fullpath = config.theConfig["show_fullpath"]
                    Qhide_extension = config.theConfig["hide_extension"]

                    new_match = match.get_match(new_path)
                    if new_match:
                        self.listdata[pos] = [
                            new_path,
                            new_match[0][1],
                            new_match[0][0].file,
                            main_dlg.getRenamePreview(new_path, new_match[0][0].file),
                            "Matched",
                            self.listdata[pos][config.D_CHECKED],
                            old_path,
                        ]
                        self.SetItem(
                            row_id,
                            config.D_MATCH_SCORE,
                            str(self.listdata[pos][config.D_MATCH_SCORE]),
                        )
                        stem, suffix = utils.GetFileStemAndSuffix(
                            self.listdata[pos][config.D_MATCHNAME]
                        )
                        self.SetItem(
                            row_id,
                            config.D_MATCHNAME,
                            str(self.listdata[pos][config.D_MATCHNAME])
                            if Qview_fullpath
                            else (
                                stem
                                if Qhide_extension
                                else self.listdata[pos][config.D_MATCHNAME].name
                            ),
                        )
                        stem, suffix = utils.GetFileStemAndSuffix(
                            self.listdata[pos][config.D_PREVIEW]
                        )
                        self.SetItem(
                            row_id,
                            config.D_PREVIEW,
                            str(self.listdata[pos][config.D_PREVIEW])
                            if Qview_fullpath
                            else (
                                stem
                                if Qhide_extension
                                else self.listdata[pos][config.D_PREVIEW].name
                            ),
                        )
                    else:
                        self.listdata[pos] = [
                            new_path,
                            0,
                            Path(),
                            Path(),
                            "No match",
                            self.listdata[pos][config.D_CHECKED],
                            old_path,
                        ]
                        self.SetItem(row_id, config.D_MATCH_SCORE, "")
                        self.SetItem(row_id, config.D_MATCHNAME, "")
                        self.SetItem(row_id, config.D_PREVIEW, "")

                    stem, suffix = utils.GetFileStemAndSuffix(
                        self.listdata[pos][config.D_FILENAME]
                    )
                    self.SetItem(
                        row_id,
                        config.D_FILENAME,
                        str(self.listdata[pos][config.D_FILENAME])
                        if Qview_fullpath
                        else (
                            stem
                            if Qhide_extension
                            else self.listdata[pos][config.D_FILENAME].name
                        ),
                    )
                    self.SetItem(
                        row_id, config.D_STATUS, self.listdata[pos][config.D_STATUS],
                    )

            except (OSError, IOError):
                wx.LogMessage("Error when renaming : %s --> %s" % (old_file, new_file))

    def GetListCtrl(self):
        return self

    def RefreshList(self):
        Qview_fullpath = config.theConfig["show_fullpath"]
        Qhide_extension = config.theConfig["hide_extension"]

        row_id = -1
        while True:
            row_id = self.GetNextItem(row_id)
            if row_id == -1:
                break
            pos = self.GetItemData(row_id)  # 0-based unsorted index
            data = self.listdata[pos]
            filepath = str(data[config.D_FILENAME])
            stem, suffix = utils.GetFileStemAndSuffix(data[config.D_FILENAME])
            self.SetItem(
                row_id,
                config.D_FILENAME,
                filepath
                if Qview_fullpath
                else (stem if Qhide_extension else data[config.D_FILENAME].name),
            )
            self.SetItem(row_id, config.D_STATUS, str(data[config.D_STATUS]))
            if data[config.D_MATCHNAME].name:
                self.SetItem(
                    row_id, config.D_MATCH_SCORE, str(data[config.D_MATCH_SCORE])
                )
                stem, suffix = utils.GetFileStemAndSuffix(data[config.D_MATCHNAME])
                self.SetItem(
                    row_id,
                    config.D_MATCHNAME,
                    str(data[config.D_MATCHNAME])
                    if Qview_fullpath
                    else (stem if Qhide_extension else data[config.D_MATCHNAME].name),
                )
                stem, suffix = utils.GetFileStemAndSuffix(data[config.D_PREVIEW])
                self.SetItem(
                    row_id,
                    config.D_PREVIEW,
                    str(data[config.D_PREVIEW])
                    if Qview_fullpath
                    else (stem if Qhide_extension else data[config.D_PREVIEW].name),
                )
            else:
                self.SetItem(row_id, config.D_MATCH_SCORE, "")
                self.SetItem(row_id, config.D_MATCHNAME, "")
                self.SetItem(row_id, config.D_PREVIEW, "")

    def AddToList(self, newdata):
        Qview_fullpath = config.theConfig["show_fullpath"]
        Qhide_extension = config.theConfig["hide_extension"]

        index = (
            0 if not self.listdata else sorted(self.listdata.keys())[-1] + 1
        )  # start indexing after max index
        row_id = self.GetItemCount()

        for data in newdata:

            # Treat duplicate file
            stem, suffix = utils.GetFileStemAndSuffix(data[config.D_FILENAME])
            item_name = (
                str(data[config.D_FILENAME])
                if Qview_fullpath
                else (stem if Qhide_extension else data[config.D_FILENAME].name)
            )
            found = self.FindItem(-1, item_name)
            if found != -1:
                continue

            self.listdata[index] = data
            self.InsertItem(row_id, item_name)
            self.SetItem(row_id, config.D_STATUS, data[config.D_STATUS])
            self.SetItem(row_id, config.D_CHECKED, data[config.D_CHECKED])
            self.SetItemData(row_id, index)
            self.CheckItem(row_id, True)
            row_id += 1
            index += 1

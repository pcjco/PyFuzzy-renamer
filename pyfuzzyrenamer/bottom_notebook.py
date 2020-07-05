import wx
import wx.lib.agw.aui as aui
from pyfuzzyrenamer import config, utils, icons, masks
from pyfuzzyrenamer.config import get_config


class bottomNotebook(aui.AuiNotebook):
    def __init__(
        self,
        parent,
        pos=wx.DefaultPosition,
        size=wx.DefaultSize,
        style=aui.AUI_NB_BOTTOM
        | aui.AUI_NB_TAB_SPLIT
        | aui.AUI_NB_TAB_MOVE
        | aui.AUI_NB_SCROLL_BUTTONS
        | aui.AUI_NB_CLOSE_ON_ACTIVE_TAB
        | aui.AUI_NB_MIDDLE_CLICK_CLOSE,
        agwStyle=aui.AUI_NB_DEFAULT_STYLE,
    ):
        aui.AuiNotebook.__init__(self, parent, pos=pos, size=size, style=style, agwStyle=agwStyle)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.OnAuiNotebookPageClose)
        self.Bind(aui.EVT_AUINOTEBOOK_TAB_RIGHT_UP, self.OnNotebookTabRightUp)

    def __getitem__(self, index):
        if index < self.GetPageCount():
            return self.GetPage(index)
        else:
            raise IndexError

    def OnAuiNotebookPageClose(self, event):
        # prevent Log to be closed , hide it instead
        page_idx = event.GetSelection()
        if self.GetPageText(page_idx) == "Log":
            event.Veto()
            self.HidePage(page_idx, hidden=True)
            get_config()["show_log"] = False
            self.GetParent().GetParent().mnu_show_log.Check(False)

    def OnNotebookTabRightUp(self, event):
        # clear Log
        page_idx = self.GetPageIndex(self.GetCurrentPage())
        if self.GetPageText(page_idx) == "Log":
            menu = wx.Menu()
            mnu_clear = wx.MenuItem(menu, wx.ID_ANY, "&Clear log", "Clear log")
            mnu_clear.SetBitmap(icons.Delete_16_PNG.GetBitmap())
            menu.Append(mnu_clear)
            self.Bind(wx.EVT_MENU, self.ClearLog, mnu_clear)
            mouse_pos = wx.GetMousePosition()
            position = self.ScreenToClient(mouse_pos)
            self.PopupMenu(menu, wx.Point(position.x, position.y))
            menu.Destroy()

    def ClearLog(self, event):
        logTabIdx = -1
        for idx in range(0, self.GetPageCount()):
            if self.GetPageText(idx) == "Log":
                logTabIdx = idx
                break
        if logTabIdx != -1:
            log = self.GetPage(logTabIdx)
            log.log.Clear()

    def ToggleLog(self):
        logTabIdx = -1
        for idx in range(0, self.GetPageCount()):
            if self.GetPageText(idx) == "Log":
                logTabIdx = idx
                break
        # Show log tab if hidden
        if get_config()["show_log"] and logTabIdx != -1 and self.GetHidden(logTabIdx):
            self.HidePage(logTabIdx, hidden=False)
        # Hide log tab if shown
        elif not get_config()["show_log"] and logTabIdx != -1 and not self.GetHidden(logTabIdx):
            self.HidePage(logTabIdx, hidden=True)


class TabLog(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)

        self.log = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        wx.Log.SetActiveTarget(wx.LogTextCtrl(self.log))

        sizer = wx.BoxSizer()
        sizer.Add(self.log, 1, wx.EXPAND | wx.ALL, 0)

        self.SetSizer(sizer)


class TabDuplicates(wx.Panel):
    def __init__(self, parent, mlist):
        wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)

        self.list_ctrl = wx.ListCtrl(self, style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_NO_HEADER)
        self.listdata = {}
        self.list_ctrl.InsertColumn(0, "Renaming Preview")
        self.mlist = mlist
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.ActivateCb)

        sizer = wx.BoxSizer()
        sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 0)

        self.SetSizer(sizer)

    def SetDuplicates(self, duplicates_keys):
        self.listdata.clear()
        self.list_ctrl.DeleteAllItems()
        row_id = 0
        self.list_ctrl.Freeze()
        for keys in duplicates_keys:
            all_previews = [y for x in self.mlist.listdata[keys[0]][config.D_PREVIEW] for y in x]
            stem, suffix = utils.GetFileStemAndSuffix(all_previews[0])
            if len(all_previews) > 1:
                stem = masks.getmergedprepost(all_previews)
            self.list_ctrl.InsertItem(row_id, stem)
            self.listdata[row_id] = [stem, keys]
            self.list_ctrl.SetItemData(row_id, row_id)
            row_id += 1
        self.list_ctrl.SetColumnWidth(0, wx.LIST_AUTOSIZE)
        self.list_ctrl.Thaw()

    def ActivateCb(self, event):
        row_id = event.GetIndex()
        pos = self.list_ctrl.GetItemData(row_id)  # 0-based unsorted index
        keys = self.listdata[pos][1]

        row_id0 = []
        for key in keys:
            idx = self.mlist.FindItem(-1, key)
            if idx != wx.NOT_FOUND:
                row_id0.append(idx)
        selected = utils.get_selected_items(self.mlist)
        self.mlist.Freeze()
        for row_id1 in selected:
            self.mlist.Select(row_id1, 0)
        self.mlist.Thaw()
        first = True
        for r in row_id0:
            self.mlist.Select(r)
            if first:
                self.mlist.EnsureVisible(r)
                first = False


class TabListItemError(wx.Panel):
    def __init__(self, parent, mlist):
        wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)

        self.list_ctrl = wx.ListCtrl(self, style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_NO_HEADER)
        self.listdata = {}
        self.list_ctrl.InsertColumn(0, "Error")
        self.mlist = mlist
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.ActivateCb)

        sizer = wx.BoxSizer()
        sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 0)

        self.SetSizer(sizer)

    def SetItemsWithError(self, errors):
        self.listdata.clear()
        self.list_ctrl.DeleteAllItems()
        row_id = 0
        self.list_ctrl.Freeze()
        for key, msg in errors.items():
            for m in msg:
                self.list_ctrl.InsertItem(row_id, m)
                self.listdata[row_id] = [m, key]
                self.list_ctrl.SetItemData(row_id, row_id)
                row_id += 1
        self.list_ctrl.SetColumnWidth(0, wx.LIST_AUTOSIZE)
        self.list_ctrl.Thaw()

    def ActivateCb(self, event):
        row_id = event.GetIndex()
        pos = self.list_ctrl.GetItemData(row_id)  # 0-based unsorted index
        key = self.listdata[pos][1]
        row_id0 = self.mlist.FindItem(-1, key)
        if row_id0 != wx.NOT_FOUND:
            selected = utils.get_selected_items(self.mlist)
            self.mlist.Freeze()
            for row_id1 in selected:
                self.mlist.Select(row_id1, 0)
            self.mlist.Thaw()
            self.mlist.Select(row_id0)
            self.mlist.EnsureVisible(row_id0)

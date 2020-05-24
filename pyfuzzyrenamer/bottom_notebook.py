import wx
import wx.lib.agw.aui as aui
from pyfuzzyrenamer import config, utils
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
        """"""
        wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)

        log = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY)
        wx.Log.SetActiveTarget(wx.LogTextCtrl(log))

        sizer = wx.BoxSizer()
        sizer.Add(log, 1, wx.EXPAND | wx.ALL, 0)

        self.SetSizer(sizer)


class TabDuplicates(wx.Panel):
    def __init__(self, parent, mlist):
        """"""
        wx.Panel.__init__(self, parent=parent, id=wx.ID_ANY)

        self.list_ctrl = wx.ListCtrl(self, style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_NO_HEADER)
        self.listdata = {}
        self.list_ctrl.InsertColumn(0, "Renaming Preview", width=500)
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
        for key in duplicates_keys:
            stem = self.mlist.listdata[key][config.D_PREVIEW].stem
            self.list_ctrl.InsertItem(row_id, stem)
            self.listdata[row_id] = [stem, key]
            self.list_ctrl.SetItemData(row_id, row_id)
            row_id += 1
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

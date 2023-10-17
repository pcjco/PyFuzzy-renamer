import pickle as pickle
import re
import wx
import wx.lib.mixins.listctrl as listmix
from pathlib import Path

from pyfuzzyrenamer import filters, utils
from pyfuzzyrenamer.config import get_config


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
    def __init__(self, parent, panel, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, pos=pos, size=size, style=style)
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

        self.InsertColumn(0, "#", width=35)
        self.InsertColumn(1, "Filter Name", width=150)
        self.InsertColumn(2, "Pattern", width=150)
        self.InsertColumn(3, "Replace", width=150)

        dt = FilterListCtrlDropTarget(self)
        dt.SetDefaultAction(wx.DragMove)
        self.SetDropTarget(dt)

        self.PopulateFilters(get_config()["filters"])
        self.unplug_preview = False

    def PopulateFilters(self, s_filters):
        self.DeleteAllItems()
        lines = s_filters.splitlines()
        it = iter(lines)
        row_id = 0
        index = 0
        for l1, l2, l3 in zip(it, it, it):
            data = (l1.strip()[1:], l2.strip()[1:-1], l3.strip()[1:-1])
            self.InsertItem(row_id, "%2d" % (int(index) + 1))
            self.SetItem(row_id, 1, data[0])
            self.SetItem(row_id, 2, data[1])
            self.SetItem(row_id, 3, data[2])
            if (l1.strip()[0]) == "+":
                self.CheckItem(row_id, True)
            else:
                self.CheckItem(row_id, False)
            try:
                re.compile(data[1])
                self.SetItemBackgroundColour(row_id, wx.Colour(153, 255, 153))
            except re.error:
                self.SetItemBackgroundColour(row_id, wx.Colour(255, 153, 153))

            row_id += 1
            index += 1

    def GetFilters(self):
        ret = ""
        row_id = -1
        while 1:
            row_id = self.GetNextItem(row_id)
            if row_id == -1:
                break
            ret += "+" if self.IsItemChecked(row_id) else "-"
            ret += self.GetItemText(row_id, 1) + "\n"
            ret += '"' + self.GetItemText(row_id, 2) + '"\n'
            ret += '"' + self.GetItemText(row_id, 3) + '"\n'
        return ret

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
        elif keycode == wx.WXK_DELETE:
            self.DeleteCb(None)
        elif keycode == wx.WXK_CONTROL_F:
            self.AddCb(None)
        elif keycode == wx.WXK_CONTROL_A:
            item = -1
            while 1:
                item = self.GetNextItem(item)
                if item == -1:
                    break
                self.SetItemState(item, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)

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
            s_filters = ""
            row_id0 = -1
            while 1:
                row_id0 = self.GetNextItem(row_id0)
                if row_id0 == -1:
                    break
                s_filters += "+" if self.IsItemChecked(row_id0) else "-"
                s_filters += self.GetItemText(row_id0, 1) + "\n"
                if row_id == row_id0:
                    if col_id == 2:
                        regexp = event.GetText()
                        s_filters += '"' + regexp + '"\n'
                        s_filters += '"' + self.GetItemText(row_id, 3) + '"\n'
                        try:
                            re.compile(regexp)
                            self.SetItemBackgroundColour(row_id0, wx.Colour(153, 255, 153))
                        except re.error:
                            self.SetItemBackgroundColour(row_id0, wx.Colour(255, 153, 153))
                    elif col_id == 3:
                        s_filters += '"' + self.GetItemText(row_id, 2) + '"\n'
                        s_filters += '"' + event.GetText() + '"\n'
                else:
                    s_filters += '"' + self.GetItemText(row_id0, 2) + '"\n'
                    s_filters += '"' + self.GetItemText(row_id0, 3) + '"\n'

            re_filters = filters.CompileFilters(s_filters)
            filter_input = Path(self.panel.preview_filters.GetValue() + ".noext") if get_config()["input_as_path"] else self.panel.preview_filters.GetValue()
            self.panel.result_preview_filters.SetValue(filters.filter_processed(filter_input, re_filters))

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
            if flags & (
                wx.LIST_HITTEST_NOWHERE | wx.LIST_HITTEST_ABOVE | wx.LIST_HITTEST_BELOW
            ):  # empty list or below last item
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
            try:
                re.compile(self.GetItemText(idx, 2))
                self.SetItemBackgroundColour(idx, wx.Colour(153, 255, 153))
            except re.error:
                self.SetItemBackgroundColour(idx, wx.Colour(255, 153, 153))
            index += 1

    def RightClickCb(self, event):
        menu = wx.Menu()
        mnu_add = menu.Append(wx.ID_ANY, "Add filter\tCtrl+F", "Add filter")
        self.Bind(wx.EVT_MENU, self.AddCb, mnu_add)
        if self.GetSelectedItemCount():
            mnu_del = menu.Append(wx.ID_ANY, "Delete filter\tDelete", "Delete filter")
            self.Bind(wx.EVT_MENU, self.DeleteCb, mnu_del)
        pos = self.ScreenToClient(event.GetPosition())
        self.PopupMenu(menu, pos)
        menu.Destroy()
        event.Skip()

    def AddCb(self, event):
        data = ("new filter", "", "")
        row_id = self.GetItemCount()
        self.InsertItem(row_id, "%2d" % (int(row_id) + 1))
        self.SetItem(row_id, 1, data[0])
        self.SetItem(row_id, 2, data[1])
        self.SetItem(row_id, 3, data[2])
        self.CheckItem(row_id, True)
        self.SetItemBackgroundColour(row_id, wx.Colour(153, 255, 153))

    def DeleteCb(self, event):
        selected = utils.get_selected_items(self)

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

    def CheckCb(self, event):
        if not self.unplug_preview:
            self.panel.UpdateFilterPreview()

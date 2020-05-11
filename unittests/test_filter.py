import unittest
import wx

from pyfuzzyrenamer import config
from unittests import pfr

# ---------------------------------------------------------------------------


class filter_Tests(pfr.PyFuzzyRenamerTestCase):
    def test_filter(self):
        for each in self.button_panel.GetChildren():
            if each.GetLabel() == "Masks && Filters...":
                btn = each
                break

        def setFilters():
            for tlw in wx.GetTopLevelWindows():
                if "masksandfiltersDialog" in type(tlw).__name__:
                    dlg = tlw
                    break
            dlg.panel.notebook.SetSelection(1)
            event = wx.KeyEvent(wx.wxEVT_CHAR)
            event.SetKeyCode(wx.WXK_CONTROL_A)
            dlg.panel.filters_list.GetEventHandler().ProcessEvent(event)
            event = wx.KeyEvent(wx.wxEVT_CHAR)
            event.SetKeyCode(wx.WXK_DELETE)
            dlg.panel.filters_list.GetEventHandler().ProcessEvent(event)

            self.addFilter(dlg.panel.filters_list, "my filter", "(^(the)\\b|, the)", " ", True)
            self.addFilter(dlg.panel.filters_list, "my filter 2", "(wire)", "foo", False)

            event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
            dlg.panel.filters_list.GetEventHandler().ProcessEvent(event)

        wx.CallAfter(setFilters)
        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
        btn.GetEventHandler().ProcessEvent(event)

        clipdata = wx.TextDataObject()
        clipdata.SetText("The wiire")
        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(clipdata)
        wx.TheClipboard.Close()
        self.frame.panel.OnAddSourceFromClipboard(None)
        clipdata = wx.TextDataObject()
        clipdata.SetText("Wire, The")
        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(clipdata)
        wx.TheClipboard.Close()
        self.frame.panel.OnAddChoicesFromClipboard(None)

        for each in self.button_panel.GetChildren():
            if each.GetLabel() == "Best match":
                btn = each
                break

        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
        btn.GetEventHandler().ProcessEvent(event)

        lst = self.frame.panel.list_ctrl
        item = -1
        item = lst.GetNextItem(item)
        self.assertEqual(
            ["The wiire", "89", "Wire, The", "Wire, The", "Matched", "True"],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )

    def test_filter2(self):
        for each in self.button_panel.GetChildren():
            if each.GetLabel() == "Masks && Filters...":
                btn = each
                break

        def setFilters():
            for tlw in wx.GetTopLevelWindows():
                if "masksandfiltersDialog" in type(tlw).__name__:
                    dlg = tlw
                    break
            dlg.panel.notebook.SetSelection(1)
            event = wx.KeyEvent(wx.wxEVT_CHAR)
            event.SetKeyCode(wx.WXK_CONTROL_A)
            dlg.panel.filters_list.GetEventHandler().ProcessEvent(event)
            event = wx.KeyEvent(wx.wxEVT_CHAR)
            event.SetKeyCode(wx.WXK_DELETE)
            dlg.panel.filters_list.GetEventHandler().ProcessEvent(event)

            self.addFilter(dlg.panel.filters_list, "my filter", "(wire)", "foo", True)
            self.addFilter(dlg.panel.filters_list, "my filter 2", "(^(the)\\b|, the)", " ", True)

            event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
            dlg.panel.filters_list.GetEventHandler().ProcessEvent(event)

        wx.CallAfter(setFilters)
        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
        btn.GetEventHandler().ProcessEvent(event)

        clipdata = wx.TextDataObject()
        clipdata.SetText("The foo")
        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(clipdata)
        wx.TheClipboard.Close()
        self.frame.panel.OnAddSourceFromClipboard(None)
        clipdata = wx.TextDataObject()
        clipdata.SetText("Wire, The")
        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(clipdata)
        wx.TheClipboard.Close()
        self.frame.panel.OnAddChoicesFromClipboard(None)

        for each in self.button_panel.GetChildren():
            if each.GetLabel() == "Best match":
                btn = each
                break

        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
        btn.GetEventHandler().ProcessEvent(event)

        lst = self.frame.panel.list_ctrl
        item = -1
        item = lst.GetNextItem(item)
        self.assertEqual(
            ["The foo", "100", "Wire, The", "Wire, The", "Matched", "True"],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )

    def addFilter(self, lst, name, regexp, repl, active):
        event = wx.KeyEvent(wx.wxEVT_CHAR)
        event.SetKeyCode(wx.WXK_CONTROL_F)
        lst.GetEventHandler().ProcessEvent(event)
        row_id = lst.GetItemCount() - 1
        lst.SetItem(row_id, 1, name)
        lst.SetItem(row_id, 2, regexp)
        event = wx.ListEvent(wx.wxEVT_LIST_END_LABEL_EDIT)
        event.SetIndex(row_id)
        event.SetColumn(2)
        lst.GetEventHandler().ProcessEvent(event)
        lst.SetItem(row_id, 3, repl)
        event = wx.ListEvent(wx.wxEVT_LIST_END_LABEL_EDIT)
        event.SetIndex(row_id)
        event.SetColumn(3)
        lst.GetEventHandler().ProcessEvent(event)
        lst.CheckItem(row_id, active)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()

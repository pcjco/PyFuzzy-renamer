import unittest
import wx

from pyfuzzyrenamer import config
from unittests import pfr

# ---------------------------------------------------------------------------


class mask_Tests(pfr.PyFuzzyRenamerTestCase):
    def test_mask(self):
        for each in self.button_panel.GetChildren():
            if each.GetLabel() == "Masks && Filters...":
                btn = each
                break

        def setMasks():
            for tlw in wx.GetTopLevelWindows():
                if "masksandfiltersDialog" in type(tlw).__name__:
                    dlg = tlw
                    break
            dlg.panel.notebook.SetSelection(0)
            event = wx.KeyEvent(wx.wxEVT_CHAR)
            event.SetKeyCode(wx.WXK_CONTROL_A)
            dlg.panel.masks_list.GetEventHandler().ProcessEvent(event)
            event = wx.KeyEvent(wx.wxEVT_CHAR)
            event.SetKeyCode(wx.WXK_DELETE)
            dlg.panel.masks_list.GetEventHandler().ProcessEvent(event)

            self.addMask(dlg.panel.masks_list, "my mask", "(_disk\\w)$", True)
            self.addMask(dlg.panel.masks_list, "my mask 2", "^(\\[\\d{4}\\]\\s?)", False)

            event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
            dlg.panel.masks_list.GetEventHandler().ProcessEvent(event)

        wx.CallAfter(setMasks)
        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
        btn.GetEventHandler().ProcessEvent(event)

        clipdata = wx.TextDataObject()
        clipdata.SetText("[1984] The wiire_disk1")
        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(clipdata)
        wx.TheClipboard.Close()
        self.frame.panel.OnAddSourceFromClipboard(None)
        clipdata = wx.TextDataObject()
        clipdata.SetText("Dummy\nWire, The\nDummy 2")
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
            ["[1984] The wiire_disk1", "68", "Wire, The", "Wire, The_disk1", "1", "Matched", "True",],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )

    def test_mask2(self):
        for each in self.button_panel.GetChildren():
            if each.GetLabel() == "Masks && Filters...":
                btn = each
                break

        def setMasks():
            for tlw in wx.GetTopLevelWindows():
                if "masksandfiltersDialog" in type(tlw).__name__:
                    dlg = tlw
                    break
            dlg.panel.notebook.SetSelection(0)
            event = wx.KeyEvent(wx.wxEVT_CHAR)
            event.SetKeyCode(wx.WXK_CONTROL_A)
            dlg.panel.masks_list.GetEventHandler().ProcessEvent(event)
            event = wx.KeyEvent(wx.wxEVT_CHAR)
            event.SetKeyCode(wx.WXK_DELETE)
            dlg.panel.masks_list.GetEventHandler().ProcessEvent(event)

            self.addMask(dlg.panel.masks_list, "my mask", "(_disk\\w)$", True)
            self.addMask(dlg.panel.masks_list, "my mask 2", "^(\\[\\d{4}\\]\\s?)", True)

            event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
            dlg.panel.masks_list.GetEventHandler().ProcessEvent(event)

        wx.CallAfter(setMasks)
        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
        btn.GetEventHandler().ProcessEvent(event)

        clipdata = wx.TextDataObject()
        clipdata.SetText("[1984] The wiire_disk1")
        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(clipdata)
        wx.TheClipboard.Close()
        self.frame.panel.OnAddSourceFromClipboard(None)
        clipdata = wx.TextDataObject()
        clipdata.SetText("Dummy\nWire, The\nDummy 2")
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
            ["[1984] The wiire_disk1", "89", "Wire, The", "[1984] Wire, The_disk1", "1", "Matched", "True",],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )

    def test_mask3(self):
        for each in self.button_panel.GetChildren():
            if each.GetLabel() == "Masks && Filters...":
                btn = each
                break

        def setMasks():
            for tlw in wx.GetTopLevelWindows():
                if "masksandfiltersDialog" in type(tlw).__name__:
                    dlg = tlw
                    break
            dlg.panel.notebook.SetSelection(0)
            event = wx.KeyEvent(wx.wxEVT_CHAR)
            event.SetKeyCode(wx.WXK_CONTROL_A)
            dlg.panel.masks_list.GetEventHandler().ProcessEvent(event)
            event = wx.KeyEvent(wx.wxEVT_CHAR)
            event.SetKeyCode(wx.WXK_DELETE)
            dlg.panel.masks_list.GetEventHandler().ProcessEvent(event)

            self.addMask(dlg.panel.masks_list, "my mask", "(_disk\\w)$", True)
            self.addMask(dlg.panel.masks_list, "my mask 2", "^(\\[\\d{4}\\]\\s?)", True)
            self.addMask(dlg.panel.masks_list, "my mask 3", "(\\s\\((Fr|En|De|Es|It|Nl|Pt|Sv|No|Da).*?\\))", True)

            event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
            dlg.panel.masks_list.GetEventHandler().ProcessEvent(event)

        wx.CallAfter(setMasks)
        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
        btn.GetEventHandler().ProcessEvent(event)

        clipdata = wx.TextDataObject()
        clipdata.SetText("[1984] The wiire (Nl)_disk1")
        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(clipdata)
        wx.TheClipboard.Close()
        self.frame.panel.OnAddSourceFromClipboard(None)
        clipdata = wx.TextDataObject()
        clipdata.SetText("Dummy\nWire, The\nDummy 2")
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
            ["[1984] The wiire (Nl)_disk1", "89", "Wire, The", "[1984] Wire, The (Nl)_disk1", "1", "Matched", "True",],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )

    def addMask(self, lst, name, regexp, active):
        event = wx.KeyEvent(wx.wxEVT_CHAR)
        event.SetKeyCode(wx.WXK_CONTROL_M)
        lst.GetEventHandler().ProcessEvent(event)
        row_id = lst.GetItemCount() - 1
        lst.SetItem(row_id, 1, name)
        lst.SetItem(row_id, 2, regexp)
        event = wx.ListEvent(wx.wxEVT_LIST_END_LABEL_EDIT)
        event.SetIndex(row_id)
        event.SetColumn(2)
        lst.GetEventHandler().ProcessEvent(event)
        lst.CheckItem(row_id, active)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()

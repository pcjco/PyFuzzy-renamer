import os
import unittest
import wx

from unittests import pfr
from pyfuzzyrenamer import config, main_listctrl

# ---------------------------------------------------------------------------


class action_Tests(pfr.PyFuzzyRenamerTestCase):
    def test_pickchoice(self):
        sourcesDir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "./data/sources")
        )
        self.frame.panel.AddSourceFromDir(sourcesDir)
        choicesDir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "./data/choices")
        )
        self.frame.panel.AddChoicesFromDir(choicesDir)

        for each in self.button_panel.GetChildren():
            if each.GetLabel() == "Best match":
                btn = each
                break

        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
        btn.GetEventHandler().ProcessEvent(event)

        lst = self.frame.panel.list_ctrl
        item = -1
        item = lst.GetNextItem(item)

        def Pick():
            for dlg in lst.GetChildren():
                if isinstance(dlg, main_listctrl.PickCandidate):
                    dlg.text.SetValue("Volutaria tubuliflora.txt")
                    event = wx.CommandEvent(wx.wxEVT_TEXT_ENTER, dlg.text.GetId())
                    dlg.text.GetEventHandler().ProcessEvent(event)
                    self.assertEqual(
                        [
                            "Abutilon à feuilles marbrées.txt",
                            "35",
                            "Volutaria tubuliflora.txt",
                            "Volutaria tubuliflora.txt",
                            "User choice",
                            "True",
                        ],
                        [
                            lst.GetItemText(item, col)
                            for col in range(0, len(config.default_columns))
                        ],
                    )

        lst.Select(item)
        event = wx.KeyEvent(wx.wxEVT_CHAR)
        event.SetKeyCode(wx.WXK_CONTROL_P)
        wx.CallAfter(Pick)
        lst.GetEventHandler().ProcessEvent(event)

    def test_resetmatch(self):
        sourcesDir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "./data/sources")
        )
        self.frame.panel.AddSourceFromDir(sourcesDir)
        choicesDir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "./data/choices")
        )
        self.frame.panel.AddChoicesFromDir(choicesDir)

        for each in self.button_panel.GetChildren():
            if each.GetLabel() == "Best match":
                btn = each
                break

        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
        btn.GetEventHandler().ProcessEvent(event)

        lst = self.frame.panel.list_ctrl
        item = -1
        item1 = lst.GetNextItem(item)
        lst.Select(item1)
        item2 = lst.GetNextItem(item1)
        lst.Select(item2)
        event = wx.KeyEvent(wx.wxEVT_CHAR)
        event.SetKeyCode(wx.WXK_CONTROL_R)
        lst.GetEventHandler().ProcessEvent(event)
        self.assertEqual(
            ["Abutilon à feuilles marbrées.txt", "", "", "", "No match", "True"],
            [
                lst.GetItemText(item1, col)
                for col in range(0, len(config.default_columns))
            ],
        )
        self.assertEqual(
            ["Acanthe à feuilles molles.txt", "", "", "", "No match", "True"],
            [
                lst.GetItemText(item2, col)
                for col in range(0, len(config.default_columns))
            ],
        )


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()

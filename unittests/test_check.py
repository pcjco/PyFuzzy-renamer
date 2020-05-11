import os
import unittest
import wx

from unittests import pfr

# ---------------------------------------------------------------------------


class check_Tests(pfr.PyFuzzyRenamerTestCase):
    def test_check(self):
        sourcesDir = os.path.abspath(os.path.join(os.path.dirname(__file__), "./data/sources"))
        self.frame.panel.AddSourceFromDir(sourcesDir)
        choicesDir = os.path.abspath(os.path.join(os.path.dirname(__file__), "./data/choices"))
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

        lst.CheckItem(item, False)
        self.assertFalse(lst.IsItemChecked(item))
        self.assertEqual("False", lst.GetItemText(item, 5))
        self.assertEqual(wx.FONTSTYLE_ITALIC, lst.GetItemFont(item).GetStyle())

        lst.CheckItem(item, True)
        self.assertTrue(lst.IsItemChecked(item))
        self.assertEqual("True", lst.GetItemText(item, 5))
        self.assertEqual(wx.FONTSTYLE_NORMAL, lst.GetItemFont(item).GetStyle())


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()

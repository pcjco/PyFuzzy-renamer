import os
import unittest
import wx

from unittests import pfr
from pyfuzzyrenamer import config

# ---------------------------------------------------------------------------


class swap_Tests(pfr.PyFuzzyRenamerTestCase):
    def test_swap(self):
        sourcesDir = os.path.abspath(os.path.join(os.path.dirname(__file__), "./data/sources"))
        self.frame.panel.AddSourcesFromDir(sourcesDir)
        choicesDir = os.path.abspath(os.path.join(os.path.dirname(__file__), "./data/choices"))
        self.frame.panel.AddChoicesFromDir(choicesDir)

        lst = self.frame.panel.OnSwap(None)

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
            [
                "Abutilon hybridum.txt",
                "86",
                "Abutilon à feuilles marbrées.txt",
                "Abutilon à feuilles marbrées.txt",
                "1",
                "Matched",
                "True",
            ],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )

# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()

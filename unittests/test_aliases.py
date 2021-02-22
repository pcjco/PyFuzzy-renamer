import os
import unittest
import wx

from unittests import pfr
from pyfuzzyrenamer import config

# ---------------------------------------------------------------------------


class aliases_Tests(pfr.PyFuzzyRenamerTestCase):
    def test_aliases(self):
        sourcesDir = os.path.abspath(os.path.join(os.path.dirname(__file__), "./data/sources"))
        self.frame.panel.AddSourcesFromDir(sourcesDir)
        choicesFile = os.path.abspath(os.path.join(os.path.dirname(__file__), "./data/aliases.xlsx"))
        self.frame.panel.ImportChoicesFromFile(choicesFile)

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
                "Abutilon à feuilles marbrées.txt",
                "86",
                "Abutilon hybridum.txt",
                "ah.txt",
                "1",
                "Matched",
                "True",
            ],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )

# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()

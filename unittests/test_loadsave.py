import os
import shutil
import unittest
import wx

from pyfuzzyrenamer import config, main_listctrl
from unittests import pfr

# ---------------------------------------------------------------------------


class loadsave_Tests(pfr.PyFuzzyRenamerTestCase):
    def test_loadsave(self):
        if os.path.exists(self.outdir):
            shutil.rmtree(self.outdir)
        os.makedirs(self.outdir)
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

        def Pick():
            for dlg in lst.GetChildren():
                if isinstance(dlg, main_listctrl.PickCandidate):
                    dlg.text.SetValue("volutaria tubuliflora")
                    event = wx.CommandEvent(wx.wxEVT_TEXT_ENTER, dlg.text.GetId())
                    dlg.text.GetEventHandler().ProcessEvent(event)

        lst.Select(item)
        event = wx.KeyEvent(wx.wxEVT_CHAR)
        event.SetKeyCode(wx.WXK_CONTROL_P)
        wx.CallAfter(Pick)
        lst.GetEventHandler().ProcessEvent(event)
        lst.Select(item, 0)

        item1 = lst.GetNextItem(item)
        lst.Select(item1)
        item2 = lst.GetNextItem(item1)
        lst.Select(item2)
        event = wx.KeyEvent(wx.wxEVT_CHAR)
        event.SetKeyCode(wx.WXK_CONTROL_R)
        lst.GetEventHandler().ProcessEvent(event)
        lst.Select(item1, 0)
        lst.Select(item2, 0)

        item = lst.GetNextItem(item2)
        lst.CheckItem(item, False)

        sessionFile = os.path.abspath(os.path.join(self.outdir, "./session.sav"))
        self.frame.SaveSession(sessionFile)

        for each in self.button_panel.GetChildren():
            if each.GetLabel() == "Reset":
                btn = each
                break

        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
        btn.GetEventHandler().ProcessEvent(event)

        self.frame.LoadSession(sessionFile)

        lst = self.frame.panel.list_ctrl
        event = wx.ListEvent(wx.wxEVT_LIST_COL_CLICK, lst.GetId())
        event.SetColumn(3)
        lst.GetEventHandler().ProcessEvent(event)

        item = -1
        item = lst.GetNextItem(item)
        self.assertEqual(
            ["Acanthe à feuilles molles.txt", "", "", "", "", "", "True"],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            ["Acanthe épineuse.txt", "", "", "", "", "", "True"],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            [
                "Abutilon à feuilles marbrées.txt",
                "86",
                "Abutilon hybridum.txt",
                "Abutilon hybridum.txt",
                "1",
                "Matched",
                "True",
            ],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            ["Aconit vénéneux.txt", "52", "Aconitum anthora.txt", "Aconitum anthora.txt", "1", "Matched", "False",],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            ["Violette cornue.txt", "71", "Viola cornuta.txt", "Viola cornuta.txt", "1", "Matched", "True",],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            [
                "Volutaire à fleurs tubulées.txt",
                "54",
                "Volutaria tubuliflora.txt",
                "Volutaria tubuliflora.txt",
                "1",
                "Matched",
                "True",
            ],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )

        shutil.rmtree(self.outdir)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()

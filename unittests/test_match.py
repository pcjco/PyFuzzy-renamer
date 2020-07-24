import os
import unittest
import wx
from pathlib import Path

from unittests import pfr
from pyfuzzyrenamer import config
from pyfuzzyrenamer.config import get_config

# ---------------------------------------------------------------------------


class match_Tests(pfr.PyFuzzyRenamerTestCase):
    def test_match(self):
        sourcesDir = os.path.abspath(os.path.join(os.path.dirname(__file__), "./data/sources"))
        self.frame.panel.AddSourcesFromDir(sourcesDir)
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
            ["Acanthe à feuilles molles.txt", "70", "Acanthus mollis.txt", "Acanthus mollis.txt", "1", "Matched", "True",],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            ["Acanthe épineuse.txt", "73", "Acanthus spinosus.txt", "Acanthus spinosus.txt", "1", "Matched", "True",],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            ["Aconit vénéneux.txt", "52", "Aconitum anthora.txt", "Aconitum anthora.txt", "1", "Matched", "True",],
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

    def test_match_sort_similarity(self):
        sourcesDir = os.path.abspath(os.path.join(os.path.dirname(__file__), "./data/sources"))
        self.frame.panel.AddSourcesFromDir(sourcesDir)
        choicesDir = os.path.abspath(os.path.join(os.path.dirname(__file__), "./data/choices"))
        self.frame.panel.AddChoicesFromDir(choicesDir)

        for each in self.button_panel.GetChildren():
            if each.GetLabel() == "Best match":
                btn = each
                break

        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
        btn.GetEventHandler().ProcessEvent(event)

        lst = self.frame.panel.list_ctrl
        event = wx.ListEvent(wx.wxEVT_LIST_COL_CLICK, lst.GetId())
        event.SetColumn(1)
        lst.GetEventHandler().ProcessEvent(event)

        item = -1
        item = lst.GetNextItem(item)
        self.assertEqual(
            ["Aconit vénéneux.txt", "52", "Aconitum anthora.txt", "Aconitum anthora.txt", "1", "Matched", "True",],
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
        item = lst.GetNextItem(item)
        self.assertEqual(
            ["Acanthe à feuilles molles.txt", "70", "Acanthus mollis.txt", "Acanthus mollis.txt", "1", "Matched", "True",],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            ["Violette cornue.txt", "71", "Viola cornuta.txt", "Viola cornuta.txt", "1", "Matched", "True",],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            ["Acanthe épineuse.txt", "73", "Acanthus spinosus.txt", "Acanthus spinosus.txt", "1", "Matched", "True",],
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

    def test_match_sort_match(self):
        sourcesDir = os.path.abspath(os.path.join(os.path.dirname(__file__), "./data/sources"))
        self.frame.panel.AddSourcesFromDir(sourcesDir)
        choicesDir = os.path.abspath(os.path.join(os.path.dirname(__file__), "./data/choices"))
        self.frame.panel.AddChoicesFromDir(choicesDir)

        for each in self.button_panel.GetChildren():
            if each.GetLabel() == "Best match":
                btn = each
                break

        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
        btn.GetEventHandler().ProcessEvent(event)

        lst = self.frame.panel.list_ctrl
        event = wx.ListEvent(wx.wxEVT_LIST_COL_CLICK, lst.GetId())
        event.SetColumn(2)
        lst.GetEventHandler().ProcessEvent(event)

        lst = self.frame.panel.list_ctrl
        item = -1
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
            ["Acanthe à feuilles molles.txt", "70", "Acanthus mollis.txt", "Acanthus mollis.txt", "1", "Matched", "True",],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            ["Acanthe épineuse.txt", "73", "Acanthus spinosus.txt", "Acanthus spinosus.txt", "1", "Matched", "True",],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            ["Aconit vénéneux.txt", "52", "Aconitum anthora.txt", "Aconitum anthora.txt", "1", "Matched", "True",],
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

    def test_match_sort_preview(self):
        sourcesDir = os.path.abspath(os.path.join(os.path.dirname(__file__), "./data/sources"))
        self.frame.panel.AddSourcesFromDir(sourcesDir)
        choicesDir = os.path.abspath(os.path.join(os.path.dirname(__file__), "./data/choices"))
        self.frame.panel.AddChoicesFromDir(choicesDir)

        for each in self.button_panel.GetChildren():
            if each.GetLabel() == "Best match":
                btn = each
                break

        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
        btn.GetEventHandler().ProcessEvent(event)

        lst = self.frame.panel.list_ctrl
        event = wx.ListEvent(wx.wxEVT_LIST_COL_CLICK, lst.GetId())
        event.SetColumn(3)
        lst.GetEventHandler().ProcessEvent(event)

        lst = self.frame.panel.list_ctrl
        item = -1
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
            ["Acanthe à feuilles molles.txt", "70", "Acanthus mollis.txt", "Acanthus mollis.txt", "1", "Matched", "True",],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            ["Acanthe épineuse.txt", "73", "Acanthus spinosus.txt", "Acanthus spinosus.txt", "1", "Matched", "True",],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            ["Aconit vénéneux.txt", "52", "Aconitum anthora.txt", "Aconitum anthora.txt", "1", "Matched", "True",],
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

    def test_match_sort_status(self):
        sourcesDir = os.path.abspath(os.path.join(os.path.dirname(__file__), "./data/sources"))
        self.frame.panel.AddSourcesFromDir(sourcesDir)
        choicesDir = os.path.abspath(os.path.join(os.path.dirname(__file__), "./data/choices"))
        self.frame.panel.AddChoicesFromDir(choicesDir)

        for each in self.button_panel.GetChildren():
            if each.GetLabel() == "Best match":
                btn = each
                break

        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
        btn.GetEventHandler().ProcessEvent(event)

        lst = self.frame.panel.list_ctrl
        event = wx.ListEvent(wx.wxEVT_LIST_COL_CLICK, lst.GetId())
        event.SetColumn(4)
        lst.GetEventHandler().ProcessEvent(event)

        lst = self.frame.panel.list_ctrl
        item = -1
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
            ["Acanthe à feuilles molles.txt", "70", "Acanthus mollis.txt", "Acanthus mollis.txt", "1", "Matched", "True",],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            ["Acanthe épineuse.txt", "73", "Acanthus spinosus.txt", "Acanthus spinosus.txt", "1", "Matched", "True",],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            ["Aconit vénéneux.txt", "52", "Aconitum anthora.txt", "Aconitum anthora.txt", "1", "Matched", "True",],
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

    def test_match_sort_checked(self):
        sourcesDir = os.path.abspath(os.path.join(os.path.dirname(__file__), "./data/sources"))
        self.frame.panel.AddSourcesFromDir(sourcesDir)
        choicesDir = os.path.abspath(os.path.join(os.path.dirname(__file__), "./data/choices"))
        self.frame.panel.AddChoicesFromDir(choicesDir)

        for each in self.button_panel.GetChildren():
            if each.GetLabel() == "Best match":
                btn = each
                break

        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
        btn.GetEventHandler().ProcessEvent(event)

        lst = self.frame.panel.list_ctrl
        event = wx.ListEvent(wx.wxEVT_LIST_COL_CLICK, lst.GetId())
        event.SetColumn(5)
        lst.GetEventHandler().ProcessEvent(event)

        lst = self.frame.panel.list_ctrl
        item = -1
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
            ["Acanthe à feuilles molles.txt", "70", "Acanthus mollis.txt", "Acanthus mollis.txt", "1", "Matched", "True",],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            ["Acanthe épineuse.txt", "73", "Acanthus spinosus.txt", "Acanthus spinosus.txt", "1", "Matched", "True",],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            ["Aconit vénéneux.txt", "52", "Aconitum anthora.txt", "Aconitum anthora.txt", "1", "Matched", "True",],
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


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()

import os
import shutil
import unittest
import wx
from pathlib import Path

from unittests import pfr
from pyfuzzyrenamer import config, main_listctrl
from pyfuzzyrenamer.config import get_config

# ---------------------------------------------------------------------------


class rename_Tests(pfr.PyFuzzyRenamerTestCase):
    def test_rename(self):
        get_config()["keep_original"] = True
        if os.path.exists(self.outdir):
            shutil.rmtree(self.outdir)
        os.makedirs(self.outdir)
        self.frame.panel.SetOutputDirectory(self.outdir)
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

        for each in self.button_panel.GetChildren():
            if each.GetLabel() == "Rename":
                btn = each
                break

        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
        btn.GetEventHandler().ProcessEvent(event)

        renamed = []
        for f in sorted(Path(self.outdir).resolve().glob("*"), key=os.path.basename):
            try:
                if f.is_file():
                    renamed.append(f.name)
            except (OSError, IOError):
                pass
        shutil.rmtree(self.outdir)

        self.assertEqual(
            [
                "Abutilon hybridum.txt",
                "Acanthus mollis.txt",
                "Acanthus spinosus.txt",
                "Aconitum anthora.txt",
                "Viola cornuta.txt",
            ],
            renamed,
        )

    def test_rename_keep_ext(self):
        get_config()["keep_original"] = True
        get_config()["keep_match_ext"] = True
        if os.path.exists(self.outdir):
            shutil.rmtree(self.outdir)
        os.makedirs(self.outdir)
        self.frame.panel.SetOutputDirectory(self.outdir)
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

        for each in self.button_panel.GetChildren():
            if each.GetLabel() == "Rename":
                btn = each
                break

        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
        btn.GetEventHandler().ProcessEvent(event)

        renamed = []
        for f in sorted(Path(self.outdir).resolve().glob("*"), key=os.path.basename):
            try:
                if f.is_file():
                    renamed.append(f.name)
            except (OSError, IOError):
                pass
        shutil.rmtree(self.outdir)

        self.assertEqual(
            [
                "Abutilon hybridum.txt.txt",
                "Acanthus mollis.txt.txt",
                "Acanthus spinosus.txt.txt",
                "Aconitum anthora.txt.txt",
                "Viola cornuta.txt.txt",
            ],
            renamed,
        )

    def test_rename_inplace(self):
        get_config()["keep_original"] = False
        if os.path.exists(self.outdir):
            shutil.rmtree(self.outdir)
        shutil.copytree(os.path.abspath(os.path.join(os.path.dirname(__file__), "./data")), self.outdir)
        sourcesDir = os.path.join(self.outdir, "sources")
        self.frame.panel.AddSourcesFromDir(sourcesDir)
        choicesDir = os.path.join(self.outdir, "choices")
        self.frame.panel.AddChoicesFromDir(choicesDir)

        for each in self.button_panel.GetChildren():
            if each.GetLabel() == "Best match":
                btn = each
                break

        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
        btn.GetEventHandler().ProcessEvent(event)

        for each in self.button_panel.GetChildren():
            if each.GetLabel() == "Rename":
                btn = each
                break

        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
        btn.GetEventHandler().ProcessEvent(event)

        renamed = []
        for f in sorted(Path(os.path.join(self.outdir, "sources")).resolve().glob("*"), key=os.path.basename):
            try:
                if f.is_file():
                    renamed.append(f.name)
            except (OSError, IOError):
                pass
        shutil.rmtree(self.outdir)

        self.assertEqual(
            [
                "Abutilon hybridum.txt",
                "Acanthus mollis.txt",
                "Acanthus spinosus.txt",
                "Aconitum anthora.txt",
                "Viola cornuta.txt",
                "Volutaire à fleurs tubulées.txt",
            ],
            renamed,
        )

    def test_rename_undo(self):
        get_config()["keep_original"] = False
        if os.path.exists(self.outdir):
            shutil.rmtree(self.outdir)
        shutil.copytree(os.path.abspath(os.path.join(os.path.dirname(__file__), "./data")), self.outdir)
        sourcesDir = os.path.join(self.outdir, "sources")
        self.frame.panel.AddSourcesFromDir(sourcesDir)
        choicesDir = os.path.join(self.outdir, "choices")
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
                    dlg.text.SetValue("viola cornuta")
                    event = wx.CommandEvent(wx.wxEVT_TEXT_ENTER, dlg.text.GetId())
                    dlg.text.GetEventHandler().ProcessEvent(event)

        lst.Select(item)
        event = wx.KeyEvent(wx.wxEVT_CHAR)
        event.SetKeyCode(wx.WXK_CONTROL_P)
        wx.CallAfter(Pick)
        lst.GetEventHandler().ProcessEvent(event)
        wx.Yield()

        item = lst.GetNextItem(item)
        lst.CheckItem(item, False)

        for each in self.button_panel.GetChildren():
            if each.GetLabel() == "Rename":
                btn = each
                break

        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
        btn.GetEventHandler().ProcessEvent(event)

        renamed = []
        for f in sorted(Path(os.path.join(self.outdir, "sources")).resolve().glob("*"), key=os.path.basename):
            try:
                if f.is_file():
                    renamed.append(f.name)
            except (OSError, IOError):
                pass

        self.assertEqual(
            [
                "Acanthe à feuilles molles.txt",
                "Acanthus spinosus.txt",
                "Aconitum anthora.txt",
                "Viola cornuta.txt",
                "Violette cornue.txt",
                "Volutaire à fleurs tubulées.txt",
            ],
            renamed,
        )

        for each in self.button_panel.GetChildren():
            if each.GetLabel() == "Undo Rename":
                btn = each
                break

        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
        btn.GetEventHandler().ProcessEvent(event)

        renamed = []
        for f in sorted(Path(os.path.join(self.outdir, "sources")).resolve().glob("*"), key=os.path.basename):
            try:
                if f.is_file():
                    renamed.append(f.name)
            except (OSError, IOError):
                pass
        shutil.rmtree(self.outdir)

        self.assertEqual(
            [
                "Abutilon à feuilles marbrées.txt",
                "Acanthe à feuilles molles.txt",
                "Acanthe épineuse.txt",
                "Aconit vénéneux.txt",
                "Violette cornue.txt",
                "Volutaire à fleurs tubulées.txt",
            ],
            renamed,
        )

    def test_rename_undo_multimatch(self):
        get_config()["keep_original"] = False
        if os.path.exists(self.outdir):
            shutil.rmtree(self.outdir)
        shutil.copytree(os.path.abspath(os.path.join(os.path.dirname(__file__), "./data")), self.outdir)

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

            event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_OK)
            dlg.panel.masks_list.GetEventHandler().ProcessEvent(event)

        wx.CallAfter(setMasks)
        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
        btn.GetEventHandler().ProcessEvent(event)

        sourcesDir = os.path.join(self.outdir, "sources_multimatch")
        self.frame.panel.AddSourcesFromDir(sourcesDir)
        choicesDir = os.path.join(self.outdir, "choices_multimatch")
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
                "Acanthe à feuilles molles_disk2.txt",
                "70",
                "Acanthus mollis[_disk1,_disk2].txt",
                "Acanthus mollis_disk2.txt",
                "2",
                "Matched",
                "True",
            ],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            [
                "Acanthe épineuse.txt",
                "73",
                "Acanthus spinosus[_disk1,_disk2].txt",
                "Acanthus spinosus[_disk1,_disk2].txt",
                "2",
                "Matched",
                "True",
            ],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            [
                "Aconit vénéneux[ ,_disk1,_disk3].txt",
                "52",
                "Aconitum anthora[ ,_disk2,_disk3].txt",
                "Aconitum anthora[ ,_disk1,_disk2,_disk3].txt",
                "3",
                "Matched",
                "True",
            ],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            ["Violette cornue_disk1.txt", "71", "Viola cornuta.txt", "Viola cornuta_disk1.txt", "1", "Matched", "True",],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            ["Volutaire à fleurs tubulées_disk1.txt", "57", "Viola cornuta.txt", "Viola cornuta_disk1.txt", "1", "Matched", "True",],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )

        for each in self.button_panel.GetChildren():
            if each.GetLabel() == "Rename":
                btn = each
                break

        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
        btn.GetEventHandler().ProcessEvent(event)

        renamed = []
        for f in sorted(Path(os.path.join(self.outdir, "sources_multimatch")).resolve().glob("*"), key=os.path.basename):
            try:
                if f.is_file():
                    renamed.append(f.name)
            except (OSError, IOError):
                pass

        self.assertEqual(
            [
                "Acanthus mollis_disk2.txt",
                "Acanthus spinosus_disk1.txt",
                "Acanthus spinosus_disk2.txt",
                "Aconitum anthora.txt",
                "Aconitum anthora_disk1.txt",
                "Aconitum anthora_disk2.txt",
                "Aconitum anthora_disk3.txt",
                "Viola cornuta_disk1.txt",
                "Volutaire à fleurs tubulées_disk1.txt",
            ],
            renamed,
        )

        item = -1
        item = lst.GetNextItem(item)
        self.assertEqual(
            [
                "Acanthus mollis_disk2.txt",
                "100",
                "Acanthus mollis[_disk1,_disk2].txt",
                "Acanthus mollis_disk2.txt",
                "2",
                "Matched",
                "True",
            ],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            [
                "Acanthus spinosus[_disk1,_disk2].txt",
                "100",
                "Acanthus spinosus[_disk1,_disk2].txt",
                "Acanthus spinosus[_disk1,_disk2].txt",
                "2",
                "Matched",
                "True",
            ],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            [
                "Aconitum anthora[ ,_disk1,_disk2,_disk3].txt",
                "100",
                "Aconitum anthora[ ,_disk2,_disk3].txt",
                "Aconitum anthora[ ,_disk1,_disk2,_disk3].txt",
                "3",
                "Matched",
                "True",
            ],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            ["Viola cornuta_disk1.txt", "100", "Viola cornuta.txt", "Viola cornuta_disk1.txt", "1", "Matched", "True",],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            [
                "Volutaire à fleurs tubulées_disk1.txt",
                "57",
                "Viola cornuta.txt",
                "Viola cornuta_disk1.txt",
                "1",
                "Matched",
                "True",
            ],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )

        for each in self.button_panel.GetChildren():
            if each.GetLabel() == "Undo Rename":
                btn = each
                break

        event = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, btn.GetId())
        btn.GetEventHandler().ProcessEvent(event)

        renamed = []
        for f in sorted(Path(os.path.join(self.outdir, "sources_multimatch")).resolve().glob("*"), key=os.path.basename):
            try:
                if f.is_file():
                    renamed.append(f.name)
            except (OSError, IOError):
                pass
        shutil.rmtree(self.outdir)

        self.assertEqual(
            [
                "Acanthe à feuilles molles_disk2.txt",
                "Acanthe épineuse.txt",
                "Aconit vénéneux.txt",
                "Aconit vénéneux_disk1.txt",
                "Aconit vénéneux_disk3.txt",
                "Violette cornue_disk1.txt",
                "Volutaire à fleurs tubulées_disk1.txt",
            ],
            renamed,
        )

        item = -1
        item = lst.GetNextItem(item)
        self.assertEqual(
            [
                "Acanthe à feuilles molles_disk2.txt",
                "70",
                "Acanthus mollis[_disk1,_disk2].txt",
                "Acanthus mollis_disk2.txt",
                "2",
                "Matched",
                "True",
            ],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            [
                "Acanthe épineuse.txt",
                "73",
                "Acanthus spinosus[_disk1,_disk2].txt",
                "Acanthus spinosus[_disk1,_disk2].txt",
                "2",
                "Matched",
                "True",
            ],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            [
                "Aconit vénéneux[ ,_disk1,_disk3].txt",
                "52",
                "Aconitum anthora[ ,_disk2,_disk3].txt",
                "Aconitum anthora[ ,_disk1,_disk2,_disk3].txt",
                "3",
                "Matched",
                "True",
            ],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            ["Violette cornue_disk1.txt", "71", "Viola cornuta.txt", "Viola cornuta_disk1.txt", "1", "Matched", "True",],
            [lst.GetItemText(item, col) for col in range(0, len(config.default_columns))],
        )
        item = lst.GetNextItem(item)
        self.assertEqual(
            [
                "Volutaire à fleurs tubulées_disk1.txt",
                "57",
                "Viola cornuta.txt",
                "Viola cornuta_disk1.txt",
                "1",
                "Matched",
                "True",
            ],
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

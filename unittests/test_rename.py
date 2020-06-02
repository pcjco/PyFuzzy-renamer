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
        self.frame.panel.AddSourceFromDir(sourcesDir)
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
                "Volutaria tubuliflora.txt",
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
        self.frame.panel.AddSourceFromDir(sourcesDir)
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
                "Volutaria tubuliflora.txt.txt",
            ],
            renamed,
        )

    def test_rename_inplace(self):
        get_config()["keep_original"] = False
        if os.path.exists(self.outdir):
            shutil.rmtree(self.outdir)
        shutil.copytree(os.path.abspath(os.path.join(os.path.dirname(__file__), "./data")), self.outdir)
        sourcesDir = os.path.join(self.outdir, "sources")
        self.frame.panel.AddSourceFromDir(sourcesDir)
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
                "Volutaria tubuliflora.txt",
            ],
            renamed,
        )

    def test_rename_undo(self):
        get_config()["keep_original"] = False
        if os.path.exists(self.outdir):
            shutil.rmtree(self.outdir)
        shutil.copytree(os.path.abspath(os.path.join(os.path.dirname(__file__), "./data")), self.outdir)
        sourcesDir = os.path.join(self.outdir, "sources")
        self.frame.panel.AddSourceFromDir(sourcesDir)
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
                    dlg.text.SetValue("Viola cornuta")
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
                "Volutaria tubuliflora.txt",
            ],
            renamed,
        )

        for each in self.button_panel.GetChildren():
            if each.GetLabel() == "Undo":
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


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()

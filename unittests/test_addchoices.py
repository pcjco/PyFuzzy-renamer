#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
from unittests import pfr
import pyfuzzyrenamer
import os
import wx
from pathlib import Path

#---------------------------------------------------------------------------

class add_choices_Tests(pfr.PyFuzzyRenamerTestCase):

    def test_addchoices(self):
        self.add_choices(singles=False)
        
    def test_addchoices_single(self):
        self.add_choices(singles=True)

    def test_addchoices_directory(self):
        self.add_choices(dir=True)

    def test_addchoices_clipboard(self):
        self.add_choices(clipboard=True)

    def test_addchoices_drop(self):
        self.add_choices(drop=True)

    def add_choices(self, dir=False, singles=False, clipboard=False, drop=False):
        choicesDir = os.path.abspath(os.path.join(os.path.dirname(__file__), './data/choices'))
        if dir:
            self.frame.panel.AddChoicesFromDir(choicesDir)
        else:
            choices = []
            for f in Path(choicesDir).resolve().glob('*'):
                try:
                    if f.is_file():
                        choices.append(f)
                        if singles:
                            self.frame.panel.AddChoicesFromFiles(choices)
                            choices.clear()
                except (OSError, IOError):
                    pass
            if not singles:
                if drop:
                    def clickNO():
                        dlg = wx.GetActiveWindow()
                        clickEvent = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_NO)
                        dlg.ProcessEvent(clickEvent)
                    droptarget = self.frame.panel.GetDropTarget()
                    wx.CallAfter(clickNO)
                    droptarget.OnDropFiles(0, 0, [str(f) for f in choices])
                elif clipboard:
                    clipdata = wx.TextDataObject()
                    clipdata.SetText('\n'.join([str(f) for f in choices]))
                    wx.TheClipboard.Open()
                    wx.TheClipboard.SetData(clipdata)
                    wx.TheClipboard.Close()
                    self.frame.panel.OnAddChoicesFromClipboard(None)
                else:
                    self.frame.panel.AddChoicesFromFiles(choices)
        allNames = [f.file.name for f in pyfuzzyrenamer.candidates['all']]
        self.assertEqual(6, len(pyfuzzyrenamer.candidates['all']))
        self.assertIn("Abutilon hybridum.txt", allNames)
        self.assertIn("Volutaria tubuliflora.txt", allNames)

#---------------------------------------------------------------------------

if __name__ == '__main__':
    unittest.main()
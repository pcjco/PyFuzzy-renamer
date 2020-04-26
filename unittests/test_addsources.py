#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
from unittests import pfr
import pyfuzzyrenamer
import os
import wx
from pathlib import Path

#---------------------------------------------------------------------------

class add_sources_Tests(pfr.PyFuzzyRenamerTestCase):

    def test_addsources(self):
        self.add_sources(singles=False)
        
    def test_addsources_single(self):
        self.add_sources(singles=True)

    def test_addsources_directory(self):
        self.add_sources(dir=True)

    def test_addsources_clipboard(self):
        self.add_sources(clipboard=True)

    def test_addsources_drop(self):
        self.add_sources(drop=True)

    def add_sources(self, dir=False, singles=False, clipboard=False, drop=False):
        sourcesDir = os.path.abspath(os.path.join(os.path.dirname(__file__), './data/sources'))
        if dir:
            self.frame.panel.AddSourceFromDir(sourcesDir)
        else:
            sources = []
            for f in Path(sourcesDir).resolve().glob('*'):
                try:
                    if f.is_file():
                        sources.append(f)
                        if singles:
                            self.frame.panel.AddSourceFromFiles(sources)
                            sources.clear()
                except (OSError, IOError):
                    pass
            if not singles:
                if drop:
                    def clickYES():
                        dlg = wx.GetActiveWindow()
                        clickEvent = wx.CommandEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, wx.ID_YES)
                        dlg.ProcessEvent(clickEvent)
                    droptarget = self.frame.panel.GetDropTarget()
                    wx.CallAfter(clickYES)
                    droptarget.OnDropFiles(0, 0, [str(f) for f in sources])
                elif clipboard:
                    clipdata = wx.TextDataObject()
                    clipdata.SetText('\n'.join([str(f) for f in sources]))
                    wx.TheClipboard.Open()
                    wx.TheClipboard.SetData(clipdata)
                    wx.TheClipboard.Close()
                    self.frame.panel.OnAddSourceFromClipboard(None)
                else:
                    self.frame.panel.AddSourceFromFiles(sources)
        lst = self.frame.panel.list_ctrl
        item = -1
        item = lst.GetNextItem(item)
        self.assertEqual(6, lst.GetItemCount())
        self.assertEqual(["Abutilon à feuilles marbrées.txt", "", "", "", "Not processed", "True"], [lst.GetItemText(item, col) for col in range(0, len(pyfuzzyrenamer.default_columns))])
        for i in range(0,5):item = lst.GetNextItem(item)
        self.assertEqual(["Volutaire à fleurs tubulées.txt", "", "", "", "Not processed", "True"], [lst.GetItemText(item, col) for col in range(0, len(pyfuzzyrenamer.default_columns))])

#---------------------------------------------------------------------------

if __name__ == '__main__':
    unittest.main()
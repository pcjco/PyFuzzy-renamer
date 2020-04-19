#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
import pyfuzzyrenamer
import wx
import os
import copy

class PyFuzzyRenamerTestCase(unittest.TestCase):
    def setUp(self):

        # Backup and Reset config file
        pyfuzzyrenamer.read_config()
        self.backup_config = copy.deepcopy(pyfuzzyrenamer.config_dict)
        pyfuzzyrenamer.default_config()

        self.app = wx.App()
        wx.Log.SetActiveTarget(wx.LogStderr())
        self.frame = pyfuzzyrenamer.MainFrame()
        self.frame.Show()
        self.frame.PostSizeEvent()
        self.button_panel = self.frame.panel.GetChildren()[1].GetChildren()[0].GetChildren()[0]
        self.outdir = os.path.abspath(os.path.join(os.path.dirname(__file__), './outdir'))

    def tearDown(self):
        def _cleanup():
            for tlw in wx.GetTopLevelWindows():
                if tlw:
                    if isinstance(tlw, wx.Dialog) and tlw.IsModal():
                        tlw.EndModal(0)
                        wx.CallAfter(tlw.Destroy)
                    else:
                        tlw.Close(force=True)
            # Restore backup config file
            pyfuzzyrenamer.config_dict = self.backup_config
            pyfuzzyrenamer.write_config()
            wx.WakeUpIdle()

        timer = wx.PyTimer(_cleanup)
        timer.Start(100)
        self.app.MainLoop()
        del self.app


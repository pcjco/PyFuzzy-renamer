import os
import copy
import unittest
import wx

from pyfuzzyrenamer import config, main_dlg


class PyFuzzyRenamerTestCase(unittest.TestCase):
    def setUp(self):

        config.default()

        main_dlg.glob_choices.clear()
        self.app = wx.App()
        wx.Log.SetActiveTarget(wx.LogStderr())
        self.frame = main_dlg.MainFrame()
        self.frame.Show()
        self.frame.PostSizeEvent()
        self.button_panel = self.frame.panel.GetChildren()[1].GetChildren()[0].GetChildren()[0]
        self.outdir = os.path.abspath(os.path.join(os.path.dirname(__file__), "./outdir"))

    def tearDown(self):
        def _cleanup():
            for tlw in wx.GetTopLevelWindows():
                if tlw:
                    if isinstance(tlw, wx.Dialog) and tlw.IsModal():
                        tlw.EndModal(0)
                        wx.CallAfter(tlw.Destroy)
                    else:
                        tlw.Close(force=True)
            wx.WakeUpIdle()

        timer = wx.PyTimer(_cleanup)
        timer.Start(100)
        self.app.MainLoop()
        del self.app

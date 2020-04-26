import wx
from multiprocessing import freeze_support

from pyfuzzyrenamer import config, main_dlg


def main():
    """Launch main application """
    freeze_support()
    config.read()
    app = wx.App(False)
    frm = main_dlg.MainFrame()
    app.SetTopWindow(frm)

    app.MainLoop()


if __name__ == "__main__":
    main()

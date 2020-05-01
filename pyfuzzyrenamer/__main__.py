import wx

from pyfuzzyrenamer import config, main_dlg


def main():
    """Launch main application """
    config.read()

    app = wx.App(False)
    frm = main_dlg.MainFrame()
    app.SetTopWindow(frm)

    app.MainLoop()

    config.write()


if __name__ == "__main__":
    main()

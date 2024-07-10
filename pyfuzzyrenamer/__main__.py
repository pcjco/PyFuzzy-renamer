import wx

from pyfuzzyrenamer import args, config, main_dlg
from pyfuzzyrenamer.args import get_args
         
def main():
    """Launch main application """
    config.read()
    args.read()

    app = wx.App(redirect=False)

    frm = main_dlg.MainFrame()

    if not get_args().mode:
        app.SetTopWindow(frm)
        app.MainLoop()

    config.write()


if __name__ == "__main__":
    main()

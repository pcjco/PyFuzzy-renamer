import wx
from pathlib import Path

from pyfuzzyrenamer import (
    config,
    filters,
    filters_listctrl,
    icons,
    masks,
    masks_listctrl,
)


class masksandfiltersDialog(wx.Dialog):
    def __init__(self, parent, label):
        wx.Dialog.__init__(
            self,
            parent,
            title=label,
            size=(350, 300),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )

        self.panel = masksandfiltersPanel(self)
        btns = self.CreateButtonSizer(wx.OK | wx.CANCEL | wx.APPLY)
        default_button = wx.FindWindowById(wx.ID_APPLY, self)
        default_button.SetLabel("Reset")

        default_button.Bind(wx.EVT_BUTTON, self.OnReset)

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(self.panel, 1, wx.ALL | wx.EXPAND, 0)
        mainSizer.Add(btns, 0, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(mainSizer)
        self.Fit()

    def OnReset(self, event):
        self.panel.filters_list.PopulateFilters(config.default_filters)
        self.panel.masks_list.PopulateMasks(config.default_masks)


class masksandfiltersPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, style=wx.WANTS_CHARS)

        self.notebook = wx.Notebook(self)
        page_filters = wx.Panel(self.notebook)
        page_masks = wx.Panel(self.notebook)

        self.notebook.AddPage(page_masks, "Masks on Sources")
        self.notebook.AddPage(page_filters, "Matching Filters")

        self.filters_list = filters_listctrl.FilterListCtrl(
            page_filters, self, size=(-1, -1), style=wx.LC_REPORT | wx.BORDER_SUNKEN
        )
        label1 = wx.StaticText(page_filters, label="Test String", size=(60, -1))
        self.preview_filters = wx.TextCtrl(
            page_filters,
            value="Hitchhiker's Guide to the Galaxy, The (AGA)",
            size=(300, -1),
        )
        label2 = wx.StaticText(page_filters, label="Result", size=(60, -1))
        self.result_preview_filters = wx.TextCtrl(
            page_filters, value="", size=(300, -1), style=wx.TE_READONLY
        )

        wx.FileSystem.AddHandler(wx.MemoryFSHandler())
        image_Info = wx.MemoryFSHandler()
        image_Info.AddFile(
            "info.png", icons.Info_16_PNG.GetBitmap(), wx.BITMAP_TYPE_PNG
        )

        html_desc_filters = wx.html.HtmlWindow(page_filters, size=(-1, 135))
        html_desc_filters.SetPage(
            '<img src="memory:info.png">'
            " These filters, using Python regular expression patterns, are applied to <b>sources</b> and <b>choices</b> strings before matching occurs."
            "It is used to help matching by cleaning strings (removing tags, ...) beforehand.<br><br>"
            "For example, replacing the pattern <font face=\"verdana\">'(\\(\\d{4}\\))'</font> by <font face=\"verdana\">''</font>:<br>"
            '<ul><li><i><font face="verdana">The Wire <font color="red">(2002)</font></font></i> \u2B62 <i><font face="verdana">The Wire</font></i></li>'
        )

        sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer2.Add(label1, 0, wx.ALL, 5)
        sizer2.Add(self.preview_filters, 1, wx.EXPAND | wx.ALL, 0)

        sizer3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer3.Add(label2, 0, wx.ALL, 5)
        sizer3.Add(self.result_preview_filters, 1, wx.EXPAND | wx.ALL, 0)

        sizer_filters = wx.BoxSizer(wx.VERTICAL)
        sizer_filters.Add(self.filters_list, 2, wx.ALL | wx.EXPAND, 1)
        sizer_filters.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 0)
        sizer_filters.Add(sizer2, 0, wx.ALL | wx.EXPAND, 1)
        sizer_filters.Add(sizer3, 0, wx.ALL | wx.EXPAND, 1)
        sizer_filters.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 0)
        sizer_filters.Add(html_desc_filters, 0, wx.EXPAND | wx.ALL)
        page_filters.SetSizer(sizer_filters)

        self.masks_list = masks_listctrl.MaskListCtrl(
            page_masks, self, size=(-1, -1), style=wx.LC_REPORT | wx.BORDER_SUNKEN
        )
        label21 = wx.StaticText(page_masks, label="Test String", size=(80, -1))
        self.preview_masks = wx.TextCtrl(
            page_masks,
            value="(1986) Hitchhiker's Guide to the Galaxy, The (AGA) Disk1",
            size=(300, -1),
        )
        self.result_preview_masks_lead = wx.TextCtrl(
            page_masks, value="", size=(40, -1), style=wx.TE_READONLY
        )
        self.result_preview_masks_mid = wx.TextCtrl(
            page_masks, value="", size=(220, -1), style=wx.TE_READONLY
        )
        self.result_preview_masks_trail = wx.TextCtrl(
            page_masks, value="", size=(40, -1), style=wx.TE_READONLY
        )
        label22 = wx.StaticText(page_masks, label="Lead-Mid-Trail", size=(80, -1))

        html_desc_masks = wx.html.HtmlWindow(page_masks, size=(-1, 200))
        html_desc_masks.SetPage(
            '<img src="memory:info.png">'
            " These masks, using Python regular expression patterns, are removed from <b>sources</b> strings before filtering and matching occur."
            "It is used to remove leading and trailing expressions (year, disk#...) before matching and restore them at renaming.<br><br>"
            "For example, masking the pattern <font face=\"verdana\">'(\\s?disk\\d)$'</font>:<br>"
            '<ol><li>Source\u2B62masked source: <i><font face="verdana">The Wiiire <font color="red"> Disk1</font> \u2B62 The Wiiire</font></i></li>'
            '<li>Masked source\u2B62best choice: <i><font face="verdana">The Wiiire \u2B62 The Wire</font></i></li>'
            '<li>Best choice\u2B62renamed unmasked source: <i><font face="verdana">The Wire \u2B62 The Wire<font color="red"> Disk1</font></font></i></li>'
        )

        sizer22 = wx.BoxSizer(wx.HORIZONTAL)
        sizer22.Add(label21, 0, wx.ALL, 5)
        sizer22.Add(self.preview_masks, 1, wx.EXPAND | wx.ALL, 0)

        sizer32 = wx.BoxSizer(wx.HORIZONTAL)
        sizer32.Add(label22, 0, wx.ALL, 5)
        sizer32.Add(self.result_preview_masks_lead, 1, wx.EXPAND | wx.ALL, 0)
        sizer32.Add(self.result_preview_masks_mid, 5, wx.EXPAND | wx.ALL, 0)
        sizer32.Add(self.result_preview_masks_trail, 1, wx.EXPAND | wx.ALL, 0)

        sizer_masks = wx.BoxSizer(wx.VERTICAL)
        sizer_masks.Add(self.masks_list, 1, wx.ALL | wx.EXPAND, 1)
        sizer_masks.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 0)
        sizer_masks.Add(sizer22, 0, wx.ALL | wx.EXPAND, 1)
        sizer_masks.Add(sizer32, 0, wx.ALL | wx.EXPAND, 1)
        sizer_masks.Add(wx.StaticLine(self, -1), 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 0)
        sizer_masks.Add(html_desc_masks, 0, wx.EXPAND | wx.ALL)
        page_masks.SetSizer(sizer_masks)

        sizer = wx.BoxSizer()
        sizer.Add(self.notebook, 1, wx.EXPAND)

        self.SetSizer(sizer)
        self.UpdateMaskPreview()
        self.UpdateFilterPreview()

        self.Bind(wx.EVT_TEXT, self.onChangePreviewFilters, self.preview_filters)
        self.Bind(wx.EVT_TEXT, self.onChangePreviewMasks, self.preview_masks)

        page_filters.Fit()
        page_masks.Fit()
        self.Fit()

    def onChangePreviewFilters(self, event):
        self.UpdateFilterPreview()

    def onChangePreviewMasks(self, event):
        self.UpdateMaskPreview()

    def UpdateFilterPreview(self):
        re_filters = filters.CompileFilters(self.filters_list.GetFilters())
        self.result_preview_filters.SetValue(
            filters.filter_processed(
                Path(self.preview_filters.GetValue() + ".txt"), re_filters
            )
        )

    def UpdateMaskPreview(self):
        re_masks = masks.CompileMasks(self.masks_list.GetMasks())
        re_filters = []
        pre, middle, post = masks.mask_processed(
            Path(self.preview_masks.GetValue() + ".txt"),
            re_masks,
            re_filters,
            applyFilters=False,
        )
        self.result_preview_masks_lead.SetValue(pre)
        self.result_preview_masks_mid.SetValue(middle)
        self.result_preview_masks_trail.SetValue(post)

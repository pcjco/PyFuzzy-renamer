import argparse
import io
import os
import shutil
import unittest
import wx
from pathlib import Path
from contextlib import redirect_stdout

from unittests import pfr
from pyfuzzyrenamer import args, config, filters, main_listctrl, main_dlg, masks
from pyfuzzyrenamer.config import get_config
from pyfuzzyrenamer.args import get_args, get_argparser

# ---------------------------------------------------------------------------


class args_Tests(pfr.PyFuzzyRenamerTestCaseCLI):
    def test_args_report_match(self):
        get_config()["workers"] = 1
        get_config()["show_fullpath"] = False
        get_config()["hide_extension"] = True
        get_config()["masks"] = "+Ending Disk#\n" + r'"(\s?_disk\d)$"' + "\n"
        masks.FileMasked.masks = masks.CompileMasks(get_config()["masks"])
        filters.FileFiltered.filters = filters.CompileFilters(get_config()["filters"])

        if os.path.exists(self.outdir):
            shutil.rmtree(self.outdir)
        shutil.copytree(os.path.abspath(os.path.join(os.path.dirname(__file__), "./data")), self.outdir)
        sourcesDir = os.path.join(self.outdir, "sources_multimatch")
        choicesDir = os.path.join(self.outdir, "choices_multimatch")
        args.theArgs = args.theArgsParser.parse_args(["--sources", sourcesDir, "--choices", choicesDir, "report_match"])

        with io.StringIO() as buf, redirect_stdout(buf):
            frame = main_dlg.MainFrame()
            shutil.rmtree(self.outdir)
            output = buf.getvalue()
            self.assertEqual(
                "acanthe à feuilles molles --> acanthus mollis (70.00)\n"
                "acanthe épineuse --> acanthus spinosus (73.00)\n"
                "aconit vénéneux --> aconitum anthora (52.00)\n"
                "violette cornue --> viola cornuta (71.00)\n"
                "volutaire à fleurs tubulées --> volutaria tubuliflora (54.00)\n",
                output,
            )

    def test_args_preview_rename(self):
        get_config()["workers"] = 1
        get_config()["masks"] = "+Ending Disk#\n" + r'"(\s?_disk\d)$"' + "\n"
        masks.FileMasked.masks = masks.CompileMasks(get_config()["masks"])
        filters.FileFiltered.filters = filters.CompileFilters(get_config()["filters"])

        if os.path.exists(self.outdir):
            shutil.rmtree(self.outdir)
        shutil.copytree(os.path.abspath(os.path.join(os.path.dirname(__file__), "./data")), self.outdir)
        sourcesDir = os.path.join(self.outdir, "sources_multimatch")
        choicesDir = os.path.join(self.outdir, "choices_multimatch")
        args.theArgs = args.theArgsParser.parse_args(["--sources", sourcesDir, "--choices", choicesDir, "preview_rename"])

        with io.StringIO() as buf, redirect_stdout(buf):
            frame = main_dlg.MainFrame()
            shutil.rmtree(self.outdir)
            output = buf.getvalue()
            self.assertEqual(
                "Renaming : "
                + os.path.join(sourcesDir, "Acanthe à feuilles molles_disk2.txt")
                + " --> "
                + os.path.join(sourcesDir, "Acanthus mollis_disk2.txt\n")
                + "Renaming : "
                + os.path.join(sourcesDir, "Acanthe épineuse.txt")
                + " --> "
                + os.path.join(sourcesDir, "Acanthus spinosus_disk1.txt\n")
                + "Copying : "
                + os.path.join(sourcesDir, "Acanthus spinosus_disk1.txt")
                + " --> "
                + os.path.join(sourcesDir, "Acanthus spinosus_disk2.txt\n")
                + "Renaming : "
                + os.path.join(sourcesDir, "Aconit vénéneux.txt")
                + " --> "
                + os.path.join(sourcesDir, "Aconitum anthora.txt\n")
                + "Copying : "
                + os.path.join(sourcesDir, "Aconitum anthora.txt")
                + " --> "
                + os.path.join(sourcesDir, "Aconitum anthora_disk2.txt\n")
                + "Renaming : "
                + os.path.join(sourcesDir, "Aconit vénéneux_disk1.txt")
                + " --> "
                + os.path.join(sourcesDir, "Aconitum anthora_disk1.txt\n")
                + "Renaming : "
                + os.path.join(sourcesDir, "Aconit vénéneux_disk3.txt")
                + " --> "
                + os.path.join(sourcesDir, "Aconitum anthora_disk3.txt\n")
                + "Renaming : "
                + os.path.join(sourcesDir, "Violette cornue_disk1.txt")
                + " --> "
                + os.path.join(sourcesDir, "Viola cornuta_disk1.txt\n")
                + "Renaming : "
                + os.path.join(sourcesDir, "Volutaire à fleurs tubulées_disk1.txt")
                + " --> "
                + os.path.join(sourcesDir, "Volutaria tubuliflora_disk1.txt\n"),
                output,
            )

    def test_args_preview_rename_nomultirename(self):
        get_config()["workers"] = 1
        get_config()["source_w_multiple_choice"] = False
        get_config()["masks"] = "+Ending Disk#\n" + r'"(\s?_disk\d)$"' + "\n"
        masks.FileMasked.masks = masks.CompileMasks(get_config()["masks"])
        filters.FileFiltered.filters = filters.CompileFilters(get_config()["filters"])

        if os.path.exists(self.outdir):
            shutil.rmtree(self.outdir)
        shutil.copytree(os.path.abspath(os.path.join(os.path.dirname(__file__), "./data")), self.outdir)
        sourcesDir = os.path.join(self.outdir, "sources_multimatch")
        choicesDir = os.path.join(self.outdir, "choices_multimatch")
        args.theArgs = args.theArgsParser.parse_args(["--sources", sourcesDir, "--choices", choicesDir, "preview_rename"])

        with io.StringIO() as buf, redirect_stdout(buf):
            frame = main_dlg.MainFrame()
            shutil.rmtree(self.outdir)
            output = buf.getvalue()
            self.maxDiff = None
            self.assertEqual(
                "Renaming : "
                + os.path.join(sourcesDir, "Acanthe à feuilles molles_disk2.txt")
                + " --> "
                + os.path.join(sourcesDir, "Acanthus mollis_disk2.txt\n")
                + "Renaming : "
                + os.path.join(sourcesDir, "Acanthe épineuse.txt")
                + " --> "
                + os.path.join(sourcesDir, "Acanthus spinosus.txt\n")
                + "Renaming : "
                + os.path.join(sourcesDir, "Aconit vénéneux.txt")
                + " --> "
                + os.path.join(sourcesDir, "Aconitum anthora.txt\n")
                + "Renaming : "
                + os.path.join(sourcesDir, "Aconit vénéneux_disk1.txt")
                + " --> "
                + os.path.join(sourcesDir, "Aconitum anthora_disk1.txt\n")
                + "Renaming : "
                + os.path.join(sourcesDir, "Aconit vénéneux_disk3.txt")
                + " --> "
                + os.path.join(sourcesDir, "Aconitum anthora_disk3.txt\n")
                + "Renaming : "
                + os.path.join(sourcesDir, "Violette cornue_disk1.txt")
                + " --> "
                + os.path.join(sourcesDir, "Viola cornuta_disk1.txt\n")
                + "Renaming : "
                + os.path.join(sourcesDir, "Volutaire à fleurs tubulées_disk1.txt")
                + " --> "
                + os.path.join(sourcesDir, "Volutaria tubuliflora_disk1.txt\n"),
                output,
            )

    def test_args_rename(self):
        get_config()["workers"] = 1
        get_config()["keep_original"] = False
        get_config()["masks"] = "+Ending Disk#\n" + r'"(\s?_disk\d)$"' + "\n"
        masks.FileMasked.masks = masks.CompileMasks(get_config()["masks"])
        filters.FileFiltered.filters = filters.CompileFilters(get_config()["filters"])

        if os.path.exists(self.outdir):
            shutil.rmtree(self.outdir)
        shutil.copytree(os.path.abspath(os.path.join(os.path.dirname(__file__), "./data")), self.outdir)
        sourcesDir = os.path.join(self.outdir, "sources_multimatch")
        choicesDir = os.path.join(self.outdir, "choices_multimatch")
        args.theArgs = args.theArgsParser.parse_args(["--sources", sourcesDir, "--choices", choicesDir, "rename"])

        with io.StringIO() as buf, redirect_stdout(buf):
            frame = main_dlg.MainFrame()
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
                    "Acanthus mollis_disk2.txt",
                    "Acanthus spinosus_disk1.txt",
                    "Acanthus spinosus_disk2.txt",
                    "Aconitum anthora.txt",
                    "Aconitum anthora_disk1.txt",
                    "Aconitum anthora_disk2.txt",
                    "Aconitum anthora_disk3.txt",
                    "Viola cornuta_disk1.txt",
                    "Volutaria tubuliflora_disk1.txt",
                ],
                renamed,
            )


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()

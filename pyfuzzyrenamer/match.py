import fuzzywuzzy.fuzz
import fuzzywuzzy.process
import wx
from multiprocessing import Pool, active_children

from pyfuzzyrenamer import config, main_dlg, masks


class FileMatch:
    def __init__(self, file, match_results):
        self.file = file
        self.match_results = match_results


def mySimilarityScorer(s1, s2):
    return fuzzywuzzy.fuzz.WRatio(s1, s2, force_ascii=False, full_process=False)


def fuzz_processor(file):
    if type(file).__name__ == "FileFiltered":
        return file.filtered
    elif type(file).__name__ == "FileMasked":
        return file.masked[1]


def match_process(idx, f_masked, f_candidates):
    data = fuzzywuzzy.process.extract(
        f_masked,
        f_candidates,
        scorer=mySimilarityScorer,
        processor=fuzz_processor,
        limit=10,
    )
    m = FileMatch(f_masked.file, data)
    return idx, m


def get_matches(sources):
    global processed
    processed = 0
    total = len(sources)
    ret = [None for i in range(total)]
    if not main_dlg.candidates:
        return ret

    def callback_processed(data):
        global processed
        processed += 1
        ret[data[0]] = data[1]

    def progress_msg(added, processed, total):
        return "Processed sources %d%%\nAdded sources %d%%" % (
            100 * (processed / total),
            100 * (added / total),
        )

    progress = wx.ProgressDialog(
        "Match Progress",
        "Processed sources    %\nAdded sources    %",
        maximum=len(sources),
        parent=None,
        style=wx.PD_AUTO_HIDE
        | wx.PD_CAN_ABORT
        | wx.PD_ESTIMATED_TIME
        | wx.PD_REMAINING_TIME,
    )
    Qmatch_firstletter = config.theConfig["match_firstletter"]
    added = 0
    if config.theConfig["workers"] > 1:
        pool = Pool(processes=config.theConfig["workers"])
        for f in sources:
            f_masked = masks.FileMasked(f)
            if not f_masked.masked[1]:
                ret[added] = None
                continue
            if Qmatch_firstletter:
                first_letter = f_masked.masked[1][0]
                if first_letter in main_dlg.candidates.keys():
                    pool.apply_async(
                        match_process,
                        (added, f_masked, main_dlg.candidates[first_letter],),
                        callback=callback_processed,
                    )
                else:
                    ret[added] = None
            else:
                pool.apply_async(
                    match_process,
                    (added, f_masked, main_dlg.candidates["all"],),
                    callback=callback_processed,
                )
            added += 1
            cancelled = not progress.Update(
                processed, progress_msg(added, processed, total)
            )[0]
            if cancelled:
                pool.terminate()
                break
        pool.close()
        while len(active_children()) > 0:
            cancelled = not progress.Update(
                processed, progress_msg(added, processed, total)
            )[0]
            if cancelled:
                pool.terminate()
                break
            wx.MilliSleep(1000)
        pool.join()
    else:
        for f in sources:
            f_masked = masks.FileMasked(f)
            if not f_masked.masked[1]:
                ret[added] = None
                continue
            if Qmatch_firstletter:
                first_letter = f_masked.masked[1][0]
                if first_letter in main_dlg.candidates.keys():
                    ret[added] = FileMatch(
                        f_masked.file,
                        fuzzywuzzy.process.extract(
                            f_masked,
                            main_dlg.candidates[first_letter],
                            scorer=mySimilarityScorer,
                            processor=fuzz_processor,
                            limit=10,
                        ),
                    )
                else:
                    ret[added] = None
            else:
                ret[added] = FileMatch(
                    f_masked.file,
                    fuzzywuzzy.process.extract(
                        f_masked,
                        main_dlg.candidates["all"],
                        scorer=mySimilarityScorer,
                        processor=fuzz_processor,
                        limit=10,
                    ),
                )
            added += 1
            processed += 1
            cancelled = not progress.Update(
                processed, progress_msg(added, processed, total)
            )[0]
            if cancelled:
                break

    return ret


def get_match(source):
    ret = None
    if not main_dlg.candidates:
        return ret
    f_masked = masks.FileMasked(source)
    if not f_masked.masked[1]:
        return ret

    if config.theConfig["match_firstletter"]:
        first_letter = f_masked.masked[1][0]
        if first_letter in main_dlg.candidates.keys():
            ret = fuzzywuzzy.process.extract(
                f_masked,
                main_dlg.candidates[first_letter],
                scorer=mySimilarityScorer,
                processor=fuzz_processor,
                limit=10,
            )
    else:
        ret = fuzzywuzzy.process.extract(
            f_masked,
            main_dlg.candidates["all"],
            scorer=mySimilarityScorer,
            processor=fuzz_processor,
            limit=10,
        )
    return ret

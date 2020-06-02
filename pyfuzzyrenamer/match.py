import fuzzywuzzy.fuzz
import fuzzywuzzy.process

from pyfuzzyrenamer import main_dlg, masks, taskserver
from pyfuzzyrenamer.config import get_config


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


class TaskMatch:
    def __init__(self, args):
        pass

    def calculate(self, args):
        if not args:
            return []
        f_masked, f_candidates = args
        data = fuzzywuzzy.process.extract(
            f_masked, f_candidates, scorer=mySimilarityScorer, processor=fuzz_processor, limit=10,
        )
        return FileMatch(f_masked.file, data)


def progress_msg(j, numtasks, output):
    try:
        return "Processed sources %d%%" % (100.0 * (float(j + 1) / float(numtasks)),)
    except ZeroDivisionError:
        return "Processed sources..."


def get_matches(sources):

    numtasks = len(sources)

    # Create the task list
    Tasks = [((), ()) for i in range(numtasks)]
    Results = [None for i in range(numtasks)]
    if not main_dlg.candidates:
        return Results

    Qmatch_firstletter = get_config()["match_firstletter"]
    for i in range(numtasks):
        f_masked = masks.FileMasked(sources[i])
        if f_masked.masked[1]:
            if Qmatch_firstletter:
                first_letter = f_masked.masked[1][0]
                if first_letter in main_dlg.candidates.keys():
                    Tasks[i] = (
                        (),
                        (f_masked, main_dlg.candidates[first_letter],),
                    )
            else:
                Tasks[i] = (
                    (),
                    (f_masked, main_dlg.candidates["all"],),
                )

    numproc = get_config()["workers"]

    ts = taskserver.TaskServerMP(
        processCls=TaskMatch, numprocesses=numproc, tasks=Tasks, results=Results, msgfunc=progress_msg, title="Match Progress"
    )
    ts.run()

    return Results


def get_match_standalone(source, candidates, match_firstletter):
    ret = None
    if not candidates:
        return ret
    f_masked = masks.FileMasked(source)
    if not f_masked.masked[1]:
        return ret

    if match_firstletter:
        first_letter = f_masked.masked[1][0]
        if first_letter in candidates.keys():
            ret = fuzzywuzzy.process.extract(
                f_masked, candidates[first_letter], scorer=mySimilarityScorer, processor=fuzz_processor, limit=10,
            )
    else:
        ret = fuzzywuzzy.process.extract(
            f_masked, candidates["all"], scorer=mySimilarityScorer, processor=fuzz_processor, limit=10,
        )
    return ret


def get_match(source):
    return get_match_standalone(source, main_dlg.candidates, get_config()["match_firstletter"])

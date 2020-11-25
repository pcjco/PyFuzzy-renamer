import fuzzywuzzy.fuzz
import fuzzywuzzy.process
from pathlib import Path

from pyfuzzyrenamer import main_dlg, masks, taskserver, utils
from pyfuzzyrenamer.config import get_config
from pyfuzzyrenamer.args import get_args


def mySimilarityScorer1(s1, s2):
    return fuzzywuzzy.fuzz.WRatio(s1, s2, force_ascii=False, full_process=True)

def mySimilarityScorer2(s1, s2):
    return fuzzywuzzy.fuzz.QRatio(s1, s2, force_ascii=False, full_process=True)

def mySimilarityScorer3(s1, s2):
    return fuzzywuzzy.fuzz.partial_ratio(s1, s2)

def mySimilarityScorer4(s1, s2):
    return fuzzywuzzy.fuzz.token_sort_ratio(s1, s2, force_ascii=False, full_process=True)

def mySimilarityScorer5(s1, s2):
    return fuzzywuzzy.fuzz.partial_token_sort_ratio(s1, s2, force_ascii=False, full_process=True)

def mySimilarityScorer6(s1, s2):
    return fuzzywuzzy.fuzz.token_set_ratio(s1, s2, force_ascii=False, full_process=True)

def mySimilarityScorer7(s1, s2):
    return fuzzywuzzy.fuzz.partial_token_set_ratio(s1, s2, force_ascii=False, full_process=True)

similarityScorers = [
    mySimilarityScorer1,
    mySimilarityScorer2,
    mySimilarityScorer3,
    mySimilarityScorer4,
    mySimilarityScorer5,
    mySimilarityScorer6,
    mySimilarityScorer7,
    ]

def fuzz_processor(file):
    t = type(file).__name__
    if t == "str":
        return file
    elif t == "FileMasked":
        # masked = [pre, middle, post]
        return file.masked[1]
    elif t == "FileFiltered":
        return file.filtered


class TaskMatch:
    def __init__(self, args):
        pass

    def calculate(self, args):
        if not args:
            return []
        f_masked, sources, f_candidates, similarityscorer = args
        match_results = fuzzywuzzy.process.extract(
            f_masked, f_candidates, scorer=similarityScorers[similarityscorer], processor=fuzz_processor, limit=10,
        )
        # [(candidate_key_1, score1), (candidate_key_2, score2), ...]
        return match_results


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
    similarityscorer = get_config()["similarityscorer"]
    for i in range(numtasks):
        f_masked = masks.FileMasked(sources[i][0])
        if f_masked.masked[1]:
            if Qmatch_firstletter:
                first_letter = f_masked.masked[1][0]
                if first_letter in main_dlg.candidates.keys():
                    Tasks[i] = (
                        (),
                        (f_masked, sources[i], list(main_dlg.candidates[first_letter].keys()),similarityscorer,),
                    )
            else:
                Tasks[i] = (
                    (),
                    (f_masked, sources[i], list(main_dlg.candidates["all"].keys()),similarityscorer,),
                )

    numproc = get_config()["workers"]

    if not get_args().mode:
        ts = taskserver.TaskServerMP(
            processCls=TaskMatch,
            numprocesses=numproc,
            tasks=Tasks,
            results=Results,
            msgfunc=progress_msg,
            title="Match Progress",
        )
    else:
        updatefunc_ = None
        if get_args().mode == "report_match":
            updatefunc_ = update_console
        ts = taskserver.TaskServerMP(
            processCls=TaskMatch, numprocesses=numproc, tasks=Tasks, results=Results, updatefunc=updatefunc_, progress=False
        )
    ts.run()

    # [ [{"key": candidate_key_1, "files_filtered": [...], "score":score1]}, {"key": candidate_key_2, "files_filtered": [...], "score":score2}, ...], ...]
    for i in range(numtasks):
        if Results[i]:
            Results[i] = [
                {"key": canditate_key, "files_filtered": main_dlg.candidates["all"][canditate_key], "score": score}
                for canditate_key, score in Results[i]
            ]
    return Results


def update_console(output, msgfunc=None):
    if not output["args"] or not output["result"]:
        return
    Qview_fullpath = get_config()["show_fullpath"]
    Qhide_extension = get_config()["hide_extension"]
    f_masked = output["args"][0].masked[1]
    print_source = f_masked

    canditate_key, score = output["result"][0]
    print_match = canditate_key
    print("%s --> %s (%.2f)" % (print_source, print_match, score))


def get_match_standalone(source, candidates, match_firstletter):
    ret = None
    if not candidates:
        return ret
    f_masked = masks.FileMasked(source[0])
    if not f_masked.masked[1]:
        return ret

    if match_firstletter:
        first_letter = f_masked.masked[1][0]
        if first_letter in candidates.keys():
            ret = fuzzywuzzy.process.extract(
                f_masked, candidates[first_letter].keys(), scorer=similarityScorers[get_config()["similarityscorer"]], processor=fuzz_processor, limit=10,
            )
    else:
        ret = fuzzywuzzy.process.extract(
            f_masked, candidates["all"].keys(), scorer=similarityScorers[get_config()["similarityscorer"]], processor=fuzz_processor, limit=10,
        )

    # [{"key": candidate_key_1, "files_filtered": [...], "score":score1}, {"key": candidate_key_2: "files_filtered": [...], "score":score2}, ...]
    if ret:
        ret = [
            {"key": canditate_key, "files_filtered": candidates["all"][canditate_key], "score": score}
            for canditate_key, score in ret
        ]
    return ret


def get_match(source):
    return get_match_standalone(source, main_dlg.candidates, get_config()["match_firstletter"])

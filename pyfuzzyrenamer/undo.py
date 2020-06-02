import os
import shutil
from pathlib import Path

from pyfuzzyrenamer import main_dlg, taskserver, match, masks, filters
from pyfuzzyrenamer.config import get_config


class TaskUndo:
    def __init__(self, args):
        pass

    def calculate(self, args):
        retcode = 0
        new_path = None
        msg = ""
        if not args:
            retcode = 2
            return {"retcode": retcode, "msg": msg, "similarity": None}

        old_file, new_file, matchname = args
        try:
            os.rename(old_file, new_file)
            new_path = Path(new_file)
            similarity = match.mySimilarityScorer(
                masks.FileMasked(new_path).masked[1], filters.FileFiltered(matchname).filtered,
            )
            msg = "Renaming : %s --> %s" % (old_file, new_file)
        except (OSError, IOError):
            retcode = 1
            msg = "Error when renaming : %s --> %s" % (old_file, new_file)
        return {"retcode": retcode, "msg": msg, "similarity": similarity}


def progress_msg(j, numtasks, output):
    try:
        return "Processed sources %d%%" % (100.0 * (float(j + 1) / float(numtasks)),)
    except ZeroDivisionError:
        return "Processed sources..."


def get_undos(old, new, matchnames):

    numtasks = len(old)

    # Create the task list
    Tasks = [((), ()) for i in range(numtasks)]
    Results = [None for i in range(numtasks)]

    for i in range(numtasks):
        old_path = old[i]
        new_path = new[i]
        matchname = matchnames[i]
        if new_path == None:
            continue
        if old_path == new_path:
            continue
        old_file = str(old_path)
        new_file = str(new_path)
        if new_file == ".":
            continue
        if not old_path.is_file():
            continue
        Tasks[i] = (
            (),
            (old_file, new_file, matchname,),
        )

    numproc = get_config()["workers"]

    ts = taskserver.TaskServerMP(
        processCls=TaskUndo, numprocesses=numproc, tasks=Tasks, results=Results, msgfunc=progress_msg, title="Undo Progress",
    )
    ts.run()

    return Results

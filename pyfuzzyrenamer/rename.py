import os
import shutil
from pathlib import Path

from pyfuzzyrenamer import main_dlg, taskserver, match
from pyfuzzyrenamer.config import get_config


class TaskRename:
    def __init__(self, args):
        pass

    def calculate(self, args):
        retcode = 0
        new_match = None
        new_path = None
        msg = ""
        if not args:
            retcode = 2
            return {"retcode": retcode, "msg": msg, "new_path": new_path, "new_match": new_match}

        old_file, new_file, Qkeep_original, Qmatch_firstletter, candidates = args
        try:
            if Qkeep_original:
                shutil.copy2(old_file, new_file)
                msg = "Copying : %s --> %s" % (old_file, new_file)
            else:
                os.rename(old_file, new_file)
                msg = "Renaming : %s --> %s" % (old_file, new_file)
            new_path = Path(new_file)
            new_match = match.get_match_standalone(new_path, candidates, Qmatch_firstletter)
        except (OSError, IOError):
            retcode = 1
            msg = "Error when renaming : %s --> %s" % (old_file, new_file)
        return {"retcode": retcode, "msg": msg, "new_path": new_path, "new_match": new_match}


def progress_msg(j, numtasks, output):
    try:
        return "Processed sources %d%%" % (100.0 * (float(j + 1) / float(numtasks)),)
    except ZeroDivisionError:
        return "Processed sources..."


def get_renames(old, preview):

    numtasks = len(old)

    # Create the task list
    Tasks = [((), ()) for i in range(numtasks)]
    Results = [None for i in range(numtasks)]

    Qkeep_original = get_config()["keep_original"]
    Qmatch_firstletter = get_config()["match_firstletter"]
    for i in range(numtasks):
        old_path = old[i]
        preview_path = preview[i]
        if old_path == preview_path:
            continue
        old_file = str(old_path)
        new_file = str(preview_path)
        if new_file == ".":
            continue
        if not old_path.is_file():
            continue
        Tasks[i] = (
            (),
            (old_file, new_file, Qkeep_original, Qmatch_firstletter, main_dlg.candidates,),
        )

    numproc = get_config()["workers"]

    ts = taskserver.TaskServerMP(
        processCls=TaskRename,
        numprocesses=numproc,
        tasks=Tasks,
        results=Results,
        msgfunc=progress_msg,
        title="Rename Progress",
    )
    ts.run()

    return Results

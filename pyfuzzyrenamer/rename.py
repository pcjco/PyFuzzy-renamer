import os
import shutil
from pathlib import Path

from pyfuzzyrenamer import taskserver, main_dlg, match, masks, utils
from pyfuzzyrenamer.config import get_config

history = []


class TaskRename:
    def __init__(self, args):
        pass

    def calculate(self, args):
        retcode = []
        msg = []
        history = []
        old_pathes, previews_pathes, Qkeep_original = args
        for old_path, preview_pathes in zip(old_pathes, previews_pathes):
            old_file = str(old_path)
            if not old_path.is_file():
                retcode.append(1)
                msg.append("Cannot find file : %s" % old_file)
                history.append(None)
                continue
            Qrenamed = False
            for preview_path in preview_pathes:
                new_file = str(preview_path)
                if old_file == new_file:
                    continue
                try:
                    if Qkeep_original or Qrenamed:
                        msg.append("Copying : %s --> %s" % (old_file, new_file))
                        history.append({"type": "copy", "to": new_file})
                        shutil.copy2(old_file, new_file)
                    else:
                        msg.append("Renaming : %s --> %s" % (old_file, new_file))
                        history.append({"type": "rename", "from": old_file, "to": new_file})
                        os.rename(old_file, new_file)
                        Qrenamed = True
                        old_file = new_file
                    retcode.append(0)
                except (OSError, IOError):
                    retcode.append(1)
        return {"retcode": retcode, "msg": msg, "history": history}


def progress_msg(j, numtasks, output):
    try:
        return "Processed sources %d%%" % (100.0 * (float(j + 1) / float(numtasks)),)
    except ZeroDivisionError:
        return "Processed sources..."


def get_renames(old_pathes, preview_pathes):

    numtasks = len(old_pathes)

    # Create the task list
    Tasks = [((), ()) for i in range(numtasks)]
    Results = [None for i in range(numtasks)]

    Qkeep_original = get_config()["keep_original"]
    for i in range(numtasks):
        Tasks[i] = (
            (),
            (old_pathes[i], preview_pathes[i], Qkeep_original),
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

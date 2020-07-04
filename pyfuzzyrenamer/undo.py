import os
import shutil
from pathlib import Path

from pyfuzzyrenamer import main_dlg, taskserver, match, masks, filters, rename
from pyfuzzyrenamer.config import get_config


class TaskUndo:
    def __init__(self, args):
        pass

    def calculate(self, args):
        retcode = 0
        msg = []
        ren = args[0]
        if ren["type"] == "rename":
            try:
                os.rename(ren["to"], ren["from"])
                msg.append("Renaming : %s --> %s" % (ren["to"], ren["from"]))
            except (OSError, IOError):
                retcode = 1
                msg.append("Error when renaming : %s --> %s" % (ren["to"], ren["from"]))
        elif ren["type"] == "copy":
            try:
                os.remove(ren["to"])
                msg.append("Removing : %s" % (ren["to"]))
            except (OSError, IOError):
                retcode = 1
                msg.append("Error when removing : %s" % (ren["to"]))
        return {"retcode": retcode, "msg": msg}


def progress_msg(j, numtasks, output):
    try:
        return "Processed sources %d%%" % (100.0 * (float(j + 1) / float(numtasks)),)
    except ZeroDivisionError:
        return "Processed sources..."


def get_undos():

    numtasks = len(rename.history)

    # Create the task list
    Tasks = [((), ()) for i in range(numtasks)]
    Results = [None for i in range(numtasks)]

    for i in range(numtasks):
        Tasks[i] = (
            (),
            (rename.history[i],),
        )

    numproc = get_config()["workers"]

    ts = taskserver.TaskServerMP(
        processCls=TaskUndo, numprocesses=numproc, tasks=Tasks, results=Results, msgfunc=progress_msg, title="Undo Progress",
    )
    ts.run()

    return Results

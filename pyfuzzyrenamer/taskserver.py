from pyfuzzyrenamer.config import get_config

import time
import types
import wx
from multiprocessing import Process, Queue, current_process


class Dispatcher:
    """
    The Dispatcher class manages the task and result queues.
    """

    def __init__(self):
        """
        Initialise the Dispatcher.
        """
        self.taskQueue = Queue()
        self.resultQueue = Queue()

    def putTask(self, task):
        """
        Put a task on the task queue.
        """
        self.taskQueue.put(task)

    def getTask(self):
        """
        Get a task from the task queue.
        """
        return self.taskQueue.get()

    def putResult(self, output):
        """
        Put a result on the result queue.
        """
        self.resultQueue.put(output)

    def getResult(self):
        """
        Get a result from the result queue.
        """
        return self.resultQueue.get()


class TaskServerMP:
    """
    The TaskServerMP class provides a target worker class method for queued processes.
    """

    def __init__(self, processCls, numprocesses=1, tasks=[], results=[], updatefunc=None, msgfunc=None, title="Progress"):
        """
        Initialise the TaskServerMP and create the dispatcher and processes.
        """
        self.numprocesses = numprocesses
        self.Tasks = tasks
        self.Results = results
        self.numtasks = len(tasks)
        self.updatefunc = updatefunc
        self.msgfunc = msgfunc

        # Create the dispatcher
        self.dispatcher = Dispatcher()

        self.Processes = []

        # The worker processes must be started here!
        for n in range(numprocesses):
            process = Process(target=TaskServerMP.worker, args=(self.dispatcher, processCls,))
            process.start()
            self.Processes.append(process)

        self.timeStart = 0.0
        self.timeElapsed = 0.0
        self.timeRemain = 0.0
        self.processTime = {}

        # Set some program flags
        self.keepgoing = True
        self.i = 0
        self.j = 0

        if isinstance(msgfunc, (types.FunctionType, types.MethodType)):
            msg = msgfunc(0, self.numtasks, None)
        else:
            msg = "Complete: %2d / %2d" % (0, self.numtasks)
        self.progress = wx.ProgressDialog(
            title,
            msg
            + "\nTime Elapsed: %s\nRemaining: %s"
            % (time.strftime("%M:%S", time.gmtime(self.timeElapsed)), time.strftime("%M:%S", time.gmtime(self.timeRemain))),
            maximum=self.numtasks,
            parent=None,
            style=wx.PD_AUTO_HIDE | wx.PD_CAN_ABORT,
        )

    def processTasks(self, resfunc=None, msgfunc=None):
        """
        Start the execution of tasks by the processes.
        """
        self.keepgoing = True

        self.timeStart = time.time()
        # Set the initial process time for each
        for n in range(self.numprocesses):
            pid_str = "%d" % self.Processes[n].pid
            self.processTime[pid_str] = 0.0

        # Submit first set of tasks
        if self.numprocesses == 0:
            numprocstart = 1
        else:
            numprocstart = min(self.numprocesses, self.numtasks)
        for self.i in range(numprocstart):
            self.dispatcher.putTask((self.i,) + self.Tasks[self.i])

        self.j = -1
        self.i = numprocstart - 1
        while self.j < self.i:
            # Get and print results
            output = self.getOutput()
            # Execute some function (Yield to a wx.Button event)
            if isinstance(resfunc, (types.FunctionType, types.MethodType)):
                resfunc(output, msgfunc)
            if (self.keepgoing) and (self.i + 1 < self.numtasks):
                # Submit another task
                self.i += 1
                self.dispatcher.putTask((self.i,) + self.Tasks[self.i])

    def processStop(self, resfunc=None):
        """
        Stop the execution of tasks by the processes.
        """
        self.keepgoing = False

        while self.j < self.i:
            # Get and print any results remining in the done queue
            output = self.getOutput()
            if isinstance(resfunc, (types.FunctionType, types.MethodType)):
                resfunc(output)

    def processTerm(self):
        """
        Stop the execution of tasks by the processes.
        """
        for n in range(self.numprocesses):
            # Terminate any running processes
            self.Processes[n].terminate()

        # Wait for all processes to stop
        while self.anyAlive():
            time.sleep(0.5)

    def anyAlive(self):
        """
        Check if any processes are alive.
        """
        isalive = False
        for n in range(self.numprocesses):
            isalive = isalive or self.Processes[n].is_alive()
        return isalive

    def getOutput(self):
        """
        Get the output from one completed task.
        """
        self.j += 1

        if self.numprocesses == 0:
            # Use the single-process method
            self.worker_sp()

        output = self.dispatcher.getResult()
        self.Results[output["num"]] = output["result"]

        # Calculate the time remaining
        self.timeRemaining(self.j + 1, self.numtasks, output["process"]["pid"])

        return output

    def timeRemaining(self, tasknum, numtasks, pid):
        """
        Calculate the time remaining for the processes to complete N tasks.
        """
        timeNow = time.time()
        self.timeElapsed = timeNow - self.timeStart

        pid_str = "%d" % pid
        self.processTime[pid_str] = self.timeElapsed

        # Calculate the average time elapsed for all of the processes
        timeElapsedAvg = 0.0
        numprocesses = self.numprocesses
        if numprocesses == 0:
            numprocesses = 1
        for pid_str in self.processTime.keys():
            timeElapsedAvg += self.processTime[pid_str] / numprocesses
        self.timeRemain = timeElapsedAvg * (float(numtasks) / float(tasknum) - 1.0)

    def worker(cls, dispatcher, processCls):
        """
        The worker creates a processCls object to calculate the result.
        """
        while True:
            args = dispatcher.getTask()
            taskproc = processCls(args[1])
            result = taskproc.calculate(args[2])
            output = {
                "process": {"name": current_process().name, "pid": current_process().pid},
                "num": args[0],
                "result": result,
            }
            # Put the result on the output queue
            dispatcher.putResult(output)

    # The multiprocessing worker must not require any existing object for execution!
    worker = classmethod(worker)

    def worker_sp(self, processCls):
        """
        A single-process version of the worker method.
        """
        args = self.dispatcher.getTask()
        taskproc = processCls(args[1])
        result = taskproc.calculate(args[2])
        output = {"process": {"name": "Process-0", "pid": 0}, "num": args[0], "result": result}
        # Put the result on the output queue
        self.dispatcher.putResult(output)

    def update(self, output, msgfunc=None):
        """
        Get and print the results from one completed task.
        """
        if self.progress:
            if isinstance(msgfunc, (types.FunctionType, types.MethodType)):
                msg = msgfunc(self.j + 1, self.numtasks, output)
            else:
                msg = "Complete: %2d / %2d" % (self.j + 1, self.numtasks)
            cancelled = not self.progress.Update(
                self.j + 1,
                msg
                + "\nTime Elapsed: %s\nRemaining: %s"
                % (
                    time.strftime("%M:%S", time.gmtime(self.timeElapsed)),
                    time.strftime("%M:%S", time.gmtime(self.timeRemain)),
                ),
            )[0]
        if cancelled:
            # Stop processing tasks
            self.processStop()
            self.progress = None

    def run(self):
        """
        Run the TaskServerMP - start, stop & terminate processes.
        """
        self.processTasks(self.updatefunc or self.update, self.msgfunc)
        if self.numprocesses > 0:
            self.processTerm()

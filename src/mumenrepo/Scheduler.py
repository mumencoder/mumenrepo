
from .common_imports import *
from .File import *
from .WorkflowReport import *
from .Task import *

class Scheduler(object):
    @staticmethod
    def init(env):
        env.attr.scheduler.runnables = set()
        env.attr.scheduler.pending = set()

        env.attr.tasks.all_names = {}

        top_task = Task.nop(env, tags={'action':'top'})
        env.attr.scheduler.top_task = top_task
        env.attr.scheduler.top_task.initialize(env)
        Scheduler.schedule( env, top_task )

        report_task = Scheduler.task_workflow_report(env)
        report_task.initialize(env)
        Scheduler.schedule( env, report_task )

    @staticmethod
    def deinit(env):
        for runnable in env.attr.scheduler.runnables:
            runnable.cleanup()

    @staticmethod
    def task_workflow_report(env):
        async def workflow_report(penv, senv):
            def write_reports():
                with File.open(penv.attr.workflow.report_path, "w") as f:
                    f.write( str(WorkflowReport.all_workflows(penv)) )
            try:
                while penv.attr.scheduler.running:
                    write_reports()
                    for i in range(0,30):
                        if penv.attr.scheduler.running is False:
                            break
                        await asyncio.sleep(1.0)
                write_reports()
            except:
                write_reports()
        return Task(env, workflow_report, ptags={'action':'workflow_report'}, background=True)

    @staticmethod
    def create_flow(env, runnable):
        pass

    @staticmethod 
    def schedule(env, runnable):
        scheduler = env.prefix('.scheduler')

        if runnable.started():
            raise Exception("runnable already started", runnable.name)
        if runnable in scheduler.runnables:
            raise Exception("runnable is already scheduled", runnable)

        runnable.start()
        scheduler.runnables.add( runnable )

    @staticmethod
    async def run(env):
        scheduler = env.prefix('.scheduler')

        scheduler.running = True
        running = True

        while running:
            awaitables = []
            for runnable in scheduler.runnables:
                for awaitable in runnable.get_awaitables():
                    awaitables.append( awaitable )
            try:
                for awaitable in asyncio.as_completed( awaitables, timeout=1.0 ):
                    await awaitable
            except asyncio.TimeoutError:
                pass

            for pending in scheduler.pending:
                scheduler.runnables.add( pending )
            scheduler.pending = set()

            running = False
            new_runnables = set()
            for runnable in scheduler.runnables:
                if not runnable.finished():
                    new_runnables.add(runnable)
            for runnable in new_runnables:
                if runnable.background is False:
                    running = True

            scheduler.runnables = new_runnables

        scheduler.running = False
        finished = False
        while not finished:
            finished = True
            for runnable in scheduler.runnables:
                if runnable.finished() is False:
                    finished = False
            await asyncio.sleep(0.2)
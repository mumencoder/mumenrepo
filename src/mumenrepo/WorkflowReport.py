
from .common_imports import *

class WorkflowReport(object):
    @staticmethod
    def common(doc):
        with doc:
            stylesheet = textwrap.dedent(
                """
                table td {
                    border: 1px solid black;
                    text-align: center;
                }

                horiz_list {
                    display: inline-block;
                }
                """)

        with doc.head:
            style(raw(stylesheet))

    @staticmethod
    def log(wf):
        doc = dom.document(title='WF Log')
        WorkflowReport.common(doc)

        with doc:
            for entry in wf.log:
                hr()
                if entry['type'] == "text":
                    div(pre(code(entry["text"])), cls="text")
                elif entry['type'] == "shell":
                    penv = entry['env']
                    pre(code( "shell command: " + penv.attr.shell.command ) )
                    if penv.attr_exists(".shell.dir"):
                        pre(code( "working dir: " + str(penv.attr.shell.dir) ) )
                    if penv.attr_exists(".process.log_path"):
                        a( "<Log>", href=f'../../{os.path.relpath(penv.attr.process.log_path, penv.attr.dirs.root)}')
                    br()
                    if penv.attr_exists('.process.p'):
                        pre(code( "result: " + str(penv.attr.process.p.returncode) ))
        return doc

    @staticmethod
    def all_workflows(env):
        doc = dom.document(title='Workflow')
        WorkflowReport.common(doc)

        with doc:
            with table():
                caption("Workflows")
                with tr():
                    th("Task")
                    th("State")
                    th("Status")
                    th("Log")
                for wf in env.attr.workflows:
                    if wf.task.name is None:
                        continue
                    log_td = lambda: td( a("*", href=f"./{wf.log_link}") )
                    tr(td(wf.task.name), td(wf.task.state), td(wf.status[-1]), log_td())

        for wf in env.attr.workflows:
            with open(wf.log_path, "w") as f:
                f.write( str(WorkflowReport.log(wf)) )

        return doc
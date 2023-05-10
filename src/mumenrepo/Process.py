
from .common_imports import *
from .Folder import *

class Process(object):
    ### Inputs
    # .shell.dir - sets current working directory for process
    # .shell.env - environment variables to launch process with
    # .process.stdout - a stream to log process stdout
    # .process.stderr - a stream to log process stderr, if missing will use same stream as .process.stdout
    ### Outputs
    # .process.instance
    # .shell.start_time
    # .shell.finish_time
    ### Notes
    # This can only be called in an environment once, multiple runs with the same inputs must use a freshly branched environment
    @staticmethod
    async def shell(env):
        process = env.prefix('.process')
        shell = env.prefix('.shell')

        if env.has_attr('.process.instance'):
            raise Exception(".process.instance already exists") 
        env.attr.process.instance = None

        if not env.has_attr('.shell.env'):
            raise Exception(".shell.env not set")
        if not env.has_attr('.process.stdout'):
            raise Exception(".process.stdout not set")
        if not env.has_attr( ".process.stderr" ):
            process.stderr = process.stdout
            process.stderr_mode = process.stdout_mode
        if not env.has_attr( ".process.stdout_mode"):
            raise Exception(".process.stdout_mode not set")
        if not env.has_attr( ".process.stderr_mode"):
            raise Exception(".process.stderr_mode not set")

        #await env.send_event("process.initialize", env)
        try:
            if env.has_attr( ".shell.dir" ):
                pushd = shell.dir
            else:
                pushd = os.getcwd()

            with Folder.Push( pushd ):
                #await env.send_event("process.starting", env)
                process.start_time = time.time()
                if process.stdout_mode == "piped":
                    stdout_arg = asyncio.subprocess.PIPE
                else:
                    stdout_arg = process.stdout
                if process.stderr_mode == "piped":
                    stderr_arg = asyncio.subprocess.PIPE
                else:
                    stderr_arg = process.stderr

                process.instance = await asyncio.create_subprocess_shell(shell.command, stdout=stdout_arg, stderr=stderr_arg, env=shell.env)
                #await env.send_event("process.started", env)

                if False:
                    pass
                #if env.event_defined('process.wait'):
                    #await env.send_event("process.wait", env)
                else:
                    while process.instance.returncode is None:
                        try:
                            (stdout, stderr) = await process.instance.communicate()
                            if stdout is not None:
                                process.stdout.write( stdout )
                            if stderr is not None:
                                process.stderr.write( stderr )
                        except subprocess.TimeoutExpired:
                            pass

                process.finish_time = time.time()
                #await env.send_event("process.finished", env)
        finally:
            pass
            #await env.send_event("process.cleanup")

    def pipe_stdout(env):
        env.attr.process.stdout = io.BytesIO()
        env.attr.process.stderr = env.attr.process.stdout
        env.attr.process.stdout_mode = "piped"
        env.attr.process.stderr_mode = "piped"  
    class Manager(object):
        def __init__(self, config):
            self.max_memory_usage = -1
            self.memory_limit = config['process.memory_limit']

        async def cleanup(self):
            if self.state == "kill":
                self.process.kill()
                await asyncio.wait_for(self.process.wait(), None)
            self.finish_time = time.time()

        def is_wait_state(self):
            if self.state == "kill":
                return False
            if self.process.returncode is not None:
                return False
            return True

        async def wait(self):
            while self.is_wait_state():
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=self.update_delay)
                except asyncio.exceptions.TimeoutError:
                    pass
                for update in self.updates:
                    update(self)

        def update(self, process):
            pinfo = process.find_by_tag()
            if len(pinfo) == 0:
                return
            if len(pinfo) > 1:
                raise Exception("non unique process")
            pinfo = pinfo[0]
            try:
                if self.memory_limit is not None and pinfo.memory_full_info().uss > self.memory_limit:
                    process.state = "kill"
                    return
                self.max_memory_usage = max( self.max_memory_usage, pinfo.memory_full_info().uss)
            except psutil.NoSuchProcess:
                pass

    @staticmethod
    def find(name=None, env_tag=None):
        pinfos = []
        scan_items = []
        if name is not None:
            scan_items.append('name')
        if env_tag is not None:
            scan_items.append('environ')

        for p_update in psutil.process_iter(['name']):
            if name is not None and p_update.name() == name:
                pinfos.append( p_update )
            elif env_tag is not None:
                try:
                    env = p_update.environ()
                    k, v = env_tag
                    if k in env and env[k] == v:
                        pinfos.append( p_update ) 
                except psutil.AccessDenied:
                    pass
        return pinfos

    @staticmethod
    def find_by_tag(tag):
        return Process.find( env_tag=('process_tag', tag))
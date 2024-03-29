
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

        await env.attr.process.events.send_event("process.initialize", env)
        try:
            if not env.has_attr( ".shell.dir" ):
                shell.dir = os.getcwd()

            with Folder.Push( shell.dir ):
                process.start_time = time.time()
                if process.stdout_mode == "piped":
                    stdout_arg = asyncio.subprocess.PIPE
                else:
                    stdout_arg = process.stdout
                if process.stderr_mode == "piped":
                    stderr_arg = asyncio.subprocess.PIPE
                else:
                    stderr_arg = process.stderr

                await env.attr.process.events.send_event("process.starting", env)
                if env.has_attr('.shell.command'):
                    process.instance = await asyncio.create_subprocess_shell(shell.command, stdout=stdout_arg, stderr=stderr_arg, env=shell.env)
                else:
                    process.instance = await asyncio.create_subprocess_exec(shell.program, *shell.args, stdout=stdout_arg, stderr=stderr_arg, env=shell.env)

                await env.attr.process.events.send_event("process.started", env)

                while process.instance.returncode is None:
                    await env.attr.process.events.send_event("process.waiting", env)
                    if env.has_attr('.process.try_terminate'):
                        kill_proc = await env.attr.process.try_terminate(env)
                        if kill_proc:
                            process.instance.terminate()
                            try:
                                await asyncio.wait_for( process.instance.wait(), timeout=2.0 )
                            except asyncio.TimeoutError:
                                pass
                            try:
                                process.instance.kill()
                                await process.instance.wait()
                            except:
                                pass
                    try:
                        await asyncio.wait_for( process.instance.wait(), timeout=0.05 )
                    except asyncio.TimeoutError:
                        pass
                    #try:
                    #    co = process.instance.communicate()
                    #    (stdout, stderr) = await asyncio.wait_for( co, timeout=0.05)
                    #    if stdout is not None:
                    #        process.stdout.write( stdout )
                    #    if stderr is not None:
                    #        process.stderr.write( stderr )
                    #except asyncio.TimeoutError:
                    #    pass

                if process.stdout_mode == "piped":
                    process.stdout.write( await process.instance.stdout.read() )
                if process.stderr_mode == "piped":
                    process.stderr.write( await process.instance.stderr.read() )

                process.finish_time = time.time()
                await env.attr.process.events.send_event("process.finished", env)
        finally:
            await env.attr.process.events.send_event("process.cleanup")

    def pipe_stdout(env):
        env.attr.process.stdout = io.BytesIO()
        env.attr.process.stderr = env.attr.process.stdout
        env.attr.process.stdout_mode = "piped"
        env.attr.process.stderr_mode = "piped"  

    @staticmethod
    def limited_process(env, memory_limit=None, time_limit=None):
        if memory_limit:
            try:
                meminfo = psutil.Process( env.attr.process.instance.pid ).memory_info()
                if meminfo.rss > memory_limit:
                    return True
            except psutil.NoSuchProcess:
                pass
        if time_limit:
            if time.time() - env.attr.process.start_time > time_limit:
                return True
        else:
            return False
        
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
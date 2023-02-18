
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

        if env.attr_exists('.process.instance'):
            raise Exception(".process.instance already exists") 
        env.attr.process.instance = None

        if not env.attr_exists('.process.piped'):
            process.piped = False
        if not env.attr_exists('.shell.env'):
            raise Exception(".shell.env not set")
        if not env.attr_exists('.process.stdout'):
            raise Exception(".process.stdout not set")
        if not env.attr_exists( ".process.stderr" ):
            process.stderr = process.stdout

        await env.send_event("process.initialize", env)
        try:
            if env.attr_exists( ".shell.dir" ):
                pushd = shell.dir
            else:
                pushd = os.getcwd()

            with Folder.Push( pushd ):
                await env.send_event("process.starting", env)
                process.start_time = time.time()
                if process.piped:
                    process.instance = await asyncio.create_subprocess_shell(shell.command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=shell.env)
                else:
                    process.instance = await asyncio.create_subprocess_shell(shell.command, stdout=process.stdout, stderr=process.stderr, env=shell.env)
                await env.send_event("process.started", env)

                if env.event_defined('process.wait'):
                    await env.send_event("process.wait", env)
                else:
                    while process.instance.returncode is None:
                        if process.piped:
                            (stdout, stderr) = await process.instance.communicate()
                            process.stdout.write( stdout.decode('ascii') )
                            process.stderr.write( stderr.decode('ascii') )
                        await asyncio.sleep(0.1)


                process.finish_time = time.time()
                await env.send_event("process.finished", env)
        finally:
            await env.send_event("process.cleanup")

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
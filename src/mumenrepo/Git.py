
from .common_imports import *

from .Process import *
from .Folder import *
from .Workflow import *

class Git(object):
    class Repo(object):
        @staticmethod
        async def command(env, command):
            env.attr.shell.dir = env.attr.git.repo.dir
            env.attr.shell.command = command
            await Process.shell(env)
            
        @staticmethod 
        async def clone(env):
            cmd = "git clone "
            if env.attr_exists('.git.repo.clone.depth'):
                cmd += f"--depth {env.attr.git.repo.clone.depth} "
            if env.attr_exists('.git.repo.clone.branch'):
                cmd += f"--branch {env.attr.git.repo.clone.branch} "
            if not env.attr_exists('.git.repo.url'):
                raise Exception("URL not set for ensure")
            cmd += f"{env.attr.git.repo.url} {env.attr.git.repo.dir} "
            penv = env.branch()
            await Git.Repo.command(penv, cmd)

        @staticmethod
        async def status(env):
            cmd = "git status -b --porcelain=v2"
            penv = env.branch()
            await Git.Repo.command(penv, cmd)
            if penv.attr.process.instance.returncode != 0:
                return None
            result = {}
            for line in penv.attr.process.stdout.getvalue().split('\n'):
                if line.startswith("#"):
                    sline = line.split(' ')
                    if len(sline[2:]) == 1:
                        result[sline[1]] = sline[2]
                    else:
                        result[sline[1]] = sline[2:]
            return result

        @staticmethod
        async def submodule_status(env):
            penv = env.branch()
            cmd = "git submodule status "
            await Git.Repo.command(penv, cmd)
            result = {}
            for line in penv.attr.process.stdout.getvalue().split('\n'):
                if len(line) == 0:
                    continue
                sline = line.split(' ')
                if line[0] == "-":
                    result[sline[0][1:]] = "missing"
                else:
                    result[sline[1]] = "ready"
            return result

        @staticmethod
        async def pull(env):
            cmd = "git fetch"
            penv = env.branch()
            await Git.Repo.command(penv, cmd)

        @staticmethod
        async def pull(env):
            cmd = "git pull"
            penv = env.branch()
            await Git.Repo.command(penv, cmd)

        @staticmethod
        async def init_all_submodules(env):
            penv = env.branch()
            cmd = "git submodule update --init --recursive "
            if penv.attr_exists(".git.repo.submodule_ref"):
                cmd += f"--reference {penv.attr.git.repo.submodule_ref} "
            await Git.Repo.command(penv, cmd)

        @staticmethod 
        def commit_history(commit, depth=32):
            q = []
            seen = set()
            i = 0
            while i < depth:
                yield commit
                for c in commit.parents:
                    if c not in seen:
                        seen.add(c)
                        i += 1
                        q.append(c)
                if len(q) == 0:
                    return
                commit = q.pop(0)

        #await Shared.Git.Repo.command(senv, 'git submodule deinit -f --all')
        #await Shared.Git.Repo.command(senv, 'git clean -fdx')

        def search_base_commit(env, start, potential_matches, max_level=32):
            repo = env.attr.git.api.repo
            current_commits = [ repo.commit(start) ]

            while max_level > 0:
                max_level -= 1
                new_current_commits = []
                for commit in current_commits:
                    if str(commit) in potential_matches:
                        return commit
                    new_current_commits += commit.parents
                current_commits = new_current_commits

            return None

        async def resolve_head(env):
            repo = env.attr.git.api.repo
            env.attr.git.ref = repo.heads[ env.attr.git.branch.name ]

        async def ensure_branch(env):
            branch_info = env.attr.git.repo.branch
            repo = env.attr.git.api.repo
            git = env.prefix('.git')

            if git.branch.name not in repo.heads:
                repo.create_head( git.branch.name )

            Git.Repo.resolve_head(env)

            if env.attr_exists('.git.repo.remote'):
                remote = repo.remote( git.remote.name )
                if git.branch.name not in remote.refs:
                    remote.fetch( git.branch.name )
                git.branch.set_tracking_branch( remote.refs[git.branch.name] )
                git.branch.set_commit( remote.refs[git.branch.name] )

            repo.head.reset( git.branch.name, working_tree=True )

            if env.attr_exists('.git.repo.remote'):
                if repo.head.commit != remote.refs[git.branch.name].commit:
                    raise Exception("repo head mismatch")

        @staticmethod
        async def ensure_worktree(env):
            cmd = "git worktree add --force "
            cmd += f'-B {env.attr.git.branch} '
            cmd += f'{env.attr.git.worktree.path} '
            cmd += f'{env.attr.git.worktree.commit}'
            await Git.Repo.command(env, cmd)

        @staticmethod
        async def ref(env, ref, remote=None):
            repo = env.attr.git.api.repo
            if remote is None:
                return repo.refs[ref]
            else:
                return repo.remote(remote).refs[ref]

        @staticmethod
        async def ensure_commit(env):
            repo = env.attr.git.api.repo
            try:
                repo.commit( env.attr.git.commit )
            except ValueError:
                repo.remote(env.attr.git.remote).fetch( env.attr.git.commit )
            env.attr.git.api.commit = repo.commit( env.attr.git.commit )
            
        @staticmethod
        async def freshen(env):
            repo = env.attr.git.api.repo
            repo.head.reset( 'origin/HEAD', working_tree=True )
            repo.remote('origin').pull()

    class AutoStash(object):
        def __init__(self, env):
            self.env = env

        async def __enter__(self):
            await Git.Repo.command(self.env, "git stash push -u")

        async def __exit__(self, exc_type, exc_value, exc_traceback):
            await Git.Repo.command(self.env, "git stash pop")

    @staticmethod
    def nightly_builds(commits):
        nights = collections.defaultdict(list)
        for commit in commits:
            h = tuple( [getattr(commit.committed_datetime, attr) for attr in ["year", "month", "day"]] )
            nights[h].append( commit )
        return [max(commits, key=lambda c: c.committed_date) for commits in nights.values()]

    @staticmethod
    def weekly_builds(commits):
        weeks = collections.defaultdict(list)
        for commit in commits:
            h = tuple( [getattr(commit.committed_datetime, attr) for attr in ["year", "month", "day"]] )
            week = h[0] * 60 + h[1] * 5 + int(h[2] / 7)
            weeks[week].append( commit )
        return [max(commits, key=lambda c: c.committed_date) for commits in weeks.values()]

    ###### repo resources ######
#    class RepoSource(ResourceTracker):
#        def __init__(self, env, base_dir, base_name, limit=None):
#            self.env = env
#            self.base_dir = base_dir
#            self.base_name = base_name
#            super().__init__(limit=limit)

#        def get_resource_data(self, i):
#            data = {"id":i, "copy_name": f'{self.base_name}.copy.{i}'}
#            data["path"] = self.base_dir / data["copy_name"]
#            return data

#        def ensure_exist(self, data):
#            data["path"].ensure_folder()

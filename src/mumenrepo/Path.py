
from .common_imports import *
from .Process import *

class Path(type(pathlib.Path())):
    def __init__(self, path):
        self.ensure_parent_folder()

    def __add__(self, path):
        newpath = Path( super().__truediv__(path) )
        newpath.ensure_folder()
        return newpath

    def __truediv__(self, path):
        newpath = Path( super().__truediv__(path) )
        return newpath

    def ensure_folder(self):
        if not self.exists():
            self.mkdir(parents=True, exist_ok=True)

    def ensure_parent_folder(self):
        if not self.exists():
            self.parent.mkdir(parents=True, exist_ok=True)

    def ensure_clean_dir(self):
        if os.path.exists(self):
            shutil.rmtree(self)
        if not os.path.exists(self):
            os.mkdir(self)

    @staticmethod            
    async def sync_folders(env, src, dest):
        env = env.branch()
        env.attr.shell.command = f"rsync -r {src}/ {dest}"
        await Process.shell(env)

    @staticmethod            
    async def full_sync_folders(env, src, dest):
        env = env.branch()
        env.attr.shell.command = f"rsync --delete -r {src}/ {dest}"
        await Process.shell(env)
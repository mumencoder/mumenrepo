
from .common_imports import *
from .Prefix import *

class File(type(pathlib.Path())):
    def __init__(self, *args, **kwargs):
        self.ensure_folder()

    def ensure_folder(self):
        if not self.parent.exists():
            self.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def open(*args, **kwargs):
        if isinstance(args[0], Prefix):
            raise Exception("attempt to open file from Prefix")
        return open(*args, **kwargs)
        
    @staticmethod
    def stale(source_files, dependent_file):
        dependent_mtime = File.mtime(dependent_file)
        for source_file in source_files:
            if dependent_mtime < File.mtime(source_file):
                return True
        return False

    @staticmethod
    def read_if_exists(file_path, exist_fn=None):
        if os.path.exists(file_path):
            with File.open(file_path) as f:
                if exist_fn:
                    return exist_fn(f.read())
                else:
                    return f.read()
        else:
            return None

    @staticmethod
    def refresh(source_file, dest_file):
        if File.stale([source_file], dest_file):
            pathlib.Path( dest_file ).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy( source_file, dest_file )
            return True
        else:
            return False

    @staticmethod
    def update_symlink(link_from, link_to):
        if os.path.lexists(link_to):
            os.unlink( link_to )
        os.symlink( link_from, link_to )

    @staticmethod
    def mtime(file):
        if os.path.exists(file):
            return os.stat(file).st_mtime
        else:
            return 0
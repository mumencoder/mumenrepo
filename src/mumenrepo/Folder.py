
from .common_imports import *

class Folder:
    class Push(object):
        def __init__(self, folder):
            self.folder = folder

        def __enter__(self):
            self.old_folder = os.getcwd()

            if not os.path.exists(self.folder):
                self.folder.mkdir(parents=True, exist_ok=True)

            os.chdir(self.folder)

        def __exit__(self, exc_type, exc_value, exc_traceback):
            os.chdir(self.old_folder)
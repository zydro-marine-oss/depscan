import os


def cache_root():
    return os.path.join(os.path.expanduser("~"), ".zydro", "depscan")

import pathlib
import os

home = pathlib.Path(os.environ.get('UDAAN_HOME', '/tmp'))
try:
    print("Calling Core")
    import integration.core.set_env
except ImportError:
    print("core/set_env.py not found !")
    pass

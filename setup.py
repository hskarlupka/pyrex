from distutils.core import setup
from distutils.extension import Extension

# Determine whether Cython can be used to decide whether to build from
# .pyx files or premade .c files
try:
    from Cython.Distutils import build_ext
except ImportError:
    print("Cython not found. Will build from .c files rather than .pyx files")
    from distutils.command.build_ext import build_ext
    cython = False
else:
    cython = True


build_modules = ["signals",
                 "antenna",
                 "ice_model",
                 "earth_model",
                 "particle",
                 "ray_tracing",
                 "kernel",
                 "custom"]

if cython:
    suffix = ".pyx"
else:
    suffix = ".c"


ext_modules = [Extension("pyrex."+module, ["pyrex/"+module+suffix])
               for module in build_modules]


cmdclass = {'build_ext': build_ext}

setup(
    name = 'pyrex',
    ext_modules = ext_modules,
    cmdclass = cmdclass
)

# from Cython.Build import cythonize

# setup(
#     ext_modules = cythonize("pyrex/signals.pyx")
# )
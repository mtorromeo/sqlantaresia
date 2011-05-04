"""
py2app/py2exe build script for MyApplication.

Will automatically ensure that all build prerequisites are available
via ez_setup

Usage (Mac OS X):
    python setup.py py2app

Usage (Windows):
    python setup.py py2exe
"""
import sys, os
from setuptools import setup

mainscript = 'bin/sqlantaresia'

if sys.platform == 'darwin':
    extra_options = dict(
        setup_requires=['py2app'],
        app=[mainscript],
        options={"py2app": {
            "argv_emulation": True,
            "includes": ["sip", "PyQt4.QtCore", "PyQt4.QtGui", "PyQt4.Qsci"]
        }},
    )
elif sys.platform == 'win32':
    import py2exe

    origIsSystemDLL = py2exe.build_exe.isSystemDLL
    def isSystemDLL(pathname):
        if os.path.basename(pathname).lower() == "msvcp90.dll":
            return 0
        return origIsSystemDLL(pathname)
    py2exe.build_exe.isSystemDLL = isSystemDLL

    extra_options = dict(
        windows=[{
            "script": mainscript,
            "icon_resources": [(0, "kexi.ico")]
        }],
        options={"py2exe": {
            "optimize": 2,
            "skip_archive": True,
            "includes": ["sip"]
        }}
    )
else:
    extra_options = {}

setup(
    name = "sqlantaresia",
    packages = ["sqlantaresia"],
    scripts = [mainscript],
    version = "0.1",
    author = "Massimiliano Torromeo",
    author_email = "massimiliano.torromeo@gmail.com",
    url = "http://code.google.com/p/sqlantaresia/",
    keywords = ["qt", "pyqt", "desktop", "mysql"],
    classifiers = [
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "License :: OSI Approved :: MIT License",
        "Environment :: X11 Applications :: Qt",
        "Intended Audience :: System Administrators",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Operating System :: POSIX :: BSD",
        "Natural Language :: English",
        "Topic :: Utilities"
    ],
    license = "MIT License",
    **extra_options
)
"""
py2app/py2exe build script for MyApplication.

Will automatically ensure that all build prerequisites are available
via ez_setup

Usage (Mac OS X):
    python setup.py py2app

Usage (Windows):
    python setup.py py2exe
"""
import sys
from setuptools import setup

mainscript = 'SQLAntaresia.py'

if sys.platform == 'darwin':
	extra_options = dict(
		setup_requires=['py2app'],
		app=[mainscript],
		options={"py2app": {
			"argv_emulation": True,
			"includes": ["PyQt4._qt"]
		}},
	)
elif sys.platform == 'win32':
	extra_options = dict(
		setup_requires=['py2exe'],
		windows=[{"script": mainscript}],
		options={"py2exe": {
			"skip_archive": True,
			"includes": ["sip"]
		}}
	)
else:
	extra_options = dict(
		scripts=[mainscript],
	)

setup(
	name="sqlantaresia",
	version="0.1",
	author="Massimiliano Torromeo",
	author_email="massimiliano.torromeo@gmail.com",
	url="http://code.google.com/p/sqlantaresia/",
	license="MIT License",
	**extra_options
)
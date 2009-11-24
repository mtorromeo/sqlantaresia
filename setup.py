from distutils.core import setup
import py2exe

setup(name="sqlantaresia",
	version="0.1",
	author="Massimiliano Torromeo",
	author_email="massimiliano.torromeo@gmail.com",
	url="http://code.google.com/p/sqlantaresia/",
	license="MIT License",
	windows=[{"script": "SQLAntaresia.py"}],
	options={"py2exe": {"skip_archive": True, "includes": ["sip"]}})
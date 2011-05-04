SQLAntaresia
============
SQLAntaresia is a cross platform MySQL management tool aimed at both developers and system administrators with a simple user interface.

.. contents::

Installation
------------
The application should work reasonably well on all the platforms where the dependencies can be satisfied (Linux, \*BSD, OSX, Windows, ...),
but at this point has only been tested on Linux operating systems and Windows XP 32bit.

Packages
''''''''
The code is hosted on `github <http://github.com/mtorromeo/sqlantaresia>`_

Clone command::

	git clone git://github.com/mtorromeo/sqlantaresia.git

Dependencies
''''''''''''
SQLAntaresia is a **python 2.6+** application and it also depends upon the following external libraries:

* PyQt4 (4.6+)
* paramiko
* MySQL-python
* DBUtils
* setproctitle
* PyCrypto (For unix only)

Build instructions
''''''''''''''''''
Before using this applications the Qt forms and icon resources must be compiled.
There is a unix shell script in the root of the distribution package named *build.sh* that takes care of this process::

	cd [SOURCE FOLDER]
	sh build.sh
	bin/sqlantaresia

CHANGELOG
---------

New in version 0.2
''''''''''''''''''
* Better database error handling and reporting

LICENSE
-------
Copyright (c) 2009-2011 Massimiliano Torromeo

SQLAntaresia is free software released under the terms of the MIT license.

See the LICENSE file provided with the source distribution for full details.

Contacts
--------
* Massimiliano Torromeo <massimiliano.torromeo@gmail.com>

SQLAntaresia
============
SQLAntaresia is a cross platform MySQL management tool aimed at both developers and system administrators with a simple user interface.

.. image:: https://lh6.googleusercontent.com/_9wOQn-OcPic/SsTIN9vu7uI/AAAAAAAADpk/oe7JLAAS2aQ/s900/sqlantaresia-screenie.png

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
* PyQt4 QScintilla bindings
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

New in version 0.5
''''''''''''''''''
* The query editor now runs the queries in a separate thread without blocking the GUI and allowing the user to kill them before they finish.
* Display database size in the treeview
* Improved treeview refreshing
* The default query limit for the table details view is now configurable
* Implemented detailed warnings visualization in the query editor
* Implemented table dumps
* Implemented configuration of the mysql protocol compression
* Implemented action toolbar in the query editor to load/save queries from/to files
* Inline editing of rows in the table details view
* Set query editor encoding to UTF-8
* Fixed query execution time calculations

New in version 0.4.2
''''''''''''''''''''
* Add option to hide the idle processes on recent mysql versions
* Close tabs with CTRL+W
* Fixed query icon in new query tab
* Fixed process list in older mysql versions
* FIX: Do not hide the client hostname

New in version 0.4.1
''''''''''''''''''''
* Fixed process list from information_schema query on standard mysql

New in version 0.4
''''''''''''''''''
* Allow multiple connections to different servers at the same time
* New process list view
* List of indexes displayed in the table structure view
* Reorganized application layout
* Allow to specify the ssh port to connect to for the tunnel

New in version 0.3
''''''''''''''''''
* Refresh database/table list action
* Sortable columns in data view
* Display query execution time
* Implemented a ssh keepalive packet to avoid network timeouts
* Save/Restore main windows geometry
* Close tab with middle click
* Several bugs fixed

New in version 0.2
''''''''''''''''''
* Implemented query limit in the data tab (default: 1000)
* Local port auto selection of the SSH tunnel (when local port = 0)
* Better database error handling and reporting
* Secured random number generator in SSH tunnels

LICENSE
-------
Copyright (c) 2009-2012 Massimiliano Torromeo

SQLAntaresia is free software released under the terms of the MIT license.

See the LICENSE file provided with the source distribution for full details.

This application uses icons from the `Farm-Fresh Web Icons <http://www.fatcow.com/free-icons>`_ icon set by FatCow Web Hosting and from the `Oxygen <http://www.oxygen-icons.org/>`_ icon set by David Vignoni.

Contacts
--------
* Massimiliano Torromeo <massimiliano.torromeo@gmail.com>

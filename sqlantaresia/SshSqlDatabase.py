# -*- coding: utf-8 -*-
from PyQt4.QtGui import QMessageBox, QApplication

import MySQLdb
import _mysql_exceptions
from DBUtils.PersistentDB import PersistentDB

try:
    import paramiko
    from tunnel import TunnelThread
except ImportError:
    TunnelThread = None

class SshSqlDatabase():
    useTunnel = False
    tunnelThread = None
    dbpool = None
    _host = ""
    _port = 3306
    _user = ""
    _passwd = ""

    def connection(self):
        return self.dbpool.connection()

    def setDatabase(self, database):
        return self.connection().cursor().execute("USE `%s`" % database)

    def enableTunnel(self, username, password, port=0):
        self.useTunnel = True
        self.tunnelUsername = username
        self.tunnelPassword = password
        self.tunnelPort = port

    def disableTunnel(self):
        self.useTunnel = False

    def isOpen(self):
        return self.dbpool is not None

    def open(self, host, user, passwd, port=3306):
        self._host = host
        self._port = port
        self._user = user
        self._passwd = passwd
        if self.useTunnel and self.tunnelThread is None:
            self.openTunnel(host, port)
            host = "127.0.0.1"
            port = self.tunnelThread.local_port
        self.dbpool = PersistentDB(creator=MySQLdb, host=host, port=port, user=user, passwd=passwd, charset="utf8", use_unicode=True, setsession=['SET AUTOCOMMIT = 1'])

    def close(self):
        self.closeTunnel()

    def reconnect(self):
        self.close()
        self.open(self._host, self._user, self._passwd, self._port)

    def openTunnel(self, host, port):
        self.tunnelThread = TunnelThread(username=self.tunnelUsername, password=self.tunnelPassword, ssh_server=host, local_port=self.tunnelPort, remote_port=port)
        self.tunnelThread.start()

    def closeTunnel(self):
        if self.tunnelThread is not None:
            self.tunnelThread.join()
            del self.tunnelThread
            self.tunnelThread = None

    def escapeTableName(self, tableName):
        return "`%s`" % tableName

    def confirmQuery(self, sql):
        if QMessageBox.question(QApplication.activeWindow(), "Query confirmation request", "%s\nAre you sure?" % sql, QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            db = self.connection().cursor()
            try:
                db.execute(sql)
            except _mysql_exceptions.ProgrammingError as (errno, errmsg):
                QMessageBox.critical(QApplication.activeWindow(), "Query result", errmsg)

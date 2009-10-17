# -*- coding: utf-8 -*-
from PyQt4.QtGui import QMessageBox

import MySQLdb
import _mysql_exceptions
from DBUtils.PersistentDB import PersistentDB

try:
	import paramiko
	from tunnel import SSHForwarder
except ImportError:
	SSHForwarder = None

class SshSqlDatabase():
	useTunnel = False
	tunnelThread = None
	dbpool = None
	__host = ""
	__port = 3306
	__user = ""
	__passwd = ""
	
	def connection(self):
		return self.dbpool.connection()
	
	def setDatabase(self, database):
		return self.connection().cursor().execute("USE `%s`" % database)

	def enableTunnel(self, username, password, port=None):
		self.useTunnel = True
		self.tunnelUsername = username
		self.tunnelPassword = password
		self.tunnelPort = port

	def disableTunnel(self):
		self.useTunnel = False
	
	def isOpen(self):
		return self.dbpool is not None

	def open(self, host, user, passwd, port=3306):
		self.__host = host
		self.__port = port
		self.__user = user
		self.__passwd = passwd
		if self.useTunnel and self.tunnelThread is None:
			self.openTunnel(host, port)
			host = "127.0.0.1"
			port = self.tunnelPort
		self.dbpool = PersistentDB(creator=MySQLdb, host=host, port=port, user=user, passwd=passwd, charset="utf8", use_unicode=True)

	def close(self):
		self.closeTunnel()

	def reconnect(self):
		self.close()
		self.open(self.__host, self.__user, self.__passwd, self.__port)

	def openTunnel(self, host, port):
		self.tunnelThread = SSHForwarder(username=self.tunnelUsername, password=self.tunnelPassword, ssh_server=host, local_port=self.tunnelPort, remote_port=port)
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
			except _mysql_exception.ProgrammingError as (errno, errmsg):
				QMessageBox.critical(QApplication.activeWindow(), "Query result", errmsg)

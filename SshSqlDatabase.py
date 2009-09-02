# -*- coding: utf-8 -*-
from PyQt4.QtGui import QMessageBox
from PyQt4.QtSql import QSqlDatabase, QSqlDriver, QSqlQuery
from PyQt4.QtCore import QVariant

try:
	import paramiko
	from tunnel import SSHForwarder
except ImportError:
	SSHForwarder = None

class SshSqlDatabase(QSqlDatabase):
	useTunnel = False
	tunnelThread = None
	
	def __init__(self, db):
		QSqlDatabase.__init__(self, db)
	
	def enableTunnel(self, username, password, port=None):
		self.useTunnel = True
		self.tunnelUsername = username
		self.tunnelPassword = password
		self.tunnelPort = port
	
	def disableTunnel(self):
		self.useTunnel = False
		if self.tunnelHost is not None:
			self.setHostName(self.tunnelHost)
			self.tunnelHost = None
		if self.tunnelRemotePort is not None:
			self.setHostName(self.tunnelRemotePort)
			self.tunnelRemotePort = None
	
	def open(self):
		if self.useTunnel and self.tunnelThread is None:
			self.openTunnel()
		return QSqlDatabase.open(self)
	
	def close(self):
		result = QSqlDatabase.close(self)
		self.closeTunnel()
		return result
	
	def reconnect(self):
		self.close()
		self.open()
	
	def openTunnel(self):
		self.tunnelHost = str(self.hostName())
		self.setHostName("127.0.0.1")
		self.tunnelRemotePort = self.port()
		if self.tunnelPort is not None:
			self.setPort(int(self.tunnelPort))
		
		self.tunnelThread = SSHForwarder(username=self.tunnelUsername, password=self.tunnelPassword, ssh_server=self.tunnelHost, local_port=self.tunnelPort, remote_port=self.tunnelRemotePort)
		self.tunnelThread.start()
	
	def closeTunnel(self):
		if self.tunnelThread is not None:
			self.tunnelThread.join()
			del self.tunnelThread
			self.tunnelThread = None

	def escapeTableName(self, tableName):
		return self.driver().escapeIdentifier(tableName, QSqlDriver.TableName)

	def confirmQuery(self, sql, query=None):
		if QMessageBox.question(QApplication.activeWindow(), "Query confirmation request", "%s\nAre you sure?" % sql, QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
			if query is None:
				query = QSqlQuery( sql, self )
			if not query.exec_() and query.lastError().isValid():
				QMessageBox.critical(QApplication.activeWindow(), "Query result", query.lastError().databaseText())
	
	def verify(self):
		if not self.isOpen():
			return False
		q = QSqlQuery("SELECT 1", self)
		return q.exec_()
	
	def recordToDict(self, record):
		res = {}
		for i in range(record.count()):
			field = record.field(i)
			type = field.type()
			value = None
			if type == QVariant.Int or type == QVariant.UInt or type == QVariant.LongLong:
				value = field.value().toInt()[0]
			elif type == QVariant.String:
				value = str(field.value().toString())
			res[ str(field.name()) ] = value
		return res

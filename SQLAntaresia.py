# -*- coding: utf-8 -*-
# File : SQLAntaresia.py
# Depends: pyqt4, python-qscintilla, python-paramiko
import sys, re, ConfigParser, os, time
from PyQt4.QtCore import Qt, QObject, SIGNAL,  QString, pyqtSignature
from PyQt4.QtGui import QApplication, QMainWindow, QMessageBox,  QDialog, QToolButton, QMenu, QComboBox, QIcon, QLabel
from PyQt4.QtSql import *

try:
	import paramiko
	from tunnel import SSHForwarder
except ImportError:
	SSHForwarder = None

from Ui_SQLAntaresiaWindow import Ui_SQLAntaresiaWindow
from Connections import Connections
from TableDetails import TableDetails
from idesqldatabase import IdeSqlDatabase
from dbmodels import *

class SQLAntaresia(QMainWindow, Ui_SQLAntaresiaWindow):
	def __init__(self):
		QMainWindow.__init__(self)
		self.tunnelThread = None

		try:
			self.login = os.getlogin()
		except:
			self.login = ""

		# Configuration file
		self.configFilename = os.path.expanduser('~/.sqlantaresia.conf')
		self.config = ConfigParser.ConfigParser()
		self.config.read([self.configFilename])

		self.configuredConnections = {}
		for connectionName in self.config.sections():
			connection = {}
			connection["username"] = self.getConf(connectionName, "username", self.login)
			connection["password"] = self.getConf(connectionName, "password", "")
			connection["host"] = self.getConf(connectionName, "host", "localhost")
			connection["port"] = self.getConfInt(connectionName, "port", 3306)
			connection["database"] = self.getConf(connectionName, "database", "")
			connection["useTunnel"] = self.getConfBool(connectionName, "useTunnel", False)
			connection["tunnelPort"] = self.getConfInt(connectionName, "tunnelPort", 3306)
			connection["tunnelUsername"] = self.getConf(connectionName, "tunnelUsername", self.login)
			connection["tunnelPassword"] = self.getConf(connectionName, "tunnelPassword", "")
			self.configuredConnections[connectionName] = connection

		# Initialize Database
		self.db = IdeSqlDatabase(QSqlDatabase.addDatabase("QMYSQL"))
		self.db.setConnectOptions("CLIENT_COMPRESS=1")
		#TODO: Gestire errore di caricamento del driver

		# Setup UI
		self.setupUi(self)
		self.tabsWidget.clear()

		# Close TAB
		self.btnCloseTab = QToolButton()
		self.btnCloseTab.setDefaultAction( self.actionClose_Tab )
		self.btnCloseTab.setToolButtonStyle(Qt.ToolButtonIconOnly)
		self.tabsWidget.setCornerWidget( self.btnCloseTab )

		# TreeViewModel
		self.dbmsModel = DBMSTreeModel(self, self.db)
		self.treeView.setModel( self.dbmsModel )

		# ContextMenu
		self.menuTable = QMenu(self.treeView)
		self.menuTable.addAction( self.actionDrop_Database )
		self.menuTable.addAction( self.actionDrop_Table )

		# Connection string widget
		for connectionName in self.configuredConnections:
			self.cmbConnection.addItem(connectionName)
		if self.cmbConnection.count()==0:
			self.cmbConnection.setEditText("root@localhost")
		self.toolBarConnection.addWidget( QLabel("Connection string:") )
		self.toolBarConnection.addWidget( self.cmbConnection )

		QObject.connect(self.actionAbout_Qt, SIGNAL("triggered()"),  QApplication.aboutQt)

	def closeEvent(self, event):
		self.db.close()
		self.closeTunnel()

	def closeTunnel(self):
		if self.tunnelThread is not None:
			self.tunnelThread.join()
			del self.tunnelThread
			self.tunnelThread = None

	def getConf(self, section, name, defValue=None):
		try:
			return self.config.get(section, name)
		except ConfigParser.NoSectionError: return defValue
		except ConfigParser.NoOptionError: return defValue

	def getConfInt(self, section, name, defValue=None):
		return int(self.getConf(section, name, defValue))

	def getConfBool(self, section, name, defValue=False):
		try:
			return self.config.getboolean(section, name)
		except ConfigParser.NoSectionError: return defValue
		except ConfigParser.NoOptionError: return defValue

	def connectToUrl(self,  url):
		url = str(url)
		self.disconnect()

		tryConnect = False
		if url in self.configuredConnections:
			connection = self.configuredConnections[url]

			if connection["useTunnel"] and SSHForwarder is not None:
				try:
					self.tunnelThread = SSHForwarder(username=connection["tunnelUsername"], password=connection["tunnelPassword"], ssh_server=connection["host"], local_port=connection["tunnelPort"], remote_port=connection["port"])
					self.tunnelThread.start()

					host = "127.0.0.1"
					port = connection["tunnelPort"]
				except (paramiko.BadHostKeyException, paramiko.AuthenticationException) as e:
					msgBoxError = QMessageBox()
					msgBoxError.setText(str(e))
					msgBoxError.exec_()
					return
			else:
				host = connection["host"]
				port = connection["port"]
			username = connection["username"]
			password = connection["password"]
			tryConnect = True
		else:
			regexp = re.compile("([A-Za-z0-9\.]+)(?::([A-Za-z0-9\.]+))?@([A-Za-z0-9\.]+)(?::([0-9]{2,5}))?(?:/([A-Za-z0-9\.]+))?")
			matches = regexp.match(url)
			if matches:
				m = matches.groups()
				username = m[0]
				password = m[1]
				host = m[2]
				port = m[3]
				if port != None:
					port = int(port)
				database = m[4]
				tryConnect = True

		if tryConnect:
			self.statusBar.showMessage("Connecting to %s..." % host)
			if self.initDB(username, host, port, password):
				self.statusBar.showMessage("Connected.", 10000)
				#TODO: Se indirizzo valido, salvarlo nella history
			else:
				self.statusBar.showMessage(self.db.lastError().text(), 10000)

	def initDB(self, username, host="localhost", port=None, password=None):
		self.db.setHostName(host)
		self.db.setUserName(username)
		if password != None and password != "":
			self.db.setPassword(password)
		if port != None and port > 0 and port < 65536:
			self.db.setPort(port)
		result = self.db.open()
		self.refreshTreeView(True)
		return result

	def refreshTreeView(self, reset=False):
		if reset:
			self.dbmsModel.setDB( self.db )
		else:
			self.dbmsModel.refresh()

	def disconnect(self):
		if self.db.isOpen():
			self.tabsWidget.clear()
			self.db.close()
			self.closeTunnel()
			self.statusBar.showMessage("Disconnected.", 10000)
			self.refreshTreeView(True)

	@pyqtSignature("QString")
	def on_cmbConnection_currentIndexChanged(self, text):
		self.connectToUrl(text)

	@pyqtSignature("")
	def on_actionDisconnect_triggered(self):
		self.disconnect()
		self.cmbConnection.setEditText("")

	@pyqtSignature("")
	def on_actionAbout_SQLAntaresia_triggered(self):
		QMessageBox.about(self, "About SQL Antaresia", u"SQL Antaresia is a MySQL administrative tool aimed at developers and sysadmins.\n\n© 2009 Massimiliano Torromeo")

	@pyqtSignature("")
	def on_actionClose_Tab_triggered(self):
		self.tabsWidget.removeTab( self.tabsWidget.currentIndex() )

	@pyqtSignature("")
	def on_actionConfigure_Connections_triggered(self):
		dialog = Connections(self, self.configuredConnections)
		dialog.exec_()
		for section in self.config.sections():
			if section not in self.configuredConnections:
				self.config.remove_section(section)
		for connection in self.configuredConnections:
			if connection not in self.config.sections():
				self.config.add_section(connection)
			self.config.set(connection, "host", self.configuredConnections[connection]["host"])
			self.config.set(connection, "port", self.configuredConnections[connection]["port"])
			self.config.set(connection, "username", self.configuredConnections[connection]["username"])
			self.config.set(connection, "password", self.configuredConnections[connection]["password"])
			self.config.set(connection, "database", self.configuredConnections[connection]["database"])
			self.config.set(connection, "useTunnel", self.configuredConnections[connection]["useTunnel"])
			self.config.set(connection, "tunnelPort", self.configuredConnections[connection]["tunnelPort"])
			self.config.set(connection, "tunnelUsername", self.configuredConnections[connection]["tunnelUsername"])
			self.config.set(connection, "tunnelPassword", self.configuredConnections[connection]["tunnelPassword"])
			with open(self.configFilename, "wb") as configfile:
				self.config.write(configfile)

	def on_treeView_activated(self, modelIndex):
		if type(modelIndex.internalPointer()) is TableTreeItem:
			dbName = modelIndex.parent().internalPointer().getName()
			tableName = modelIndex.internalPointer().getName()

			index = self.tabsWidget.addTab( TableDetails(self.db, dbName, tableName), QIcon(":/16/table.png"), "%s.%s" % (dbName, tableName) )
			self.tabsWidget.setCurrentIndex(index)

	def on_treeView_customContextMenuRequested(self, point):
		modelIndex = self.treeView.currentIndex()

		self.actionDrop_Database.setEnabled( type(modelIndex.internalPointer()) is DatabaseTreeItem )
		self.actionDrop_Table.setEnabled( type(modelIndex.internalPointer()) is TableTreeItem )

		self.menuTable.popup( self.treeView.mapToGlobal(point) )

	@pyqtSignature("")
	def on_actionDrop_Database_triggered(self):
		queries = []
		for idx in self.treeView.selectedIndexes():
			if idx.parent().internalPointer() is None:
				dbName = idx.internalPointer().getName()
				queries.append( "DROP DATABASE %s;" % self.db.escapeTableName(dbName) )
		if QMessageBox.question(self, "Confirmation request", "\n".join(queries)+"\n\nDo want to proceed?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
			query = QSqlQuery( "\n".join(queries), self.db )
			if not query.exec_() and query.lastError().isValid():
				QMessageBox.critical(self, "Query result", query.lastError().databaseText())
			self.refreshTreeView()

	@pyqtSignature("")
	def on_actionDrop_Table_triggered(self):
		queries = []
		for idx in self.treeView.selectedIndexes():
			if idx.parent().internalPointer() is not None:
				dbName = idx.parent().internalPointer().getName()
				tableName = idx.internalPointer().getName()
				queries.append( "DROP TABLE %s.%s;" % (self.db.escapeTableName(dbName), self.db.escapeTableName(tableName)) )
		if QMessageBox.question(self, "Confirmation request", "\n".join(queries)+"\n\nDo want to proceed?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
			query = QSqlQuery( "\n".join(queries), self.db )
			if not query.exec_() and query.lastError().isValid():
				QMessageBox.critical(self, "Query result", query.lastError().databaseText())
			self.refreshTreeView()


if __name__ == "__main__":
	app = QApplication(sys.argv)
	window = SQLAntaresia()
	window.show()
	sys.exit(app.exec_())

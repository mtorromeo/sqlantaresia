# -*- coding: utf-8 -*-
# File : SQLAntaresia.py
# Depends: pyqt4, python-qscintilla, python-paramiko
import sys, re, ConfigParser, os, time
from PyQt4.QtCore import Qt, QObject, SIGNAL, pyqtSignature, QString, QModelIndex
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
from QueryTab import QueryTab
from SshSqlDatabase import SshSqlDatabase
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
		if not QSqlDatabase.isDriverAvailable("QMYSQL"):
			QMessageBox.critical(self, "SQL Driver not found", "The QMYSQL database driver could not be loaded. Consult the system administrator.")
			exit(1)

		self.db = SshSqlDatabase(QSqlDatabase.addDatabase("QMYSQL"))
		self.db.setConnectOptions("CLIENT_COMPRESS=1")

		# Setup UI
		self.setupUi(self)
		self.tabsWidget.clear()

		# StatusBar Widgets
		self.lblConnectedHost = QLabel("Host:")
		self.lblConnectionStatus = QLabel("Status:")
		self.statusBar.addPermanentWidget(self.lblConnectedHost)
		self.statusBar.addPermanentWidget(self.lblConnectionStatus)

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

		# Connection string widget
		for connectionName in self.configuredConnections:
			self.cmbConnection.addItem(connectionName)
		if self.cmbConnection.count()==0:
			self.cmbConnection.setEditText("root@localhost")
		self.toolBarConnection.insertWidget( self.actionGo, QLabel("Connection string:") )
		self.toolBarConnection.insertWidget( self.actionGo, self.cmbConnection )

		QObject.connect(self.actionAbout_Qt, SIGNAL("triggered()"),  QApplication.aboutQt)

	def closeEvent(self, event):
		self.db.close()

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

		if url in self.configuredConnections:
			connection = self.configuredConnections[url]

			if self.initDB(connection["username"], connection["host"], connection["port"], connection["password"], connection["useTunnel"], connection["tunnelPort"], connection["tunnelUsername"], connection["tunnelPassword"]):
				self.statusBar.showMessage("Connected.", 10000)
			else:
				self.statusBar.showMessage(self.db.lastError().text(), 10000)
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

				if self.initDB(username, host, port, password):
					self.statusBar.showMessage("Connected.", 10000)
					#TODO: Se indirizzo valido, salvarlo nella history
				else:
					self.statusBar.showMessage(self.db.lastError().text(), 10000)

	def initDB(self, username, host="localhost", port=None, password=None, useTunnel=False, tunnelPort=None, tunnelUsername=None, tunnelPassword=None):
		self.statusBar.showMessage("Connecting to %s..." % host)
		self.lblConnectedHost.setText("Host:")
		self.lblConnectionStatus.setText("Status: Connecting...")

		self.db.setHostName(host)
		self.db.setUserName(username)
		if password != None and password != "":
			self.db.setPassword(password)
		if port != None and port > 0 and port < 65536:
			self.db.setPort(port)

		if useTunnel and SSHForwarder is not None:
			self.db.enableTunnel(tunnelUsername, tunnelPassword, tunnelPort)

		try:
			result = self.db.open()
		except (paramiko.BadHostKeyException, paramiko.AuthenticationException) as e:
			self.statusBar.showMessage(str(e), 10000)

		if result:
			self.lblConnectedHost.setText("Host: %s@%s" % (username, host))
			self.lblConnectionStatus.setText("Status: Connected.")
		else:
			self.lblConnectionStatus.setText("Status: Disconnected.")

		self.refreshTreeView(True)
		return result

	def refreshTreeView(self, reset=False):
		if reset:
			self.dbmsModel.setDB( self.db )
			# Auto expand root items
			i = 0
			invalid = QModelIndex()
			while self.dbmsModel.index(i,0,invalid).isValid():
				self.treeView.expand( self.dbmsModel.index(i,0,invalid) )
				i += 1
		else:
			self.dbmsModel.refresh()

	def disconnect(self):
		if self.db.isOpen():
			self.tabsWidget.clear()
			self.db.close()
			self.statusBar.showMessage("Disconnected.", 10000)
			self.refreshTreeView(True)

	@pyqtSignature("QString")
	def on_cmbConnection_activated(self, text):
		self.on_actionGo_triggered()

	@pyqtSignature("")
	def on_actionGo_triggered(self):
		self.connectToUrl( self.cmbConnection.lineEdit().text() )

	@pyqtSignature("")
	def on_actionReconnect_triggered(self):
		self.db.reconnect()

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

	@pyqtSignature("")
	def on_actionNew_Query_Tab_triggered(self):
		if len(self.treeView.selectedIndexes()) > 0:
			idx = self.treeView.selectedIndexes()[0]
			if type(idx.internalPointer()) is DatabaseTreeItem:
				dbName = idx.internalPointer().getName()
				index = self.tabsWidget.addTab( QueryTab(self.db, dbName), QIcon(":/16/db.png"), "Query on %s" % (dbName) )
				self.tabsWidget.setCurrentIndex(index)

	def on_treeView_activated(self, modelIndex):
		if type(modelIndex.internalPointer()) is TableTreeItem:
			dbName = modelIndex.parent().internalPointer().getName()
			tableName = modelIndex.internalPointer().getName()

			index = self.tabsWidget.addTab( TableDetails(self.db, dbName, tableName), QIcon(":/16/table.png"), "%s.%s" % (dbName, tableName) )
			self.tabsWidget.setCurrentIndex(index)

	def on_treeView_customContextMenuRequested(self, point):
		modelIndex = self.treeView.currentIndex()

		self.menuTable.clear()

		if type(modelIndex.internalPointer()) is DatabaseTreeItem:
			self.menuTable.addAction( self.actionNew_Query_Tab )
			self.menuTable.addAction( self.actionDrop_Database )

		if type(modelIndex.internalPointer()) is TableTreeItem:
			self.menuTable.addAction( self.actionOptimize_Table )
			self.menuTable.addAction( self.actionRepair_Table )
			self.menuTable.addAction( self.actionTruncate_Table )
			self.menuTable.addAction( self.actionDrop_Table )

		self.menuTable.popup( self.treeView.mapToGlobal(point) )

	def queryOnSelectedTables(self, queryTpl):
		queries = []
		for idx in self.treeView.selectedIndexes():
			if idx.parent().internalPointer() is not None:
				dbName = idx.parent().internalPointer().getName()
				tableName = idx.internalPointer().getName()
				queries.append( queryTpl % (self.db.escapeTableName(dbName), self.db.escapeTableName(tableName)) )
		if QMessageBox.question(self, "Confirmation request", "\n".join(queries)+"\n\nDo you want to proceed?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
			query = QSqlQuery( "\n".join(queries), self.db )
			if not query.exec_() and query.lastError().isValid():
				QMessageBox.critical(self, "Query result", query.lastError().databaseText())
			else:
				return True
		return False

	@pyqtSignature("")
	def on_actionDrop_Database_triggered(self):
		queries = []
		for idx in self.treeView.selectedIndexes():
			if type(idx.internalPointer()) is DatabaseTreeItem:
				dbName = idx.internalPointer().getName()
				queries.append( "DROP DATABASE %s;" % self.db.escapeTableName(dbName) )
		if QMessageBox.question(self, "Confirmation request", "\n".join(queries)+"\n\nDo you want to proceed?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
			query = QSqlQuery( "\n".join(queries), self.db )
			if not query.exec_() and query.lastError().isValid():
				QMessageBox.critical(self, "Query result", query.lastError().databaseText())
			self.refreshTreeView()

	@pyqtSignature("")
	def on_actionDrop_Table_triggered(self):
		if self.queryOnSelectedTables("DROP TABLE %s.%s;"):
			self.refreshTreeView()

	@pyqtSignature("")
	def on_actionTruncate_Table_triggered(self):
		self.queryOnSelectedTables("TRUNCATE TABLE %s.%s;")

	@pyqtSignature("")
	def on_actionOptimize_Table_triggered(self):
		self.queryOnSelectedTables("OPTIMIZE TABLE %s.%s;")

	@pyqtSignature("")
	def on_actionRepair_Table_triggered(self):
		self.queryOnSelectedTables("REPAIR TABLE %s.%s;")


if __name__ == "__main__":
	app = QApplication(sys.argv)
	window = SQLAntaresia()
	window.show()
	sys.exit(app.exec_())

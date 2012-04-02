# -*- coding: utf-8 -*-
# File : SQLAntaresia.py
# Depends: pyqt4, python-qscintilla, python-paramiko

import re
import ConfigParser
import os
import socket
import _mysql_exceptions
import paramiko

from PyQt4.QtCore import QObject, SIGNAL, pyqtSignature, QModelIndex, QByteArray, Qt
from PyQt4.QtGui import QApplication, QMainWindow, QMessageBox, QMenu, QIcon, QLabel, QDialog, QToolBar, QShortcut, QKeySequence
from QMiddleClickCloseTabBar import QMiddleClickCloseTabBar

from ConfigureConnection import ConfigureConnection
from Ui_SQLAntaresiaWindow import Ui_SQLAntaresiaWindow
from SettingsDialog import SettingsDialog
from TableDetails import TableDetails
from QueryTab import QueryTab
from ProcessListTab import ProcessListTab
from connections import SQLServerConnection

from dbmodels import DBMSTreeModel, DatabaseTreeItem, TableTreeItem, ConnectionTreeItem

class SQLAntaresia(QMainWindow, Ui_SQLAntaresiaWindow):
    def __init__(self):
        QMainWindow.__init__(self)

        # Configuration file
        if os.name == "nt":
            appdir = os.path.expanduser('~/Application Data/SQLAntaresia')
            if not os.path.isdir(appdir):
                os.mkdir(appdir)
            self.configFilename = appdir + "/sqlantaresia.conf"
        else:
            self.configFilename = os.path.expanduser('~/.sqlantaresia.conf')

        self.config = ConfigParser.ConfigParser()
        self.config.read([self.configFilename])

        self.connections = {}
        for connectionName in self.config.sections():
            if connectionName[0] != "@":
                self.connections[connectionName] = SQLServerConnection(
                    username = self.getConf(connectionName, "username", None),
                    password = self.getConf(connectionName, "password", ""),
                    host = self.getConf(connectionName, "host", "localhost"),
                    port = self.getConfInt(connectionName, "port", 3306),
                    database = self.getConf(connectionName, "database", ""),
                    use_tunnel = self.getConfBool(connectionName, "use_tunnel", False),
                    tunnel_username = self.getConf(connectionName, "tunnel_username", None),
                    tunnel_password = self.getConf(connectionName, "tunnel_password", ""),
                    tunnel_port = self.getConfInt(connectionName, "tunnel_port", 22),
                )

        # Setup UI
        self.setupUi(self)
        self.tabsWidget.clear()
        self.tabsWidget.setTabBar( QMiddleClickCloseTabBar() )
        self.tabsWidget.setTabsClosable(True)
        self.tabsWidget.setMovable(True)

        # Close tab shortcut
        closeTabShortcut = QShortcut(QKeySequence("CTRL+W"), self)
        closeTabShortcut.activated.connect(self.on_closeTabShortcut_activated)

        # Setup left dock with a new window with toolbar
        dockWindow = QMainWindow(self.dockWidget)
        dockWindow.setWindowFlags(Qt.Widget)
        self.dockToolbar = QToolBar(dockWindow)
        dockWindow.addToolBar(self.dockToolbar)
        dockWindow.setCentralWidget(self.treeView)
        self.dockWidget.setWidget(dockWindow)

        # Dock toolbar
        self.dockToolbar.addAction(self.actionAddConnection)
        self.dockToolbar.addAction(self.actionRemoveConnection)
        self.dockToolbar.addAction(self.actionConfigureConnection)
        self.dockToolbar.addAction(self.actionRefresh)
        self.dockToolbar.addSeparator()
        self.dockToolbar.addAction(self.actionDisconnect)
        self.dockToolbar.addAction(self.actionReconnect)

        # StatusBar Widgets
        self.lblConnectedHost = QLabel("Host:")
        self.lblConnectionStatus = QLabel("Status:")
        self.statusBar.addPermanentWidget(self.lblConnectedHost)
        self.statusBar.addPermanentWidget(self.lblConnectionStatus)

        # TreeViewModel
        self.dbmsModel = DBMSTreeModel(self, self.connections)
        self.treeView.setModel( self.dbmsModel )

        # ContextMenu
        self.menuTable = QMenu(self.treeView)

        # Saved settings
        QueryTab.font.fromString( self.getConf("@QueryEditor", "font", 'Monospace,12,-1,5,50,0,0,0,0,0') )
        if self.config.has_section("@MainWindow"):
            self.restoreGeometry( QByteArray.fromBase64( self.config.get("@MainWindow", "geometry") ) )

        QObject.connect(self.actionAboutQt, SIGNAL("triggered()"),  QApplication.aboutQt)

    def closeEvent(self, event):
        for connectionName in self.connections:
            self.connections[connectionName].close()

        if "@MainWindow" not in self.config.sections():
            self.config.add_section("@MainWindow")
        self.config.set("@MainWindow", "geometry", self.saveGeometry().toBase64())

        with open(self.configFilename, "wb") as configfile:
            self.config.write(configfile)

    def on_closeTabShortcut_activated(self):
        idx = self.tabsWidget.currentIndex()
        if idx >= 0:
            self.tabsWidget.removeTab(idx)

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

    @pyqtSignature("")
    def on_actionRefresh_triggered(self):
        self.dbmsModel.refresh()

    @pyqtSignature("")
    def on_actionReconnect_triggered(self):
        for idx in self.treeView.selectedIndexes():
            item = idx.internalPointer()
            connection = item.getConnection()
            if connection.isOpen():
                connection.reconnect()

    @pyqtSignature("")
    def on_actionDisconnect_triggered(self):
        for idx in self.treeView.selectedIndexes():
            item = idx.internalPointer()
            item.getConnection().close()

    @pyqtSignature("")
    def on_actionAboutSQLAntaresia_triggered(self):
        QMessageBox.about(self, "About SQL Antaresia", u"SQL Antaresia is a MySQL administrative tool aimed at developers and sysadmins.\n\n© 2009-2012 Massimiliano Torromeo")

    def on_tabsWidget_tabCloseRequested(self, index):
        self.tabsWidget.removeTab( index )

    def saveConfig(self):
        for section in self.config.sections():
            if section[0] != "@" and section not in self.connections:
                self.config.remove_section(section)

        for name in self.connections:
            if name not in self.config.sections():
                self.config.add_section(name)
            connection = self.connections[name]
            self.config.set(name, "host", connection.host)
            self.config.set(name, "port", connection.port)
            self.config.set(name, "username", connection.username)
            self.config.set(name, "password", connection.password)
            self.config.set(name, "database", connection.database)
            self.config.set(name, "use_tunnel", connection.use_tunnel)
            self.config.set(name, "tunnel_username", connection.tunnel_username)
            self.config.set(name, "tunnel_password", connection.tunnel_password)
            self.config.set(name, "tunnel_port", connection.tunnel_port)

        with open(self.configFilename, "wb") as configfile:
            self.config.write(configfile)

    @pyqtSignature("")
    def on_actionConfigureSQLAntaresia_triggered(self):
        d = SettingsDialog()
        d.setEditorFont(QueryTab.font)
        if d.exec_():
            QueryTab.font = d.lblSelectedFont.font()
            if "@QueryEditor" not in self.config.sections():
                self.config.add_section("@QueryEditor")
            self.config.set("@QueryEditor", "font", QueryTab.font.toString())
            with open(self.configFilename, "wb") as configfile:
                self.config.write(configfile)

    @pyqtSignature("")
    def on_actionNewQueryTab_triggered(self):
        if self.treeView.selectedIndexes():
            idx = self.treeView.selectedIndexes()[0]
            item = idx.internalPointer()

            if type(item) is DatabaseTreeItem:
                dbName = item.getName()

                index = self.tabsWidget.addTab( QueryTab(item.getConnection(), dbName), QIcon(":/16/icons/database_edit.png"), "Query on %s" % (dbName) )
                self.tabsWidget.setCurrentIndex(index)

    @pyqtSignature("")
    def on_actionShowProcessList_triggered(self):
        if self.treeView.selectedIndexes():
            idx = self.treeView.selectedIndexes()[0]
            connection = idx.internalPointer().getConnection()

            index = self.tabsWidget.addTab( ProcessListTab(connection), QIcon(":/16/icons/database_server.png"), "Process list of %s" % (connection.host) )
            self.tabsWidget.setCurrentIndex(index)

    def on_treeView_activated(self, modelIndex):
        item = modelIndex.internalPointer()
        _type = type(item)

        if _type is TableTreeItem:
            parent = modelIndex.parent().internalPointer()
            dbName = parent.getName()
            tableName = item.getName()

            index = self.tabsWidget.addTab( TableDetails(item.getConnection(), dbName, tableName), QIcon(":/16/icons/database_table.png"), "%s.%s" % (dbName, tableName) )
            self.tabsWidget.setCurrentIndex(index)

        elif _type is ConnectionTreeItem:
            try:
                item.open()
            except _mysql_exceptions.OperationalError as (errnum, errmsg):
                QMessageBox.critical(self, "MySQL error (%d)" % errnum, errmsg)
            except paramiko.SSHException as e:
                QMessageBox.critical(self, "SSH error", str(e))
            except socket.error as e:
                QMessageBox.critical(self, "Network error", str(e))

    def on_treeView_customContextMenuRequested(self, point):
        item = self.treeView.currentIndex().internalPointer()
        _type = type(item)

        self.menuTable.clear()

        if _type is DatabaseTreeItem:
            self.menuTable.addAction( self.actionNewQueryTab )
            self.menuTable.addAction( self.actionDropDatabase )

        elif _type is TableTreeItem:
            self.menuTable.addAction( self.actionShowCreate )
            self.menuTable.addAction( self.actionOptimizeTable )
            self.menuTable.addAction( self.actionRepairTable )
            self.menuTable.addAction( self.actionTruncateTable )
            self.menuTable.addAction( self.actionDropTable )

        elif _type is ConnectionTreeItem:
            self.menuTable.addAction( self.actionConfigureConnection )
            self.menuTable.addAction( self.actionRemoveConnection )
            if item.getConnection().isOpen():
                self.menuTable.addSeparator()
                self.menuTable.addAction(self.actionDisconnect)
                self.menuTable.addAction(self.actionReconnect)
                self.menuTable.addAction( self.actionShowProcessList )

        self.menuTable.popup( self.treeView.mapToGlobal(point) )

    def queryOnSelectedTables(self, queryTpl, listTables=False):
        queries = []
        for idx in self.treeView.selectedIndexes():
            if idx.parent().internalPointer() is not None:
                dbName = idx.parent().internalPointer().getName()
                tableName = idx.internalPointer().getName()
                if listTables:
                    queries.append( "%s.%s" % (self.db.escapeTableName(dbName), self.db.escapeTableName(tableName)) )
                else:
                    queries.append( queryTpl % (self.db.escapeTableName(dbName), self.db.escapeTableName(tableName)) )
        if listTables:
            query = queryTpl % (", ".join(queries))
        else:
            query = "\n".join(queries)
        queryDesc = query if len(query)<500 else query[0:250] + "\n[...]\n" + query[-250:]
        if QMessageBox.question(self, "Confirmation request", queryDesc+"\n\nDo you want to proceed?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            try:
                self.db.connection().cursor().execute(query)
            except _mysql_exceptions.ProgrammingError as (errno, errmsg): #@UnusedVariable
                QMessageBox.critical(self, "Query result", errmsg)
            else:
                return True
        return False

    @pyqtSignature("")
    def on_actionShowCreate_triggered(self):
        if self.treeView.selectedIndexes():
            idx = self.treeView.selectedIndexes()[0]
            item = idx.internalPointer()

            if type(item) is TableTreeItem:
                dbName = idx.parent().internalPointer().getName()
                tableName = item.getName()

                try:
                    cursor = item.getConnection().cursor()
                    cursor.execute("SHOW CREATE TABLE `%s`.`%s`;" % (dbName, tableName))
                    row = cursor.fetchone()
                    create = row[1]
                except _mysql_exceptions.ProgrammingError as (errno, errmsg): #@UnusedVariable
                    QMessageBox.critical(self, "Query result", errmsg)

                index = self.tabsWidget.addTab( QueryTab(item.getConnection(), dbName, query=create), QIcon(":/16/icons/database.png"), "Query on %s" % (dbName) )
                self.tabsWidget.setCurrentIndex(index)

    @pyqtSignature("")
    def on_actionDropDatabase_triggered(self):
        queries = []
        for idx in self.treeView.selectedIndexes():
            if type(idx.internalPointer()) is DatabaseTreeItem:
                dbName = idx.internalPointer().getName()
                queries.append( "DROP DATABASE %s;" % self.db.escapeTableName(dbName) )
        if QMessageBox.question(self, "Confirmation request", "\n".join(queries)+"\n\nDo you want to proceed?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            try:
                self.db.connection().cursor().execute("\n".join(queries))
            except _mysql_exceptions.ProgrammingError as (errno, errmsg): #@UnusedVariable
                QMessageBox.critical(self, "Query result", errmsg)
            self.refreshTreeView()

    @pyqtSignature("")
    def on_actionDropTable_triggered(self):
        if self.queryOnSelectedTables("DROP TABLE %s.%s;"):
            self.refreshTreeView()

    @pyqtSignature("")
    def on_actionTruncateTable_triggered(self):
        self.queryOnSelectedTables("TRUNCATE TABLE %s.%s;")

    @pyqtSignature("")
    def on_actionOptimizeTable_triggered(self):
        self.queryOnSelectedTables("OPTIMIZE TABLE %s;", listTables=True)

    @pyqtSignature("")
    def on_actionRepairTable_triggered(self):
        self.queryOnSelectedTables("REPAIR TABLE %s.%s;")

    @pyqtSignature("")
    def on_actionConfigureConnection_triggered(self):
        if self.treeView.selectedIndexes():
            idx = self.treeView.selectedIndexes()[0]
            item = idx.internalPointer()

            if type(item) is ConnectionTreeItem:
                name = item.getName()
                connection = item.getConnection()
                options = {
                    "host": connection.host,
                    "port": connection.port,
                    "database": connection.database,
                    "username": connection.username,
                    "password": connection.password,
                    "use_tunnel": connection.use_tunnel,
                    "tunnel_port": connection.tunnel_port,
                    "tunnel_username": connection.tunnel_username,
                    "tunnel_password": connection.tunnel_password,
                }

                configDialog = ConfigureConnection(self, name, options)
                if configDialog.exec_() == QDialog.Accepted:
                    connection.host = options["host"]
                    connection.port = options["port"]
                    connection.database = options["database"]
                    connection.username = options["username"]
                    connection.password = options["password"]
                    connection.use_tunnel = options["use_tunnel"]
                    connection.tunnel_port = options["tunnel_port"]
                    connection.tunnel_username = options["tunnel_username"]
                    connection.tunnel_password = options["tunnel_password"]

                    self.connections[configDialog.connection] = connection

                    if name != configDialog.connection:
                        self.dbmsModel.setData(idx, configDialog.connection,  Qt.DisplayRole)
                        del self.connections[name]

                    self.saveConfig()

    @pyqtSignature("")
    def on_actionAddConnection_triggered(self):
        options = {
            "host": "localhost",
            "port": 3306,
            "database": None,
            "username": "root",
            "password": "",
            "use_tunnel": False,
            "tunnel_port": 22,
            "tunnel_username": None,
            "tunnel_password": None
        }

        configDialog = ConfigureConnection(self, "", options)
        if configDialog.exec_() == QDialog.Accepted:
            name = configDialog.connection
            if name not in self.connections:
                self.connections[name] = SQLServerConnection( **options )
                self.dbmsModel.refresh()
                self.saveConfig()

    @pyqtSignature("")
    def on_actionRemoveConnection_triggered(self):
        if not self.treeView.selectedIndexes():
            return

        idx = self.treeView.selectedIndexes()[0]
        item = idx.internalPointer()

        if type(item) is not ConnectionTreeItem:
            return

        name = item.getName()
        connection = item.getConnection()

        if connection.isOpen():
            connection.close()

        del self.connections[name]
        self.dbmsModel.refresh()
        self.saveConfig()
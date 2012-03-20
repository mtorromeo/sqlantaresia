# -*- coding: utf-8 -*-
# File : SQLAntaresia.py
# Depends: pyqt4, python-qscintilla, python-paramiko

import re, ConfigParser, os, socket, _mysql_exceptions
from PyQt4.QtCore import QObject, SIGNAL, pyqtSignature, QModelIndex, QByteArray
from PyQt4.QtGui import QApplication, QMainWindow, QMessageBox, QMenu, QIcon, QLabel
from QMiddleClickCloseTabBar import QMiddleClickCloseTabBar

try:
    import paramiko
    from tunnel import TunnelThread
except DeprecationWarning:
    pass
except ImportError:
    TunnelThread = None
except Exception as e:
    print e

from Ui_SQLAntaresiaWindow import Ui_SQLAntaresiaWindow
from SettingsDialog import SettingsDialog
from Connections import Connections
from TableDetails import TableDetails
from QueryTab import QueryTab
from SshSqlDatabase import SshSqlDatabase
from dbmodels import DBMSTreeModel, DatabaseTreeItem, TableTreeItem

class SQLAntaresia(QMainWindow, Ui_SQLAntaresiaWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.tunnelThread = None

        try:
            self.login = os.getlogin()
        except:
            self.login = ""

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

        self.configuredConnections = {}
        for connectionName in self.config.sections():
            if connectionName[0] != "@":
                connection = {}
                connection["username"] = self.getConf(connectionName, "username", self.login)
                connection["password"] = self.getConf(connectionName, "password", "")
                connection["host"] = self.getConf(connectionName, "host", "localhost")
                connection["port"] = self.getConfInt(connectionName, "port", 3306)
                connection["database"] = self.getConf(connectionName, "database", "")
                connection["useTunnel"] = self.getConfBool(connectionName, "useTunnel", False)
                connection["tunnelPort"] = self.getConfInt(connectionName, "tunnelPort", 0)
                connection["tunnelUsername"] = self.getConf(connectionName, "tunnelUsername", self.login)
                connection["tunnelPassword"] = self.getConf(connectionName, "tunnelPassword", "")
                self.configuredConnections[connectionName] = connection

        self.db = SshSqlDatabase()

        # Setup UI
        self.setupUi(self)
        self.tabsWidget.clear()
        self.tabsWidget.setTabBar( QMiddleClickCloseTabBar() )
        self.tabsWidget.setTabsClosable(True)
        self.tabsWidget.setMovable(True)

        # StatusBar Widgets
        self.lblConnectedHost = QLabel("Host:")
        self.lblConnectionStatus = QLabel("Status:")
        self.statusBar.addPermanentWidget(self.lblConnectedHost)
        self.statusBar.addPermanentWidget(self.lblConnectionStatus)

        # TreeViewModel
        self.dbmsModel = DBMSTreeModel(self, self.db)
        self.treeView.setModel( self.dbmsModel )

        # ContextMenu
        self.menuTable = QMenu(self.treeView)

        # Saved settings
        QueryTab.font.fromString( self.getConf("@QueryEditor", "font", 'Monospace,12,-1,5,50,0,0,0,0,0') )
        if self.config.has_section("@MainWindow"):
            self.restoreGeometry( QByteArray.fromBase64( self.config.get("@MainWindow", "geometry") ) )

        # Connection string widget
        for connectionName in self.configuredConnections:
            self.cmbConnection.addItem(connectionName)
        if self.cmbConnection.count()==0:
            self.cmbConnection.setEditText("root@localhost")
        self.toolBarConnection.insertWidget( self.actionGo, QLabel("Connection string:") )
        self.toolBarConnection.insertWidget( self.actionGo, self.cmbConnection )

        self.setTabOrder(self.cmbConnection, self.treeView)
        self.setTabOrder(self.treeView, self.tabsWidget)
        self.cmbConnection.lineEdit().selectAll()

        QObject.connect(self.actionAboutQt, SIGNAL("triggered()"),  QApplication.aboutQt)

    def closeEvent(self, event):
        self.db.close()
        if "@MainWindow" not in self.config.sections():
            self.config.add_section("@MainWindow")
        self.config.set("@MainWindow", "geometry", self.saveGeometry().toBase64())
        with open(self.configFilename, "wb") as configfile:
            self.config.write(configfile)

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

    def connectToUrl(self, url):
        self.disconnect()

        if url in self.configuredConnections:
            connection = self.configuredConnections[url]

            if self.initDB(connection["username"], connection["host"], connection["port"], connection["password"], connection["useTunnel"], connection["tunnelPort"], connection["tunnelUsername"], connection["tunnelPassword"]):
                self.statusBar.showMessage("Connected.", 10000)
        else:
            regexp = re.compile("([A-Za-z0-9\.]+)(?::([A-Za-z0-9\.]+))?@([A-Za-z0-9\.]+)(?::([0-9]{2,5}))?(?:/([A-Za-z0-9\.]+))?")
            matches = regexp.match(url)
            if matches:
                m = matches.groups()
                username = m[0]
                password = "" if m[1] is None else m[1]
                host = m[2]
                port = 3306 if m[3] is None else int(m[3])
                #database = m[4]

                if self.initDB(username, host, port, password):
                    self.statusBar.showMessage("Connected.", 10000)
                    #TODO: Se indirizzo valido, salvarlo nella history

    def initDB(self, username, host="localhost", port=None, password=None, useTunnel=False, tunnelPort=0, tunnelUsername=None, tunnelPassword=None):
        self.statusBar.showMessage("Connecting to %s..." % host)
        self.lblConnectedHost.setText("Host:")
        self.lblConnectionStatus.setText("Status: Connecting...")

        if useTunnel and TunnelThread is not None:
            self.db.enableTunnel(tunnelUsername, tunnelPassword, tunnelPort)

        result = False
        try:
            self.db.open(host=host, user=username, passwd=password, port=port)
            result = True
        except (paramiko.BadHostKeyException, paramiko.AuthenticationException, socket.error) as e:
            QMessageBox.critical(self, "Connection error", str(e))

        if result:
            self.lblConnectedHost.setText("Host: %s@%s" % (username, host))
            self.lblConnectionStatus.setText("Status: Connected.")
        else:
            self.lblConnectionStatus.setText("Status: Disconnected.")

        self.refreshTreeView()
        return result

    def refreshTreeView(self):
        try:
            self.dbmsModel.setDB( self.db )

            # Auto expand root items
            i = 0
            invalid = QModelIndex()
            while self.dbmsModel.index(i,0,invalid).isValid():
                self.treeView.expand( self.dbmsModel.index(i,0,invalid) )
                i += 1
        except _mysql_exceptions.OperationalError as (errno, errmsg):
            if errno in (1018, # Can't read dir
                         2003, 2006): # Can't connect to
                if errno >= 2000:
                    self.lblConnectionStatus.setText("Status: Disconnected.")
                    QMessageBox.critical(self, "Connection error", str(errmsg))
            elif errno == 1045: # Access denied
                self.disconnect()
                QMessageBox.critical(self, "Database error", str(errmsg))
            else:
                QMessageBox.critical(self, "Database error", "[{0}] {1}".format(errno, errmsg))

    def disconnect(self):
        if self.db.isOpen():
            self.tabsWidget.clear()
            self.db.close()
            self.statusBar.showMessage("Disconnected.", 10000)
            self.refreshTreeView()

    @pyqtSignature("QString")
    def on_cmbConnection_activated(self, text):
        self.on_actionGo_triggered()

    @pyqtSignature("")
    def on_actionGo_triggered(self):
        self.connectToUrl( self.cmbConnection.lineEdit().text() )

    @pyqtSignature("")
    def on_actionRefresh_triggered(self):
        self.refreshTreeView()

    @pyqtSignature("")
    def on_actionReconnect_triggered(self):
        self.db.reconnect()

    @pyqtSignature("")
    def on_actionDisconnect_triggered(self):
        self.disconnect()
        self.cmbConnection.setEditText("")

    @pyqtSignature("")
    def on_actionAboutSQLAntaresia_triggered(self):
        QMessageBox.about(self, "About SQL Antaresia", u"SQL Antaresia is a MySQL administrative tool aimed at developers and sysadmins.\n\n© 2009-2012 Massimiliano Torromeo")

    def on_tabsWidget_tabCloseRequested(self, index):
        self.tabsWidget.removeTab( index )

    @pyqtSignature("")
    def on_actionConfigureConnections_triggered(self):
        dialog = Connections(self, self.configuredConnections)
        dialog.exec_()

        for section in self.config.sections():
            if section[0] != "@" and section not in self.configuredConnections:
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
        if len(self.treeView.selectedIndexes()) > 0:
            idx = self.treeView.selectedIndexes()[0]
            if type(idx.internalPointer()) is DatabaseTreeItem:
                dbName = idx.internalPointer().getName()
                index = self.tabsWidget.addTab( QueryTab(self.db, dbName), QIcon(":/16/icons/db.png"), "Query on %s" % (dbName) )
                self.tabsWidget.setCurrentIndex(index)

    def on_treeView_activated(self, modelIndex):
        if type(modelIndex.internalPointer()) is TableTreeItem:
            dbName = modelIndex.parent().internalPointer().getName()
            tableName = modelIndex.internalPointer().getName()

            index = self.tabsWidget.addTab( TableDetails(self.db, dbName, tableName), QIcon(":/16/icons/table.png"), "%s.%s" % (dbName, tableName) )
            self.tabsWidget.setCurrentIndex(index)

    def on_treeView_customContextMenuRequested(self, point):
        modelIndex = self.treeView.currentIndex()

        self.menuTable.clear()

        if type(modelIndex.internalPointer()) is DatabaseTreeItem:
            self.menuTable.addAction( self.actionNewQueryTab )
            self.menuTable.addAction( self.actionDropDatabase )

        if type(modelIndex.internalPointer()) is TableTreeItem:
            self.menuTable.addAction( self.actionShowCreate )
            self.menuTable.addAction( self.actionOptimizeTable )
            self.menuTable.addAction( self.actionRepairTable )
            self.menuTable.addAction( self.actionTruncateTable )
            self.menuTable.addAction( self.actionDropTable )

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
        if len(self.treeView.selectedIndexes()) > 0:
            idx = self.treeView.selectedIndexes()[0]
            if type(idx.internalPointer()) is TableTreeItem:
                dbName = idx.parent().internalPointer().getName()
                tableName = idx.internalPointer().getName()

                try:
                    cursor = self.db.connection().cursor()
                    cursor.execute("SHOW CREATE TABLE `%s`.`%s`;" % (dbName, tableName))
                    row = cursor.fetchone()
                    create = row[1]
                except _mysql_exceptions.ProgrammingError as (errno, errmsg): #@UnusedVariable
                    QMessageBox.critical(self, "Query result", errmsg)

                index = self.tabsWidget.addTab( QueryTab(self.db, dbName, query=create), QIcon(":/16/icons/db.png"), "Query on %s" % (dbName) )
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

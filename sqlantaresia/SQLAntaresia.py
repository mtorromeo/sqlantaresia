# -*- coding: utf-8 -*-
# File : SQLAntaresia.py
# Depends: pyqt4, python-qscintilla, python-paramiko

import ConfigParser
import os
import socket
import _mysql_exceptions
import paramiko
import application
import datetime
import MySQLdb

from PyQt4.QtCore import QObject, SIGNAL, pyqtSignature, QByteArray, Qt
from PyQt4.QtGui import QApplication, QMainWindow, QMessageBox, QMenu, QIcon, QDialog, QShortcut, QKeySequence, QHeaderView
from QMiddleClickCloseTabBar import QMiddleClickCloseTabBar

from ConfigureConnection import ConfigureConnection
from Ui_SQLAntaresiaWindow import Ui_SQLAntaresiaWindow
from SettingsDialog import SettingsDialog
from TableDetails import TableDetails
from QueryTab import QueryTab
from editor import SQLEditor
from DumpTab import DumpTab
from ProcessListTab import ProcessListTab
from connections import SQLServerConnection

from dbmodels import DBMSTreeModel, DatabaseTreeItem, TableTreeItem, ConnectionTreeItem, ProcedureTreeItem, FunctionTreeItem, TriggerTreeItem


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
                    username=self.getConf(connectionName, "username", None),
                    password=self.getConf(connectionName, "password", ""),
                    host=self.getConf(connectionName, "host", "localhost"),
                    port=self.getConfInt(connectionName, "port", 3306),
                    compression=self.getConfBool(connectionName, "compression", False),
                    use_tunnel=self.getConfBool(connectionName, "use_tunnel", False),
                    tunnel_username=self.getConf(connectionName, "tunnel_username", None),
                    tunnel_password=self.getConf(connectionName, "tunnel_password", ""),
                    tunnel_port=self.getConfInt(connectionName, "tunnel_port", 22),
                )

        # Setup UI
        self.setupUi(self)
        self.tabsWidget.clear()
        self.tabsWidget.setTabBar(QMiddleClickCloseTabBar())
        self.tabsWidget.setTabsClosable(True)
        self.tabsWidget.setMovable(True)
        self.tabsWidget.setDocumentMode(True)
        self.setUnifiedTitleAndToolBarOnMac(True)

        # Close tab shortcut
        closeTabShortcut = QShortcut(QKeySequence("CTRL+W"), self)
        closeTabShortcut.activated.connect(self.on_closeTabShortcut_activated)

        # TreeViewModel
        self.dbmsModel = DBMSTreeModel(self, self.connections)
        self.treeView.setModel(self.dbmsModel)

        # ContextMenu
        self.menuTable = QMenu(self.treeView)

        # Saved settings
        SQLEditor.font.fromString(self.getConf("@QueryEditor", "font", 'Monospace,12,-1,5,50,0,0,0,0,0'))
        TableDetails.defaultLimit = self.getConfInt("@TableDetails", "defaultLimit", 100)
        if self.config.has_section("@MainWindow"):
            self.restoreGeometry(QByteArray.fromBase64(self.getConf("@MainWindow", "geometry", "0")))
            self.splitter.restoreState(QByteArray.fromBase64(self.getConf("@MainWindow", "splitter", "0")))
            self.actionShowToolbar.setChecked(self.getConfBool("@MainWindow", "toolbar", True))
        else:
            size = self.size()
            self.splitter.setSizes([size.width() / 4, size.width() / 4 * 3])

        QObject.connect(self.actionAboutQt, SIGNAL("triggered()"),  QApplication.aboutQt)

    def closeEvent(self, event):
        for connectionName in self.connections:
            self.connections[connectionName].close()

        if "@MainWindow" not in self.config.sections():
            self.config.add_section("@MainWindow")
        self.config.set("@MainWindow", "geometry", self.saveGeometry().toBase64())
        self.config.set("@MainWindow", "splitter", self.splitter.saveState().toBase64())
        self.config.set("@MainWindow", "toolbar", self.toolBar.isVisible())

        with open(self.configFilename, "wb") as configfile:
            self.config.write(configfile)

    def on_closeTabShortcut_activated(self):
        idx = self.tabsWidget.currentIndex()
        if idx >= 0:
            self.tabsWidget.removeTab(idx)

    def getConf(self, section, name, defValue=None):
        try:
            return self.config.get(section, name)
        except ConfigParser.NoSectionError:
            return defValue
        except ConfigParser.NoOptionError:
            return defValue

    def getConfInt(self, section, name, defValue=None):
        return int(self.getConf(section, name, defValue))

    def getConfBool(self, section, name, defValue=False):
        try:
            return self.config.getboolean(section, name)
        except ConfigParser.NoSectionError:
            return defValue
        except ConfigParser.NoOptionError:
            return defValue

    def addQueryTab(self, connection, dbName, query=None, title=None):
        if not title:
            title = "Query on %s" % dbName
        index = self.tabsWidget.addTab(QueryTab(connection, dbName, query), QIcon(":/16/icons/database_edit.png"), title)
        self.tabsWidget.setCurrentIndex(index)

    def on_actionShowToolbar_toggled(self, checked):
        self.toolBar.setVisible(checked)

    @pyqtSignature("")
    def on_actionRefresh_triggered(self):
        self.dbmsModel.refresh()

        i = 0
        item = self.dbmsModel.item(i)
        while item:
            if item.getConnection().isOpen():
                item.open()
                self.treeView.setExpanded(item.index(), True)

            i += 1
            item = self.dbmsModel.item(i)

    @pyqtSignature("")
    def on_actionReconnect_triggered(self):
        for idx in self.treeView.selectedIndexes():
            item = idx.data(Qt.UserRole + 1).getConnectionItem()
            item.getConnection().reconnect()
            item.refresh()
            item.open()
            self.treeView.setExpanded(idx, True)

    @pyqtSignature("")
    def on_actionDisconnect_triggered(self):
        for idx in self.treeView.selectedIndexes():
            item = idx.data(Qt.UserRole + 1).getConnectionItem()
            item.getConnection().close()
            item.refresh()
            self.treeView.setExpanded(idx, False)

    @pyqtSignature("")
    def on_actionAboutSQLAntaresia_triggered(self):
        QMessageBox.about(self, "About %s" % application.name,
            u"<b>%s</b> v%s<br /><a href='%s'>%s</a><br /><br />%s<br /><br />© 2009-2012 <a href='mailto:massimiliano.torromeo@gmail.com'>Massimiliano Torromeo</a>" % (
                application.name,
                application.version,
                application.url, application.url,
                application.description,
            )
        )

    def on_tabsWidget_tabCloseRequested(self, index):
        self.tabsWidget.removeTab(index)

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
            self.config.set(name, "compression", connection.compression)
            self.config.set(name, "use_tunnel", connection.use_tunnel)
            self.config.set(name, "tunnel_username", connection.tunnel_username)
            self.config.set(name, "tunnel_password", connection.tunnel_password)
            self.config.set(name, "tunnel_port", connection.tunnel_port)

        with open(self.configFilename, "wb") as configfile:
            self.config.write(configfile)

    @pyqtSignature("")
    def on_actionPreferences_triggered(self):
        d = SettingsDialog()
        d.setEditorFont(SQLEditor.font)
        if not d.exec_():
            return

        for section in ("@QueryEditor", "@TableDetails"):
            if section not in self.config.sections():
                self.config.add_section(section)

        SQLEditor.font = d.lblSelectedFont.font()
        TableDetails.defaultLimit = d.spinDefaultLimit.value()
        self.config.set("@QueryEditor", "font", SQLEditor.font.toString())
        self.config.set("@TableDetails", "defaultLimit", TableDetails.defaultLimit)

        with open(self.configFilename, "wb") as configfile:
            self.config.write(configfile)

    @pyqtSignature("")
    def on_actionNewQueryTab_triggered(self):
        if not self.treeView.selectedIndexes():
            return

        idx = self.treeView.selectedIndexes()[0]
        item = idx.data(Qt.UserRole + 1)

        if type(item) is DatabaseTreeItem:
            dbName = item.text()
            self.addQueryTab(item.getConnection(), dbName)

    @pyqtSignature("")
    def on_actionShowProcessList_triggered(self):
        if not self.treeView.selectedIndexes():
            return

        idx = self.treeView.selectedIndexes()[0]
        connection = idx.data(Qt.UserRole + 1).getConnection()

        index = self.tabsWidget.addTab(ProcessListTab(connection), QIcon(":/16/icons/database_server.png"), "Process list of %s" % (connection.host))
        self.tabsWidget.setCurrentIndex(index)

    def on_treeView_activated(self, modelIndex):
        item = modelIndex.data(Qt.UserRole + 1)
        _type = type(item)

        if _type is TableTreeItem:
            parent = modelIndex.parent().data(Qt.UserRole + 1)
            dbName = parent.text()
            tableName = item.text()

            index = self.tabsWidget.addTab(TableDetails(item.getConnection(), dbName, tableName), QIcon(":/16/icons/database_table.png"), "%s.%s" % (dbName, tableName))
            self.tabsWidget.setCurrentIndex(index)

        elif _type is TriggerTreeItem:
            parent = modelIndex.parent().data(Qt.UserRole + 1)
            dbName = parent.text()
            trigName = item.text()

            try:
                conn = item.getConnection()
                cursor = conn.cursor()

                query = "SHOW TRIGGERS IN %s WHERE `Trigger` = ?;" % (conn.quoteIdentifier(dbName),)
                cursor.execute(query.replace("?", "%s"), trigName)
                row = cursor.fetchone()
                statement = row[3]
            except _mysql_exceptions.ProgrammingError as (errno, errmsg):  # @UnusedVariable
                QMessageBox.critical(self, "Query result", errmsg)
                return

            create = """DROP TRIGGER {trigger};

CREATE TRIGGER {trigger} {timing} {event} ON {table}
FOR EACH ROW
{statement};
""".format(
    trigger=conn.quoteIdentifier(trigName),
    timing=row[4],
    event=row[1],
    table=conn.quoteIdentifier(row[2]),
    statement=statement,
)

            self.addQueryTab(conn, dbName, create)

        elif _type in [ProcedureTreeItem, FunctionTreeItem]:
            parent = modelIndex.parent().data(Qt.UserRole + 1)
            dbName = parent.text()
            procName = item.name

            try:
                conn = item.getConnection()
                cursor = conn.cursor()

                cursor.execute("SHOW CREATE %s %s.%s;" % ("PROCEDURE" if _type is ProcedureTreeItem else "FUNCTION", conn.quoteIdentifier(dbName), conn.quoteIdentifier(procName)))
                row = cursor.fetchone()
                create = row[2]
            except _mysql_exceptions.ProgrammingError as (errno, errmsg):  # @UnusedVariable
                QMessageBox.critical(self, "Query result", errmsg)
                return

            self.addQueryTab(conn, dbName, create)

        elif not self.treeView.isExpanded(modelIndex):
            try:
                item.open()
            except _mysql_exceptions.OperationalError as (errnum, errmsg):
                QMessageBox.critical(self, "MySQL error (%d)" % errnum, errmsg)
            except paramiko.SSHException as e:
                QMessageBox.critical(self, "SSH error", str(e))
            except socket.error as e:
                QMessageBox.critical(self, "Network error", str(e))

    def on_treeView_customContextMenuRequested(self, point):
        item = self.treeView.currentIndex().data(Qt.UserRole + 1)
        _type = type(item)

        self.menuTable.clear()

        if _type is DatabaseTreeItem:
            self.menuTable.addAction(self.actionNewQueryTab)
            self.menuTable.addAction(self.actionShowCreate)
            self.menuTable.addAction(self.actionDumpDatabase)
            self.menuTable.addAction(self.actionDropDatabase)

        elif _type is TableTreeItem:
            self.menuTable.addAction(self.actionShowCreate)
            self.menuTable.addAction(self.actionDumpTable)
            self.menuTable.addAction(self.actionAnalyzeTable)
            self.menuTable.addAction(self.actionOptimizeTable)
            self.menuTable.addAction(self.actionRepairTable)
            self.menuTable.addAction(self.actionTruncateTable)
            self.menuTable.addAction(self.actionDropTable)

        elif _type is ConnectionTreeItem:
            self.menuTable.addAction(self.actionConfigureConnection)
            self.menuTable.addAction(self.actionRemoveConnection)
            if item.getConnection().isOpen():
                self.menuTable.addSeparator()
                self.menuTable.addAction(self.actionDisconnect)
                self.menuTable.addAction(self.actionReconnect)
                self.menuTable.addAction(self.actionShowProcessList)

        else:
            return

        self.menuTable.popup(self.treeView.mapToGlobal(point))

    def queryOnSelectedTables(self, queryTpl, listTables=False):
        queries = []
        conn = None

        for idx in self.treeView.selectedIndexes():
            item = idx.data(Qt.UserRole + 1)
            if type(item) is not TableTreeItem:
                continue

            # Use the first connection found
            if not conn:
                conn = item.getConnection()

            # Skip every selected db not using the same connection
            if conn != item.getConnection():
                continue

            dbName = item.parent().text()
            tableName = item.text()

            if listTables:
                queries.append("%s.%s" % (conn.quoteIdentifier(dbName), conn.quoteIdentifier(tableName)))
            else:
                queries.append(queryTpl % (conn.quoteIdentifier(dbName), conn.quoteIdentifier(tableName)))

        if listTables:
            query = queryTpl % (", ".join(queries))
        else:
            query = "\n".join(queries)

        self.addQueryTab(conn, dbName, query)

    @pyqtSignature("")
    def on_actionShowCreate_triggered(self):
        if not self.treeView.selectedIndexes():
            return

        idx = self.treeView.selectedIndexes()[0]
        item = idx.data(Qt.UserRole + 1)

        if type(item) not in [DatabaseTreeItem, TableTreeItem]:
            return

        try:
            conn = item.getConnection()
            cursor = conn.cursor()

            if type(item) is TableTreeItem:
                dbName = idx.parent().data(Qt.UserRole + 1).text()
                tableName = item.text()
                cursor.execute("SHOW CREATE TABLE %s.%s;" % (conn.quoteIdentifier(dbName), conn.quoteIdentifier(tableName)))
            else:
                dbName = item.text()
                cursor.execute("SHOW CREATE DATABASE %s;" % (conn.quoteIdentifier(dbName)))

            row = cursor.fetchone()
            create = row[1]
        except _mysql_exceptions.ProgrammingError as (errno, errmsg):  # @UnusedVariable
            QMessageBox.critical(self, "Query result", errmsg)

        index = self.tabsWidget.addTab(QueryTab(item.getConnection(), dbName, query=create), QIcon(":/16/icons/database.png"), "Query on %s" % dbName)
        self.tabsWidget.setCurrentIndex(index)

    @pyqtSignature("")
    def on_actionDumpDatabase_triggered(self):
        if not self.treeView.selectedIndexes():
            return

        idx = self.treeView.selectedIndexes()[0]
        item = idx.data(Qt.UserRole + 1)

        if type(item) is not DatabaseTreeItem:
            return

        dbName = item.text()
        conn = item.getConnection()

        index = self.tabsWidget.addTab(DumpTab(conn, dbName), QIcon(":/16/icons/save.png"), "Dump of %s" % dbName)
        self.tabsWidget.setCurrentIndex(index)

    @pyqtSignature("")
    def on_actionDumpTable_triggered(self):
        if not self.treeView.selectedIndexes():
            return

        idx = self.treeView.selectedIndexes()[0]
        item = idx.data(Qt.UserRole + 1)

        if type(item) is not TableTreeItem:
            return

        db = item.getConnection()
        dbName = idx.parent().data(Qt.UserRole + 1).text()
        quoteDbName = db.quoteIdentifier(dbName)
        tableName = db.quoteIdentifier(item.text())

        try:
            cursor = db.cursor()

            cursor.execute("SHOW CREATE TABLE %s.%s;" % (quoteDbName, tableName))
            row = cursor.fetchone()
            createTable = row[1]

            cursor.execute("SHOW VARIABLES LIKE 'version';")
            row = cursor.fetchone()
            serverVersion = row[1]

            dump = """-- {appName} {appVersion}
--
-- Host: {host}    Database: {dbName}
-- ------------------------------------------------------
-- Server version       {serverVersion}

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table {tableName}
--

DROP TABLE IF EXISTS {tableName};
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
{createTable};
/*!40101 SET character_set_client = @saved_cs_client */;
""".format(
    appName=application.name,
    appVersion=application.version,
    host=db.host,
    dbName=dbName,
    tableName=tableName,
    serverVersion=serverVersion,
    createTable=createTable,
)

            data = []
            cursor.execute("SELECT * FROM %s.%s;" % (quoteDbName, tableName))

            for row in cursor.fetchall():
                datarow = []
                for i, cell in enumerate(row):
                    if cell is None:
                        datarow.append("NULL")
                    elif cursor.description[i][1] in MySQLdb.BINARY:
                        datarow.append("0x%s" % cell.encode("hex"))
                    elif isinstance(cell, basestring):
                        try:
                            datarow.append("'%s'" % db.escapeString(cell.encode("utf-8")))
                        except UnicodeDecodeError:
                            datarow.append("0x%s" % cell.encode("hex"))
                    elif isinstance(cell, (int, long, float)):
                        datarow.append(str(cell))
                    else:
                        datarow.append("'%s'" % db.escapeString(str(cell)))
                        print type(cell), cell
                data.append("(%s)" % ",".join(datarow))

            if data:
                dump += """
--
-- Dumping data for table {tableName}
--

LOCK TABLES {tableName} WRITE;
/*!40000 ALTER TABLE {tableName} DISABLE KEYS */;
INSERT INTO {tableName} VALUES {data};
/*!40000 ALTER TABLE {tableName} ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;
""".format(
    tableName=tableName,
    data=",".join(data),
)
        except _mysql_exceptions.ProgrammingError as (errno, errmsg):  # @UnusedVariable
            QMessageBox.critical(self, "Query result", errmsg)

        dump += "\n-- Dump completed on %s\n" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        index = self.tabsWidget.addTab(QueryTab(item.getConnection(), dbName, query=dump), QIcon(":/16/icons/database.png"), "Dump of %s.%s" % (quoteDbName, tableName))
        self.tabsWidget.setCurrentIndex(index)

    @pyqtSignature("")
    def on_actionDropDatabase_triggered(self):
        queries = []
        conn = None

        for idx in self.treeView.selectedIndexes():
            item = idx.data(Qt.UserRole + 1)

            if type(item) is not DatabaseTreeItem:
                continue

            # Use the first connection found
            if not conn:
                conn = item.getConnection()

            # Skip every selected db not using the same connection
            if conn != item.getConnection():
                continue

            dbName = item.text()
            queries.append("DROP DATABASE %s;" % conn.quoteIdentifier(dbName))

        if conn and QMessageBox.question(self, "Confirmation request", "\n".join(queries) + "\n\nDo you want to proceed?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            try:
                conn.cursor().execute("\n".join(queries))
            except _mysql_exceptions.ProgrammingError as (errno, errmsg):  # @UnusedVariable
                QMessageBox.critical(self, "Query result", errmsg)
            self.on_actionRefresh_triggered()

    @pyqtSignature("")
    def on_actionDropTable_triggered(self):
        queries = []
        conn = None

        for idx in self.treeView.selectedIndexes():
            item = idx.data(Qt.UserRole + 1)
            if type(item) is TableTreeItem:
                # Use the first connection found
                if not conn:
                    conn = item.getConnection()

                # Skip every selected db not using the same connection
                if conn != item.getConnection():
                    continue

                dbName = item.parent().text()
                tableName = item.text()

                queries.append("DROP TABLE %s.%s" % (conn.quoteIdentifier(dbName), conn.quoteIdentifier(tableName)))

        if conn and QMessageBox.question(self, "Confirmation request", "\n".join(queries) + "\n\nDo you want to proceed?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            try:
                conn.cursor().execute("\n".join(queries))
            except _mysql_exceptions.ProgrammingError as (errno, errmsg):  # @UnusedVariable
                QMessageBox.critical(self, "Query result", errmsg)
            self.on_actionRefresh_triggered()

    @pyqtSignature("")
    def on_actionTruncateTable_triggered(self):
        self.queryOnSelectedTables("TRUNCATE TABLE %s.%s;")

    @pyqtSignature("")
    def on_actionAnalyzeTable_triggered(self):
        self.queryOnSelectedTables("ANALYZE TABLE %s;", listTables=True)

    @pyqtSignature("")
    def on_actionOptimizeTable_triggered(self):
        self.queryOnSelectedTables("OPTIMIZE TABLE %s;", listTables=True)

    @pyqtSignature("")
    def on_actionRepairTable_triggered(self):
        self.queryOnSelectedTables("REPAIR TABLE %s;", listTables=True)

    @pyqtSignature("")
    def on_actionConfigureConnection_triggered(self):
        if not self.treeView.selectedIndexes():
            return

        idx = self.treeView.selectedIndexes()[0]
        item = idx.data(Qt.UserRole + 1)

        if type(item) is not ConnectionTreeItem:
            return

        name = item.text()
        connection = item.getConnection()
        options = {
            "host": connection.host,
            "port": connection.port,
            "compression": connection.compression,
            "username": connection.username,
            "password": connection.password,
            "use_tunnel": connection.use_tunnel,
            "tunnel_port": connection.tunnel_port,
            "tunnel_username": connection.tunnel_username,
            "tunnel_password": connection.tunnel_password,
        }

        configDialog = ConfigureConnection(self, name, options)
        if configDialog.exec_() != QDialog.Accepted:
            return

        connection.host = options["host"]
        connection.port = options["port"]
        connection.compression = options["compression"]
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
            "compression": False,
            "username": "root",
            "password": "",
            "use_tunnel": False,
            "tunnel_port": 22,
            "tunnel_username": None,
            "tunnel_password": None
        }

        configDialog = ConfigureConnection(self, "", options)
        if configDialog.exec_() != QDialog.Accepted:
            return

        name = configDialog.connection
        if name not in self.connections:
            self.connections[name] = SQLServerConnection(**options)
            self.on_actionRefresh_triggered()
            self.saveConfig()

    @pyqtSignature("")
    def on_actionRemoveConnection_triggered(self):
        if not self.treeView.selectedIndexes():
            return

        idx = self.treeView.selectedIndexes()[0]
        item = idx.data(Qt.UserRole + 1)

        if type(item) is not ConnectionTreeItem:
            return

        name = item.text()
        connection = item.getConnection()

        if connection.isOpen():
            connection.close()

        del self.connections[name]
        self.on_actionRefresh_triggered()
        self.saveConfig()

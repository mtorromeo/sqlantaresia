# -*- coding: utf-8 -*-

from PyQt4.QtGui import QStandardItem, QStandardItemModel, QIcon


class BaseTreeItem(QStandardItem):
    def __init__(self, name):
        QStandardItem.__init__(self, name)
        self.setEditable(False)
        self.setColumnCount(1)
        self.setData(self)

    def getModel(self):
        item = self
        while item is not None and type(item) is not DBMSTreeModel:
            item = item.parent
        return item

    def getConnectionItem(self):
        item = self
        while item is not None and type(item) is not ConnectionTreeItem:
            item = item.parent()
        return item

    def getConnection(self):
        item = self.getConnectionItem()
        return item.connection if type(item) is ConnectionTreeItem else None

    def open(self):
        self.refresh()

    def refresh(self):
        self.setRowCount(0)

    def __repr__(self):
        return "<" + self.__class__.__name__ + " " + self.getName() + ">"


class ConnectionTreeItem(BaseTreeItem):
    def __init__(self, name, connection):
        BaseTreeItem.__init__(self, name)
        self.connection = connection
        self.refresh()

    def refresh(self):
        BaseTreeItem.refresh(self)

        if self.connection.isOpen():
            databases = EntityDatabasesTreeItem()
            privileges = EntityPrivilegesTreeItem()

            self.insertRow(0, databases)
            self.insertRow(1, privileges)

        self.refreshIcon()

    def open(self):
        if not self.connection.isOpen():
            self.connection.open()
            BaseTreeItem.open(self)

    def refreshIcon(self):
        if self.connection.isOpen():
            self.setIcon(QIcon(":/16/icons/database_server.png"))
        else:
            self.setIcon(QIcon(":/16/icons/database_connect.png"))


class EntityDatabasesTreeItem(BaseTreeItem):
    def __init__(self):
        BaseTreeItem.__init__(self, "Databases")
        self.setIcon(QIcon(":/16/icons/database.png"))
        self.setColumnCount(2)
        self.rowsByDb = {}

    def getDbList(self):
        def showDbSize(t):
            for row in t.result:
                i = self.rowsByDb[row[0]]
                self.setChild(i, 1, BaseTreeItem("%d MB" % (row[1] / 1024 / 1024)))

        self.getConnection().asyncQuery("SELECT TABLE_SCHEMA, SUM(DATA_LENGTH) + SUM(INDEX_LENGTH) FROM `information_schema`.`TABLES` GROUP BY TABLE_SCHEMA", callback=showDbSize)

        dblist = []
        db = self.getConnection().cursor()
        db.execute("SHOW DATABASES")
        for row in db.fetchall():
            dblist.append(row[0])
        return dblist

    def refresh(self):
        BaseTreeItem.refresh(self)

        self.rowsByDb = {}
        for i, db in enumerate(self.getDbList()):
            self.rowsByDb[db] = i
            self.insertRow(i, DatabaseTreeItem(db))


class EntityPrivilegesTreeItem(BaseTreeItem):
    def __init__(self):
        BaseTreeItem.__init__(self, "Privileges")
        self.setIcon(QIcon(":/16/icons/group.png"))

    def getPrivList(self):
        privlist = []
        db = self.getConnection().cursor()
        db.execute("SELECT GRANTEE FROM `information_schema`.`USER_PRIVILEGES` GROUP BY GRANTEE")
        for row in db.fetchall():
            privlist.append(row[0])
        return privlist

    def refresh(self):
        BaseTreeItem.refresh(self)

        for i, priv in enumerate(self.getPrivList()):
            self.insertRow(i, PrivilegeTreeItem(priv))


class DatabaseTreeItem(BaseTreeItem):
    def __init__(self, db):
        BaseTreeItem.__init__(self, db)
        self.setIcon(QIcon(":/16/icons/database.png"))
        self.setColumnCount(2)
        self.rowsByTable = {}

    def getTableList(self):
        def showTableSize(t):
            for row in t.result:
                size = row[1]
                if size is None:
                    size = 0

                i = self.rowsByTable[row[0]]
                self.setChild(i, 1, BaseTreeItem("%d MB" % (size / 1024 / 1024)))

        self.getConnection().asyncQuery("SELECT TABLE_NAME, DATA_LENGTH + INDEX_LENGTH FROM `information_schema`.`TABLES` WHERE TABLE_SCHEMA = %s", (self.text(),), callback=showTableSize)

        tablelist = []

        conn = self.getConnection()
        db = conn.cursor()

        db.execute("SHOW TABLES IN %s" % conn.quoteIdentifier(self.text()))
        for row in db.fetchall():
            tablelist.append(row[0])

        return tablelist

    def refresh(self):
        BaseTreeItem.refresh(self)

        self.rowsByTable = {}
        for i, table in enumerate(self.getTableList()):
            self.rowsByTable[table] = i
            self.insertRow(i, TableTreeItem(table))


class TableTreeItem(BaseTreeItem):
    def __init__(self, table):
        BaseTreeItem.__init__(self, table)
        self.setIcon(QIcon(":/16/icons/database_table.png"))


class PrivilegeTreeItem(BaseTreeItem):
    def __init__(self, priv):
        BaseTreeItem.__init__(self, priv)
        self.setIcon(QIcon(":/16/icons/user.png"))


class DBMSTreeModel(QStandardItemModel):
    def __init__(self, parent=None, connections=None):
        QStandardItemModel.__init__(self, parent)
        self.setConnections(connections)
        self.setColumnCount(1)
        self.setHorizontalHeaderLabels(["Connections", "Dimension"])

    def setConnections(self, connections):
        self.connections = connections
        self.refresh()

    def refresh(self):
        self.clear()

        try:
            for i, connectionName in enumerate(sorted(self.connections.iterkeys())):
                self.insertRow(i, ConnectionTreeItem(connectionName, self.connections[connectionName]))
        except Exception as e:
            self.clear()
            raise e
        finally:
            self.reset()

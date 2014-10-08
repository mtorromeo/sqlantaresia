# -*- coding: utf-8 -*-

from PyQt5.QtGui import QIcon, QStandardItem, QStandardItemModel


class BaseTreeItem(QStandardItem):
    def __init__(self, text, **kwds):
        super().__init__(text, **kwds)
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
    def __init__(self, connection, **kwds):
        super().__init__(**kwds)
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
            self.setIcon(QIcon(":/16/database-server"))
        else:
            self.setIcon(QIcon(":/16/database-connect"))


class EntityDatabasesTreeItem(BaseTreeItem):
    def __init__(self, **kwds):
        super().__init__(text="Databases", **kwds)
        self.setIcon(QIcon(":/16/database"))
        self.rowsByDb = {}

    def getDbList(self):
        def showDbSize(t):
            for row in t.result:
                i = self.rowsByDb[row[0]]
                self.setChild(i, 1, BaseTreeItem(text="%d MB" % (row[1] / 1024 / 1024)))

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
            self.insertRow(i, DatabaseTreeItem(text=db))


class EntityPrivilegesTreeItem(BaseTreeItem):
    def __init__(self, **kwds):
        super().__init__(text="Privileges", **kwds)
        self.setIcon(QIcon(":/16/group"))

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
            self.insertRow(i, PrivilegeTreeItem(text=priv))


class DatabaseTreeItem(BaseTreeItem):
    def __init__(self, **kwds):
        super().__init__(**kwds)
        self.setIcon(QIcon(":/16/database"))
        self.rowsByTable = {}

    def getTableList(self):
        def showTableSize(t):
            for row in t.result:
                size = row[1]
                if size is None:
                    size = 0

                i = self.rowsByTable[row[0]]
                self.setChild(i, 1, BaseTreeItem(text="%d MB" % (size / 1024 / 1024)))

        self.getConnection().asyncQuery("SELECT TABLE_NAME, DATA_LENGTH + INDEX_LENGTH FROM `information_schema`.`TABLES` WHERE TABLE_SCHEMA = %s", (self.text(),), callback=showTableSize)

        tablelist = []

        conn = self.getConnection()
        db = conn.cursor()

        db.execute("SHOW TABLES IN %s" % conn.quoteIdentifier(self.text()))
        for row in db.fetchall():
            tablelist.append(row[0])

        return tablelist

    def getTriggerList(self):
        triglist = []

        conn = self.getConnection()
        db = conn.cursor()

        db.execute("SHOW TRIGGERS FROM %s" % conn.quoteIdentifier(self.text()))
        for row in db.fetchall():
            triglist.append(row[0])

        return triglist

    def getProcedureList(self):
        proclist = []

        conn = self.getConnection()
        db = conn.cursor()

        db.execute("SHOW PROCEDURE STATUS WHERE Db=%s", (self.text(),))
        for row in db.fetchall():
            proclist.append(row[1])

        return proclist

    def getFunctionList(self):
        funclist = []

        conn = self.getConnection()
        db = conn.cursor()

        db.execute("SHOW FUNCTION STATUS WHERE Db=%s", (self.text(),))
        for row in db.fetchall():
            funclist.append(row[1])

        return funclist

    def refresh(self):
        BaseTreeItem.refresh(self)

        i = None
        for i, proc in enumerate(self.getProcedureList()):
            self.insertRow(i, ProcedureTreeItem(proc=proc))

        if i is None:
            i = -1

        for func in self.getFunctionList():
            i += 1
            self.insertRow(i, FunctionTreeItem(func=func))

        for trig in self.getTriggerList():
            i += 1
            self.insertRow(i, TriggerTreeItem(text=trig))

        self.rowsByTable = {}
        for table in self.getTableList():
            i += 1
            self.rowsByTable[table] = i
            self.insertRow(i, TableTreeItem(text=table))


class TableTreeItem(BaseTreeItem):
    def __init__(self, **kwds):
        super().__init__(**kwds)
        self.setIcon(QIcon(":/16/database-table"))


class PrivilegeTreeItem(BaseTreeItem):
    def __init__(self, **kwds):
        super().__init__(**kwds)
        self.setIcon(QIcon(":/16/user"))


class ProcedureTreeItem(BaseTreeItem):
    def __init__(self, proc, **kwds):
        super().__init__(text=proc + "()", **kwds)
        self.name = proc
        self.setIcon(QIcon(":/16/code"))


class FunctionTreeItem(BaseTreeItem):
    def __init__(self, func, **kwds):
        super().__init__(text=func + "()", **kwds)
        self.name = func
        self.setIcon(QIcon(":/16/code"))


class TriggerTreeItem(BaseTreeItem):
    def __init__(self, **kwds):
        super().__init__(**kwds)
        self.setIcon(QIcon(":/16/database-lightning"))


class DBMSTreeModel(QStandardItemModel):
    def __init__(self, connections=None, **kwds):
        super().__init__(**kwds)
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(["Connections", "Dimension"])
        self.setConnections(connections)

    def setConnections(self, connections):
        self.connections = connections
        self.refresh()

    def refresh(self):
        self.clear()

        try:
            for i, connectionName in enumerate(sorted(self.connections.keys())):
                self.insertRow(i, [ConnectionTreeItem(text=connectionName, connection=self.connections[connectionName]), BaseTreeItem(text="")])
        except Exception as e:
            self.clear()
            raise e
        finally:
            pass
            # self.beginResetModel()
            # self.endResetModel()

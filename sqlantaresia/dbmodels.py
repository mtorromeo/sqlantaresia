# -*- coding: utf-8 -*-

import _mysql_exceptions
from PyQt4 import QtCore, QtGui

class BaseTreeItem(object):
    """ Base class for composite pattern of trac data.
        Provides the basic abilities needed to treat all
        trac data as a tree.

        Used for the tree view.  Knows about the types of the class.
    """
    def __init__(self):
        pass

    def getName(self):
        return self.name

    def getToolTip(self, col):
        return None

    def getColumnData(self, col):
        """ Return the data for a given column. """
        if 0 == col:
            return self.getName()
        else:
            return ""

    def getActions(self):
        """ Return a list of QActions. This menu is used for any
            context specific interaction.
        """
        return []

    def getChildren(self):
        raise NotImplementedError

    def getParent(self):
        raise NotImplementedError

    def getIcon(self, col):
        raise NotImplementedError

    def getRow(self):
        raise NotImplementedError

    def getChild(self, index):
        return self.getChildren()[index]

    def getNChildren(self):
        return len(self.getChildren())

    def getPriorityKey(self):
        """ Helper method for priority based sorting.
        """
        return 0

    def getModel(self):
        item = self
        while item is not None and type(item) is not DBMSTreeModel:
            item = item.parent
        return item

    def getConnection(self):
        item = self
        while item is not None and type(item) is not ConnectionTreeItem:
            item = item.getParent()
        return item.connection if type(item) is ConnectionTreeItem else None

    def __repr__(self):
        return "<" + self.__class__.__name__ + " " + self.getName() + ">"

class ConnectionTreeItem(BaseTreeItem):
    def __init__(self, row, model, name, connection):
        self.parent = model
        self.row = row
        self.connection = connection
        self.name = name
        self.roots = []
        self.refreshData()

    def refreshData(self):
        if self.connection.isOpen():
            self.roots = [
                EntityDatabasesTreeItem(0, self, self.connection),
                EntityPrivilegesTreeItem(1, self, self.connection),
            ]
        else:
            self.roots = []

    def getParent(self):
        return None

    def getChildren(self):
        return self.roots

    def getRow(self):
        return self.row

    def getIcon(self, col):
        if self.connection.isOpen():
            return QtGui.QImage(":/16/icons/database_server.png")
        else:
            return QtGui.QImage(":/16/icons/database_connect.png")

    def open(self):
        if not self.connection.isOpen():
            self.parent.layoutAboutToBeChanged.emit()
            self.connection.open()
            self.refreshData()
            self.parent.layoutChanged.emit()


class EntityDatabasesTreeItem(BaseTreeItem):
    def __init__(self, row, parent, db):
        self.row = row
        self.parent = parent
        self.db = db
        self.name = "Databases"
        self.items = []
        self.__databases = []
        self.refreshData()

    def __getDbList(self):
        dblist = []
        db = self.db.connection().cursor()
        db.execute("SHOW DATABASES")
        for row in db.fetchall():
            dblist.append( row[0] )
        return dblist

    def refreshData(self):
        self.__databases = []
        self.items = []
        self.__databases = self.__getDbList()
        for i in range(len(self.__databases)):
            self.items.append(DatabaseTreeItem( i, self, self.db, self.__databases[i] ))

    def getParent(self):
        return self.parent

    def getChildren(self):
        return self.items

    def getRow(self):
        return self.row

    def getIcon(self, col):
        return QtGui.QImage(":/16/icons/database.png")

class EntityPrivilegesTreeItem(BaseTreeItem):
    def __init__(self, row, parent, db):
        self.row = row
        self.parent = parent
        self.db = db
        self.name = "Privileges"
        self.items = []
        self.__privileges = []
        self.refreshData()

    def __getList(self):
        _list = []
        db = self.db.connection().cursor()
        db.execute("SELECT GRANTEE FROM `information_schema`.`USER_PRIVILEGES` GROUP BY GRANTEE")
        for row in db.fetchall():
            _list.append( row[0] )
        return _list

    def refreshData(self):
        self.__privileges = self.__getList()
        self.items = []
        for i in range(len(self.__privileges)):
            self.items.append(PrivilegeTreeItem( i, self, self.db, self.__privileges[i] ))

    def getParent(self):
        return self.parent

    def getChildren(self):
        return self.items

    def getRow(self):
        return self.row

    def getIcon(self, col):
        return QtGui.QImage(":/16/icons/group.png")


class DatabaseTreeItem(BaseTreeItem):
    def __init__(self, row, parent, db, name):
        self.row = row
        self.parent = parent
        self.db = db
        self.name = name
        self.children = []
        self.refreshData()

    def refreshData(self):
        children = []
        db = self.db.connection().cursor()
        try:
            db.execute("SHOW TABLES IN %s" % self.db.escapeTableName(self.name))
            i = 0
            for row in db.fetchall():
                children.append( TableTreeItem( i, self, self.db, row[0] ) )
                i = i+1
        except _mysql_exceptions.OperationalError as e:
            if e.args[0] != 1018: # Can't read dir
                raise e
        finally:
            self.children = children

    def getParent(self):
        return self.parent

    def getChildren(self):
        return self.children

    def getRow(self):
        return self.row

    def getIcon(self, col):
        return QtGui.QImage(":/16/icons/database.png")

class TableTreeItem(BaseTreeItem):
    def __init__(self, row, parent, db, name):
        self.row = row
        self.parent = parent
        self.db = db
        self.name = name

    def getToolTip(self, col):
        return "table"

    def getChildren(self):
        return []

    def getParent(self):
        return self.parent

    def getRow(self):
        return self.row

    def getIcon(self, col):
        return QtGui.QImage(":/16/icons/database_table.png")

class PrivilegeTreeItem(BaseTreeItem):
    def __init__(self, row, parent, db, name):
        self.row = row
        self.parent = parent
        self.db = db
        self.name = name

    def getChildren(self):
        return []

    def getParent(self):
        return self.parent

    def getRow(self):
        return self.row

    def getIcon(self, col):
        return QtGui.QImage(":/16/icons/user.png")

class DBMSTreeModel(QtCore.QAbstractItemModel):
    def __init__(self, parent=None, connections=None):
        QtCore.QAbstractItemModel.__init__(self, parent)
        self.setConnections(connections)

    def setConnections(self, connections):
        self.connections = connections
        self.roots = []
        try:
            i = 0
            for connectionName in self.connections:
                self.roots.append( ConnectionTreeItem(i, self, connectionName, self.connections[connectionName]) )
                i += 1
        except Exception as e:
            self.roots = []
            raise e
        finally:
            self.reset()

    def refresh(self):
        present = []
        for i, item in enumerate(self.roots):
            name = item.getName()
            if name not in self.connections:
                del self.roots[i]
            else:
                present.append(name)

        for i, item in enumerate(self.roots):
            item.row = i

        for name in self.connections:
            if name not in present:
                i = len(self.roots)
                self.roots.append( ConnectionTreeItem(i, self, name, self.connections[name]) )

        self.reset()

    def rowCount(self, parentIdx):
        if parentIdx.isValid():
            return parentIdx.internalPointer().getNChildren()
        else:
            return len(self.roots)

    def columnCount(self, parent):
        return 1

    def data(self, index, role):
        if not index.isValid() or role is QtCore.Qt.EditRole:
            return None

        item = index.internalPointer()

        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.UserRole:
            return item.getColumnData(index.column())
        elif role == QtCore.Qt.DecorationRole:
            return item.getIcon(index.column())
        elif role == QtCore.Qt.ToolTipRole:
            return item.getToolTip(index.column())

        return None

    def parent(self, childIdx):
        if not childIdx.isValid():
            return QtCore.QModelIndex()

        child = childIdx.internalPointer()
        parent = child.getParent()
        if parent is None:
            return QtCore.QModelIndex()

        return self.createIndex(parent.getRow(), 0, parent);

    def index(self, row, column, parentIdx):
        if not self.hasIndex(row, column, parentIdx):
            return QtCore.QModelIndex()

        if not parentIdx.isValid():
            if len(self.roots)>=row:
                return self.createIndex(row, column, self.roots[row])
            else:
                return QtCore.QModelIndex()

        parent = parentIdx.internalPointer()
        if row >= parent.getNChildren():
            return QtCore.QModelIndex()

        return self.createIndex(row, column, parent.getChild(row))

    def headerData(self, col, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return "Connections"
        return None

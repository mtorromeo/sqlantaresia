# -*- coding: utf-8 -*-

from PyQt4 import QtCore, QtGui
from PyQt4.QtSql import QSqlQuery

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

	def getColumnData(self,col):
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

	def getIcon(self,col):
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
		if self.db.isOpen():
			q = QSqlQuery(self.db)
			q.exec_("SHOW DATABASES")
			while q.next():
				dblist.append( str(q.value(0).toString()) )
		return dblist

	def refreshData(self):
		self.__databases = self.__getDbList()
		self.items = []
		for i in range(len(self.__databases)):
			self.items.append(DatabaseTreeItem( i, self, self.db, self.__databases[i] ))

	def getParent(self):
		return self.parent

	def getChildren(self):
		return self.items

	def getRow(self):
		return self.row

	def getIcon(self, col):
		return QtGui.QImage(":/16/db.png")

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
		if self.db.isOpen():
			q = QSqlQuery(self.db)
			q.exec_("SELECT GRANTEE FROM `information_schema`.`USER_PRIVILEGES` GROUP BY GRANTEE")
			while q.next():
				_list.append( str(q.value(0).toString()) )
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
		return QtGui.QImage(":/16/system-users.png")


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
		if self.db.isOpen():
			q = QSqlQuery(self.db)
			q.exec_("SHOW TABLES IN %s" % self.db.escapeTableName(self.name))
			i = 0
			while q.next():
				children.append( TableTreeItem( i, self, self.db, q.value(0).toString() ) )
				i = i+1
		self.children = children

	def getParent(self):
		return self.parent

	def getChildren(self):
		return self.children

	def getRow(self):
		return self.row

	def getIcon(self, col):
		return QtGui.QImage(":/16/db.png")

class TableTreeItem(BaseTreeItem):
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
		return QtGui.QImage(":/16/table.png")

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
		return QtGui.QImage(":/16/user-properties.png")

class DBMSTreeModel(QtCore.QAbstractItemModel):
	def __init__(self, parent=None, db=None):
		QtCore.QAbstractItemModel.__init__(self, parent)
		self.db = db
		self.roots = []

	def setDB(self, db):
		self.db = db
		self.roots = [
			EntityDatabasesTreeItem(0, None, self.db),
			EntityPrivilegesTreeItem(1, None, self.db)
		]
		self.reset()

	def refresh(self):
		self.setDB(self.db)

	"""def refresh(self):
		olddatabases = self.databases
		self.databases = self.__getDbList()
		for i in range(len(olddatabases)-1,-1,-1):
			if olddatabases[i] not in self.databases:
				self.emit(QtCore.SIGNAL("rowsAboutToBeRemoved"), None,i,i)
				print "remove", olddatabases[i]
				del self.roots[i]
				self.emit(QtCore.SIGNAL("rowsRemoved"), None,i,i)
		for i in range(len(self.databases)):
			if self.databases[i] not in olddatabases:
				self.emit(QtCore.SIGNAL("rowsAboutToBeInserted"), None,i,i)
				print "insert", self.databases[i]
				self.roots.insert(i, DatabasesTreeItem( self, self.db, self.databases[i] ))
				self.emit(QtCore.SIGNAL("rowsInserted"), None,i,i)"""

	def rowCount(self, parentIdx):
		if parentIdx.isValid():
			return parentIdx.internalPointer().getNChildren()
		else:
			return len(self.roots)

	def columnCount(self, parent):
		return 1

	def data(self, index, role):
		if not index.isValid() or role is QtCore.Qt.EditRole:
			return QtCore.QVariant()

		if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.UserRole:
			return QtCore.QVariant( index.internalPointer().getColumnData(index.column()) )
		elif role == QtCore.Qt.DecorationRole:
			return QtCore.QVariant( index.internalPointer().getIcon(index.column()) )

		return QtCore.QVariant()

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
			return QtCore.QVariant("Databases")
		return QtCore.QVariant()

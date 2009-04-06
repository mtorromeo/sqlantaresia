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

	def getIcon(self,col):
		raise NotImplementedError

	def getActions(self):
		""" Return a list of QActions. This menu is used for any
			context specific interaction.
		"""
		return []

	def getChildren(self):
		raise NotImplementedError

	def getParent(self):
		raise NotImplementedError

	def getChild(self, index):
		return self.getChildren()[index]

	def getNChildren(self):
		return len(self.getChildren())

	def indexOf(self, item):
		children = self.getChildren()
		child_wrappers = [w.wrapped for w in children]
		index = child_wrappers.index(item.wrapped)
		return index
		#return self.getChildren().index(item)


	def getPriorityKey(self):
		""" Helper method for priority based sorting.
		"""
		return 0


class DatabasesTreeItem(BaseTreeItem):
	def __init__(self, parent, db, dbName):
		self.parent = parent
		self.db = db
		self.name = dbName
		self.children = []
		self.refreshData()

	def refreshData(self):
		children = []
		if self.db.isOpen():
			q = QSqlQuery(self.db)
			q.exec_("SHOW TABLES IN `%s`" % self.name.replace("`",""))
			while q.next():
				children.append( TableTreeItem( self, self.db, q.value(0).toString() ) )
		self.children = children

	def getIcon(self, col):
		return QtGui.QImage(":/16/db.png")

	def getParent(self):
		return self.parent

	def getChildren(self):
		return self.children


class TableTreeItem(BaseTreeItem):
	def __init__(self, parent, db, tableName):
		self.parent = parent
		self.db = db
		self.name = tableName

	def getIcon(self, col):
		return QtGui.QImage(":/16/table.png")

	def getChildren(self):
		return []

	def getParent(self):
		return self.parent

class DatabasesTreeModel(QtCore.QAbstractItemModel):
	def __init__(self, parent=None, db=None):
		QtCore.QAbstractItemModel.__init__(self, parent)
		self.db = db
		self.roots = []
		self.__databases = []

	def __getDbList(self):
		dblist = []
		if self.db.isOpen():
			q = QSqlQuery(self.db)
			q.exec_("SHOW DATABASES")
			while q.next():
				dblist.append( str(q.value(0).toString()) )
		return dblist

	def setDB(self, db):
		self.db = db
		self.databases = self.__getDbList()
		self.roots = []
		for database in self.databases:
			self.roots.append(DatabasesTreeItem( self, self.db, database ))
		self.reset()

	def refresh(self):
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
				self.emit(QtCore.SIGNAL("rowsInserted"), None,i,i)

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

	def makeIndex(self, row, col, obj):
		#self.leaky_bucket.append(obj)
		return self.createIndex(row, col, obj)

	def parent(self, childIdx):
		if not childIdx.isValid():
			return QtCore.QModelIndex()

		child = childIdx.internalPointer()
		if child in self.roots:
			return QtCore.QModelIndex()

		return self.indexOf(child.getParent())

	def index(self, row, column, parentIdx):
		# If parent invalid, return highest level items
		if not parentIdx.isValid():
			if len(self.roots)>=row:
				return self.makeIndex(row,column,self.roots[row])
			else:
				return QtCore.QModelIndex()
		parent = parentIdx.internalPointer()

		# If index is out of range, return problem
		if row >= parent.getNChildren():
			return QtCore.QModelIndex()

		return self.makeIndex(row, column, parent.getChild(row))


	def indexOf(self, item):
		if item in self.roots:
			return self.createIndex(0,0,item)

		parent = item.getParent()
		if parent is None or parent in self.roots:
			return self.createIndex(0,0,parent)

		row = parent.indexOf(item)
		return self.makeIndex(row, 0, item)

	def headerData(self, col, orientation, role):
		if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
			return QtCore.QVariant("Databases")
		return QtCore.QVariant()

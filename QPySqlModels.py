# -*- coding: utf-8 -*-
from PyQt4.QtCore import SIGNAL, QAbstractTableModel, Qt

from MySQLdb.cursors import SSCursor

class QPySelectModel(QAbstractTableModel):
	__rows = []
	__statement = None

	def __init__(self, parent, db):
		QAbstractTableModel.__init__(self, parent)
		self.db = db.connection().cursor(cursorclass=SSCursor)
	
	def __del__(self):
		self.db.close()
	
	def cursor(self):
		return self.db
	
	def select(self):
		self.__rows = []
		if self.__statement is not None:
			self.db.execute(self.__statement)
			for row in self.db.fetchall():
				self.__rows.append(row)
	
	def setSelect(self, statement):
		self.__statement = statement
	
	def rowCount(self, parent):
		return len(self.__rows)
	
	def columnCount(self, parent):
		return 0 if self.db.description is None else len(self.db.description)
	
	def data(self, index, role):
		if len(self.__rows)==0 or not index.isValid() or not role in [Qt.DisplayRole, Qt.UserRole] or index.row()>=len(self.__rows) or index.column()>=len(self.__rows[index.row()]):
			return None
		
		return self.__rows[index.row()][index.column()]
	
	def headerData(self, section, orientation, role):
		if role != Qt.DisplayRole or orientation == Qt.Vertical:
			return None
		
		try:
			return self.db.description[section][0]
		except:
			return None

class QPyTableModel(QPySelectModel):
	__tableName = None
	__filter = ""
	
	def setTable(self, tableName):
		self.__tableName = tableName
	
	def setFilter(self, where=""):
		self.__filter = where
	
	def select(self):
		statement = "SELECT * FROM `%s`" % self.__tableName
		if self.__filter != "":
			statement += " WHERE %s" % self.__filter
		self.setSelect(statement)
		QPySelectModel.select(self)
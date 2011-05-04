# -*- coding: utf-8 -*-
from PyQt4.QtCore import QAbstractTableModel, Qt

#from MySQLdb.cursors import SSCursor

class QPySelectModel(QAbstractTableModel):
	_rows = []
	_statement = None

	def __init__(self, parent, db):
		QAbstractTableModel.__init__(self, parent)
		#self.cursor = db.connection().cursor(cursorclass=SSCursor)
		self.cursor = db.connection().cursor()

	def __del__(self):
		self.cursor.close()

	def select(self):
		self._rows = []
		if self._statement is not None:
			self.cursor.execute(self._statement)
			for row in self.cursor.fetchall():
				self._rows.append(row)

	def setSelect(self, statement):
		self._statement = statement

	def rowCount(self, parent):
		return len(self._rows)

	def columnCount(self, parent):
		return 0 if self.cursor.description is None else len(self.cursor.description)

	def data(self, index, role):
		if len(self._rows)==0 or not index.isValid() or not role in [Qt.DisplayRole, Qt.UserRole] or index.row()>=len(self._rows) or index.column()>=len(self._rows[index.row()]):
			return None

		data = self._rows[index.row()][index.column()]
		return "NULL" if data is None else unicode(data)

	def headerData(self, section, orientation, role):
		if role != Qt.DisplayRole or orientation == Qt.Vertical:
			return None

		try:
			return self.cursor.description[section][0]
		except:
			return None

class QPyTableModel(QPySelectModel):
	_tableName = None
	_filter = ""

	def setTable(self, tableName):
		self._tableName = tableName

	def setFilter(self, where=""):
		self._filter = where

	def select(self):
		statement = "SELECT * FROM `%s`" % self._tableName
		if self._filter != "":
			statement += " WHERE %s" % self._filter
		self.setSelect(statement)
		QPySelectModel.select(self)
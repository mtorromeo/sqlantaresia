# -*- coding: utf-8 -*-
from PyQt4.QtCore import QAbstractTableModel, Qt

import operator

#from MySQLdb.cursors import SSCursor

class QPySelectModel(QAbstractTableModel):
    _rows = []
    _statement = None

    def __init__(self, parent, db):
        QAbstractTableModel.__init__(self, parent)
        self.db = db
        self.cursor = db.cursor()

    def __del__(self):
        self.cursor.close()

    def select(self):
        self._rows = []
        self._types = []

        if self._statement is not None:
            self.cursor.execute(self._statement)
            for row in self.cursor.fetchall():
                self._rows.append( list(row) )

            if self._rows:
                self._types = [description[1] for description in self.cursor.description]

    def setSelect(self, statement):
        self._statement = statement

    def rowCount(self, parent):
        return len(self._rows)

    def columnCount(self, parent):
        return 0 if self.cursor.description is None else len(self.cursor.description)

    def data(self, index, role):
        if not self._rows or not index.isValid() or not role in [Qt.DisplayRole, Qt.UserRole, Qt.EditRole] or index.row()>=len(self._rows) or index.column()>=len(self._rows[index.row()]):
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

    def sort(self, ncol, order):
        self.layoutAboutToBeChanged.emit()
        self._rows = sorted(self._rows, key=operator.itemgetter(ncol), reverse=(order == Qt.DescendingOrder))
        self.layoutChanged.emit()

class QPyTableModel(QPySelectModel):
    def __init__(self, parent, db):
        QPySelectModel.__init__(self, parent, db)
        self._tableName = None
        self._filter = ""
        self._limit = 0

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled

        return QAbstractTableModel.flags(self, index) | Qt.ItemIsEditable

    def setData(self, index, value, role):
        if index.isValid() and role == Qt.EditRole and len(self._primary_columns):
            row = self._rows[index.row()]

            where = []
            values = [value]

            for primary_column in self._primary_columns:
                for i, column in enumerate(self.cursor.description):
                    if column[0] == primary_column:
                        where.append( "%s = ?" % self.db.quoteIdentifier(primary_column) )
                        values.append( row[i] )
                        break

            query = "UPDATE %s SET %s = ? WHERE %s" % ( self.db.quoteIdentifier(self._tableName), self.db.quoteIdentifier( self.cursor.description[index.column()][0] ), " AND ".join(where))
            cursor = self.db.cursor()
            cursor.execute( query.replace('?', '%s'), values )

            self._rows[index.row()][index.column()] = value

            self.dataChanged.emit(index, index)
            return True

        return False

    def setTable(self, tableName):
        self._tableName = tableName

    def setFilter(self, where=""):
        self._filter = where

    def setLimit(self, limit=0):
        self._limit = int(limit)

    def select(self, primary_columns = None):
        self._primary_columns = [] if primary_columns is None else primary_columns
        statement = "SELECT * FROM %s" % self.db.quoteIdentifier(self._tableName)
        if self._filter:
            statement += " WHERE %s" % self._filter
        if self._limit:
            statement += " LIMIT %d" % self._limit
        self.setSelect(statement)
        QPySelectModel.select(self)
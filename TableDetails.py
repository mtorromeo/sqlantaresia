# -*- coding: utf-8 -*-
from PyQt4 import QtGui
from PyQt4.QtCore import QVariant, QObject, SIGNAL, pyqtSignature
from PyQt4.QtSql import *
from PyQt4.Qsci import QsciScintilla, QsciScintillaBase, QsciLexerSQL
from Ui_TableDetailsWidget import Ui_TableDetailsWidget

class TableDetails(QtGui.QTabWidget, Ui_TableDetailsWidget):
	def __init__(self, db, dbName, tableName):
		QtGui.QTabWidget.__init__(self)

		self.db = db
		self.dbName = dbName
		self.tableName = tableName

		self.queryStructure = QSqlQuery( """SELECT `COLUMN_NAME` AS 'Field', `COLUMN_TYPE` AS 'Type', `COLUMN_DEFAULT` AS 'Default', `IS_NULLABLE` AS 'Nullable', `COLUMN_KEY` AS 'Key', `EXTRA` AS 'Extra', `COLLATION_NAME` AS 'Collation'
FROM `information_schema`.`COLUMNS`
WHERE `TABLE_SCHEMA`=? AND `TABLE_NAME`=?
ORDER BY `ORDINAL_POSITION`""", self.db)
		self.queryStructure.addBindValue(QVariant(self.dbName))
		self.queryStructure.addBindValue(QVariant(self.tableName))
		self.queryStructure.exec_()

		self.setupUi(self)

		self.lexer = QsciLexerSQL()
		self.txtQuery.setFolding(QsciScintilla.NoFoldStyle)
		self.txtQuery.setMarginWidth(0, 30)
		self.txtQuery.setMarginLineNumbers(0, True)
		self.txtQuery.setLexer(self.lexer)
		self.txtQuery.setText("SELECT * FROM %s" % self.escapedTableName())

		self.activate()
		self.tableModel = QSqlTableModel(self, self.db)
		self.tableModel.setEditStrategy(QSqlTableModel.OnManualSubmit)
		self.tableModel.setTable( self.tableName )
		self.tableData.setModel( self.tableModel )

		self.refreshData()
		self.refreshStructure()

	def escapedDBName(self):
		return self.db.escapeTableName(self.dbName)

	def escapedTableName(self):
		return self.db.escapeTableName(self.tableName)

	@pyqtSignature("")
	def on_btnExecuteQuery_clicked(self):
		self.activate()
		queryModel = QSqlQueryModel(self)
		queryModel.setQuery( self.txtQuery.text(), self.db )
		self.tableQueryResult.setModel( queryModel )
		if queryModel.lastError().isValid():
			self.labelQueryError.setText( queryModel.lastError().databaseText() )
		else:
			self.labelQueryError.setText("")
			self.tableQueryResult.resizeColumnsToContents()

	@pyqtSignature("")
	def on_btnRefreshData_clicked(self):
		self.refreshData()

	def refreshData(self):
		self.activate()
		self.tableModel.setFilter("1 LIMIT 0,%d" % self.spinLimit.value())
		self.tableModel.select()
		self.tableModel.reset()
		self.tableData.resizeColumnsToContents()

	def refreshStructure(self):
		self.activate()
		modelStructure = QSqlQueryModel(self)
		#QObject.connect(modelStructure, SIGNAL("rowsInserted()"), self.tableStructure.resizeColumnsToContents)
		modelStructure.setQuery(self.queryStructure)
		self.tableStructure.setModel(modelStructure)
		self.tableStructure.resizeColumnsToContents()

		if self.queryStructure.lastError().isValid():
			print self.queryStructure.lastError().databaseText()

	def activate(self):
		self.db.setDatabaseName(self.dbName)
		self.db.open()

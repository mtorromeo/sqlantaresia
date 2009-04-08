# -*- coding: utf-8 -*-
from PyQt4 import QtGui
from PyQt4.QtCore import Qt, QLocale, QVariant, QObject, SIGNAL, pyqtSignature
from PyQt4.QtSql import *
from PyQt4.Qsci import QsciScintilla, QsciScintillaBase, QsciLexerSQL
from QXTableModel import QXTableModel
from Ui_TableDetailsWidget import Ui_TableDetailsWidget

class TableDetails(QtGui.QTabWidget, Ui_TableDetailsWidget):
	def __init__(self, db, dbName, tableName):
		QtGui.QTabWidget.__init__(self)

		self.db = db
		self.dbName = dbName
		self.tableName = tableName

		#Structure
		self.queryStructure = QSqlQuery( """SELECT `COLUMN_NAME` AS 'Field', `COLUMN_TYPE` AS 'Type', `COLUMN_DEFAULT` AS 'Default', `IS_NULLABLE` AS 'Nullable', `COLUMN_KEY` AS 'Key', `EXTRA` AS 'Extra', `COLLATION_NAME` AS 'Collation'
FROM `information_schema`.`COLUMNS`
WHERE `TABLE_SCHEMA`=? AND `TABLE_NAME`=?
ORDER BY `ORDINAL_POSITION`""", self.db)
		self.queryStructure.addBindValue(QVariant(self.dbName))
		self.queryStructure.addBindValue(QVariant(self.tableName))
		self.queryStructure.exec_()

		self.setupUi(self)

		#Query: Lexer
		self.lexer = QsciLexerSQL()
		self.txtQuery.setFolding(QsciScintilla.NoFoldStyle)
		self.txtQuery.setWrapMode(QsciScintilla.WrapWord)
		self.txtQuery.setMarginWidth(0, 30)
		self.txtQuery.setMarginLineNumbers(0, True)
		self.txtQuery.setLexer(self.lexer)
		self.txtQuery.setText("SELECT * FROM %s" % self.escapedTableName())

		#Data
		self.activate()
		self.tableModel = QXTableModel(self, self.db)
		self.tableModel.setEditStrategy(QSqlTableModel.OnManualSubmit)
		self.tableModel.setTable( self.tableName )
		QObject.connect(self.tableModel, SIGNAL("edited"), self.tableDataEdited)
		self.tableData.setModel( self.tableModel )

		#Retrieve
		self.refreshInfo()
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
			if queryModel.query().isSelect():
				self.labelQueryError.setText("%d rows returned" % queryModel.query().size())
			else:
				self.labelQueryError.setText("%d rows affected" % queryModel.query().numRowsAffected())
			self.tableQueryResult.resizeColumnsToContents()

	@pyqtSignature("")
	def on_btnRefreshData_clicked(self):
		self.refreshData()

	def refreshInfo(self):
		sysLocale = QLocale.system()

		q = QSqlQuery("SELECT `TABLE_TYPE`, `ENGINE`, `ROW_FORMAT`, `TABLE_ROWS`, `DATA_LENGTH`, `AUTO_INCREMENT`, `CREATE_TIME`, `UPDATE_TIME`, `CHECK_TIME`, `TABLE_COLLATION` FROM `information_schema`.`TABLES` WHERE TABLE_SCHEMA=? AND TABLE_NAME=?", self.db)
		q.addBindValue(QVariant(self.dbName))
		q.addBindValue(QVariant(self.tableName))
		q.exec_()
		q.first()
		self.lblTableInfo.setText("""<b>Type:</b> %s<br />
<b>Engine:</b> %s<br />
<b>Row Format:</b> %s<br />
<b>Number of rows:</b> %s<br />
<b>Data Length:</b> %s<br />
<b>Next Auto Increment:</b> %s<br />
<b>Created:</b> %s<br />
<b>Last Update:</b> %s<br />
<b>Last Check:</b> %s<br />
<b>Collation:</b> %s
""" % (
       q.value(0).toString(),
		 q.value(1).toString(),
		 q.value(2).toString(),
		 sysLocale.toString( q.value(3).toInt()[0] ),
		 sysLocale.toString( q.value(4).toInt()[0] ),
		 q.value(5).toString(),
		 q.value(6).toDateTime().toString(Qt.SystemLocaleDate),
		 q.value(7).toDateTime().toString(Qt.SystemLocaleDate),
		 q.value(8).toDateTime().toString(Qt.SystemLocaleDate),
		 q.value(9).toString()
		))

	def refreshData(self):
		self.activate()
		#TODO: Extend QSqlTableModel to implement a cleaner setLimit, the current workaround breaks the order by
		self.tableModel.select()
		self.tableModel.reset()
		self.tableData.resizeColumnsToContents()
		self.btnUndo.setEnabled(False)
		self.btnApply.setEnabled(False)

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

	def tableDataEdited(self):
		self.btnUndo.setEnabled(True)
		self.btnApply.setEnabled(True)

	@pyqtSignature("")
	def on_btnApply_clicked(self):
		self.tableModel.submitAll()
		if self.tableModel.lastError().isValid():
			self.lblDataSubmitResult.setText( self.tableModel.lastError().databaseText() )
		self.btnUndo.setEnabled(False)
		self.btnApply.setEnabled(False)

	@pyqtSignature("")
	def on_btnUndo_clicked(self):
		self.tableModel.revertAll()
		self.btnUndo.setEnabled(False)
		self.btnApply.setEnabled(False)

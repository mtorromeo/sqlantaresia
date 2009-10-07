# -*- coding: utf-8 -*-
from PyQt4 import QtGui
from PyQt4.QtCore import Qt, QLocale, QObject, SIGNAL, pyqtSignature
from PyQt4.QtSql import *
from PyQt4.Qsci import QsciScintilla, QsciScintillaBase, QsciLexerSQL
from Ui_QueryWidget import Ui_QueryWidget

class QueryTab(QtGui.QTabWidget, Ui_QueryWidget):
	def __init__(self, db, dbName, query="SHOW TABLES"):
		QtGui.QTabWidget.__init__(self)

		self.db = db
		self.dbName = dbName

		self.setupUi(self)

		#Query: Lexer
		self.lexer = QsciLexerSQL()
		self.txtQuery.setFolding(QsciScintilla.NoFoldStyle)
		self.txtQuery.setWrapMode(QsciScintilla.WrapWord)
		self.txtQuery.setMarginWidth(0, 30)
		self.txtQuery.setMarginLineNumbers(0, True)
		self.txtQuery.setLexer(self.lexer)
		self.txtQuery.setText(query)

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

	def activate(self):
		self.db.setDatabaseName(self.dbName)
		self.db.open()

# -*- coding: utf-8 -*-
from PyQt4 import QtGui
from PyQt4.QtCore import Qt, QLocale, QObject, SIGNAL, pyqtSignature
from PyQt4.Qsci import QsciScintilla, QsciScintillaBase, QsciLexerSQL
from QPySqlModels import QPySelectModel
import _mysql_exceptions

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
		self.db.setDatabase(self.dbName)
		queryModel = QPySelectModel(self, self.db)
		queryModel.setSelect( self.txtQuery.text() )
		try:
			queryModel.select()
			self.tableQueryResult.setModel( queryModel )
			#TODO: show affected rows
			"""if queryModel.query().isSelect():
				self.labelQueryError.setText("%d rows returned" % queryModel.query().size())
			else:
				self.labelQueryError.setText("%d rows affected" % queryModel.query().numRowsAffected())"""
			self.tableQueryResult.resizeColumnsToContents()
		except _mysql_exceptions.ProgrammingError as (errno, errmsg):
			self.labelQueryError.setText( errmsg )


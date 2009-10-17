# -*- coding: utf-8 -*-
from PyQt4.QtGui import QTabWidget, QColor, QFont
from PyQt4.QtCore import Qt, QLocale, QObject, SIGNAL, pyqtSignature
from PyQt4.Qsci import QsciScintilla, QsciScintillaBase, QsciLexerSQL
from QPySqlModels import QPySelectModel
import _mysql_exceptions

from Ui_QueryWidget import Ui_QueryWidget

class QueryTab(QTabWidget, Ui_QueryWidget):
	def __init__(self, db, dbName, query="SHOW TABLES"):
		QTabWidget.__init__(self)

		self.db = db
		self.dbName = dbName

		self.setupUi(self)
		
		self.lexer = QsciLexerSQL()
		
		self.lexer.setDefaultFont(QFont("fixed"))
		self.txtQuery.setMarginsFont(QFont("fixed", 14))
		
		bgColor = QColor(30,36,38,255)
		black = QColor(0,0,0,255)
		
		self.lexer.setDefaultColor(QColor(190,190,190,255))
		self.lexer.setColor(QColor(101,103,99,255), self.lexer.Comment)
		self.lexer.setColor(QColor(101,103,99,255), self.lexer.CommentLine)
		self.lexer.setColor(QColor(101,103,99,255), self.lexer.PlusComment)
		self.lexer.setColor(QColor(139,226,51,255), self.lexer.DoubleQuotedString)
		self.lexer.setColor(QColor(139,226,51,255), self.lexer.SingleQuotedString)
		self.lexer.setColor(QColor(114,160,207,255), self.lexer.Keyword)
		self.lexer.setColor(QColor(252,163,61,255), self.lexer.PlusKeyword)
		self.lexer.setPaper(bgColor)
		self.lexer.setDefaultPaper(bgColor)
		self.txtQuery.setSelectionBackgroundColor(black)
		self.txtQuery.setCaretLineVisible(True)
		self.txtQuery.setCaretLineBackgroundColor(QColor(44,53,56,255))
		self.txtQuery.setMarginsForegroundColor(bgColor)
		self.txtQuery.setMarginsBackgroundColor(black)
		self.txtQuery.setMatchedBraceBackgroundColor(QColor(89,71,47,255))

		self.txtQuery.setAutoIndent(True)
		self.txtQuery.setFolding(QsciScintilla.NoFoldStyle)
		self.txtQuery.setWrapMode(QsciScintilla.WrapWord)
		self.txtQuery.setMarginWidth(0, 30)
		self.txtQuery.setMarginLineNumbers(0, True)
		self.txtQuery.setBraceMatching(self.txtQuery.SloppyBraceMatch)
		
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


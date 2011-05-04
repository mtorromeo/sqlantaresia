# -*- coding: utf-8 -*-
from PyQt4.QtGui import QTabWidget, QColor, QFont
from PyQt4.QtCore import pyqtSignature
from PyQt4.Qsci import QsciScintilla, QsciLexerSQL
from QPySqlModels import QPySelectModel
import _mysql_exceptions

from Ui_QueryWidget import Ui_QueryWidget

class QueryTab(QTabWidget, Ui_QueryWidget):
	def __init__(self, db, dbName, query="SHOW TABLES", font=QFont("fixed")):
		QTabWidget.__init__(self)

		self.db = db
		self.dbName = dbName

		self.setupUi(self)
		
		self.lexer = QsciLexerSQL()
		
		self.lexer.setDefaultFont(font)
		self.lexer.setFont(font)
		self.txtQuery.setMarginsFont(font)
		
		fgColor = QColor(190,190,190,255)
		bgColor = QColor(30,36,38,255)
		black = QColor(0,0,0,255)
		comment = QColor(101,103,99,255)
		
		self.lexer.setDefaultColor(fgColor)
		self.lexer.setColor(fgColor, self.lexer.Default)
		self.lexer.setColor(comment, self.lexer.Comment)
		self.lexer.setColor(comment, self.lexer.CommentLine)
		self.lexer.setColor(comment, self.lexer.CommentDoc)
		self.lexer.setColor(QColor(204,33,33,255), self.lexer.Number)
		self.lexer.setColor(QColor(114,160,207,255), self.lexer.Keyword)
		self.lexer.setColor(QColor(139,226,51,255), self.lexer.DoubleQuotedString)
		self.lexer.setColor(QColor(139,226,51,255), self.lexer.SingleQuotedString)
		self.lexer.setColor(QColor(252,163,61,255), self.lexer.PlusKeyword)
		self.lexer.setColor(fgColor, self.lexer.Operator)
		self.lexer.setColor(fgColor, self.lexer.Identifier)
		self.lexer.setColor(comment, self.lexer.PlusComment)
		self.lexer.setColor(comment, self.lexer.CommentLineHash)
		self.lexer.setColor(comment, self.lexer.CommentDocKeyword)
		self.lexer.setColor(comment, self.lexer.CommentDocKeywordError)
		self.lexer.setPaper(bgColor)
		self.lexer.setDefaultPaper(bgColor)
		self.txtQuery.setCaretForegroundColor(fgColor)
		self.txtQuery.setSelectionBackgroundColor(black)
		self.txtQuery.setCaretLineVisible(True)
		self.txtQuery.setCaretLineBackgroundColor(QColor(44,53,56,255))
		self.txtQuery.setMarginsForegroundColor(bgColor)
		self.txtQuery.setMarginsBackgroundColor(black)
		self.txtQuery.setMatchedBraceForegroundColor(fgColor)
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
			if self.txtQuery.text().strip().lower().startswith('select'):
				self.labelQueryError.setText("%d rows returned" % queryModel.cursor.rowcount)
			else:
				self.labelQueryError.setText("%d rows affected" % queryModel.cursor.rowcount)
			self.tableQueryResult.resizeColumnsToContents()
		except _mysql_exceptions.ProgrammingError as (errno, errmsg):
			self.labelQueryError.setText( errmsg )

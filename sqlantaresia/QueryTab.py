# -*- coding: utf-8 -*-
from PyQt4.QtGui import QTabWidget, QColor, QFont, QToolBar, QFileDialog
from PyQt4.QtCore import pyqtSignature, Qt
from PyQt4.Qsci import QsciScintilla, QsciLexerSQL
from QPySqlModels import QPySelectModel
import _mysql_exceptions
import time
import codecs

from Ui_QueryWidget import Ui_QueryWidget

class QueryTab(QTabWidget, Ui_QueryWidget):
    font = QFont("fixed")

    def __init__(self, db, dbName, query="SHOW TABLES"):
        QTabWidget.__init__(self)

        self.db = db
        self.dbName = dbName
        self.queryFile = None

        self.setupUi(self)
        self.tableQueryResult.verticalHeader().hide()

        # toolbar
        self.toolbar = QToolBar(self)
        self.toolbar.addAction(self.actionLoadQuery)
        self.toolbar.addAction(self.actionSaveQuery)
        self.toolbar.addAction(self.actionSaveQueryAs)
        self.toolbarLayout.insertWidget(0, self.toolbar)

        self.lexer = QsciLexerSQL()

        self.lexer.setDefaultFont(self.font)
        self.lexer.setFont(self.font)
        self.txtQuery.setMarginsFont(self.font)

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
        self.txtQuery.setUtf8(True)
        self.txtQuery.setText(query)

    @pyqtSignature("")
    def on_actionLoadQuery_triggered(self):
        fileName = QFileDialog.getOpenFileName(self, "Load query", "", "SQL Files (*.sql)")
        if fileName:
            self.queryFile = fileName
            with codecs.open(fileName, "r", "utf-8") as f:
                sql = f.read()
            self.txtQuery.setText(sql)

    @pyqtSignature("")
    def on_actionSaveQuery_triggered(self):
        if not self.queryFile:
            self.on_actionSaveQueryAs_triggered()
        else:
            self.saveQuery(self.queryFile)

    @pyqtSignature("")
    def on_actionSaveQueryAs_triggered(self):
        fileName = QFileDialog.getSaveFileName(self, "Save query", "", "SQL Files (*.sql)")
        if fileName:
            self.queryFile = fileName
            self.saveQuery(fileName)

    def saveQuery(self, fileName):
        with codecs.open(fileName, "w", "utf-8") as f:
            f.write( self.txtQuery.text() )

    @pyqtSignature("")
    def on_btnExecuteQuery_clicked(self):
        self.db.setDatabase(self.dbName)
        queryModel = QPySelectModel(self, self.db)
        queryModel.setSelect( self.txtQuery.text() )
        try:
            elapsed = time.time()
            queryModel.select()
            elapsed = time.time() - elapsed
            self.tableQueryResult.setModel( queryModel )
            if self.txtQuery.text().strip().lower().startswith('select'):
                self.labelQueryError.setText("%d rows returned" % queryModel.cursor.rowcount)
            else:
                self.labelQueryError.setText("%d rows affected" % queryModel.cursor.rowcount)
            self.labelQueryTime.setText("Query took %f sec" % elapsed)
            self.tableQueryResult.resizeColumnsToContents()
        except (_mysql_exceptions.ProgrammingError, _mysql_exceptions.IntegrityError, _mysql_exceptions.OperationalError) as (errno, errmsg):
            self.labelQueryError.setText( errmsg )
            self.labelQueryTime.setText("")

        warningsModel = QPySelectModel(self, self.db)
        warningsModel.setSelect( "SHOW WARNINGS" )
        warningsModel.select()
        self.tableWarnings.setModel( warningsModel )
        self.tableWarnings.resizeRowsToContents()
        self.tableWarnings.resizeColumnsToContents()

        height = 0
        for i in range(len(warningsModel._rows)):
            height += self.tableWarnings.rowHeight(i)+2
        if height:
            height += 4
        self.tableWarnings.setMaximumHeight(height)

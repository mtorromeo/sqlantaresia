from PyQt4 import QtGui
from PyQt4 import Qsci

from zipfile import ZipFile
from gzip import GzipFile
from bz2 import BZ2File

import codecs


class SQLEditor(Qsci.QsciScintilla):
    font = QtGui.QFont("fixed")

    def __init__(self, parent):
        Qsci.QsciScintilla.__init__(self, parent)

        self.lexer = Qsci.QsciLexerSQL()
        self.lexer.setDefaultFont(self.font)
        self.lexer.setFont(self.font)
        self.setMarginsFont(self.font)

        fgColor = QtGui.QColor(190, 190, 190, 255)
        bgColor = QtGui.QColor(30, 36, 38, 255)
        black = QtGui.QColor(0, 0, 0, 255)
        comment = QtGui.QColor(101, 103, 99, 255)

        self.lexer.setDefaultColor(fgColor)
        self.lexer.setColor(fgColor, self.lexer.Default)
        self.lexer.setColor(comment, self.lexer.Comment)
        self.lexer.setColor(comment, self.lexer.CommentLine)
        self.lexer.setColor(comment, self.lexer.CommentDoc)
        self.lexer.setColor(QtGui.QColor(204, 33, 33, 255), self.lexer.Number)
        self.lexer.setColor(QtGui.QColor(114, 160, 207, 255), self.lexer.Keyword)
        self.lexer.setColor(QtGui.QColor(139, 226, 51, 255), self.lexer.DoubleQuotedString)
        self.lexer.setColor(QtGui.QColor(139, 226, 51, 255), self.lexer.SingleQuotedString)
        self.lexer.setColor(QtGui.QColor(252, 163, 61, 255), self.lexer.PlusKeyword)
        self.lexer.setColor(fgColor, self.lexer.Operator)
        self.lexer.setColor(fgColor, self.lexer.Identifier)
        self.lexer.setColor(comment, self.lexer.PlusComment)
        self.lexer.setColor(comment, self.lexer.CommentLineHash)
        self.lexer.setColor(comment, self.lexer.CommentDocKeyword)
        self.lexer.setColor(comment, self.lexer.CommentDocKeywordError)
        self.lexer.setPaper(bgColor)
        self.lexer.setDefaultPaper(bgColor)

        self.setCaretForegroundColor(fgColor)
        self.setSelectionBackgroundColor(black)
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QtGui.QColor(44, 53, 56, 255))
        self.setMarginsForegroundColor(bgColor)
        self.setMarginsBackgroundColor(black)
        self.setMatchedBraceForegroundColor(fgColor)
        self.setMatchedBraceBackgroundColor(QtGui.QColor(89, 71, 47, 255))

        self.setAutoIndent(True)
        self.setFolding(Qsci.QsciScintilla.NoFoldStyle)
        self.setWrapMode(Qsci.QsciScintilla.WrapWord)
        self.setMarginWidth(0, 30)
        self.setMarginLineNumbers(0, True)
        self.setBraceMatching(self.SloppyBraceMatch)

        self.setLexer(self.lexer)
        self.setUtf8(True)

        self.filename = None

    def loadDialog(self):
        filename = QtGui.QFileDialog.getOpenFileName(self, "Load query", "", "SQL Files (*.sql *.sql.gz *.sql.bz2 *.sql.zip)")
        if filename:
            self.filename = filename

            if self.filename.endswith(".gz"):
                opener = GzipFile
            elif self.filename.endswith(".bz2"):
                opener = BZ2File
            elif self.filename.endswith(".zip"):
                opener = ZipFile
            else:
                opener = open

            with codecs.EncodedFile(opener(self.filename, "r"), "utf-8") as f:
                sql = f.read()

            self.setText(sql)

    def saveAsDialog(self):
        filename = QtGui.QFileDialog.getSaveFileName(self, "Save query", "", "SQL Files (*.sql *.sql.gz *.sql.bz2 *.sql.zip)")
        if filename:
            self.filename = filename
            self.saveQuery(self.filename)

    def save(self):
        if not self.filename:
            self.saveAsDialog()
        else:
            self.saveQuery(self.filename)

    def saveQuery(self, filename):
        if filename.endswith(".gz"):
            opener = GzipFile
        elif filename.endswith(".bz2"):
            opener = BZ2File
        elif filename.endswith(".zip"):
            opener = ZipFile
        else:
            opener = open

        with codecs.EncodedFile(opener(self.filename, "w"), "utf-8") as f:
            f.write(self.text())

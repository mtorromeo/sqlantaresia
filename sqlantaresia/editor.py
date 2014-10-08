from PyQt5 import Qsci
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import QFileDialog

from zipfile import ZipFile
from gzip import GzipFile
from bz2 import BZ2File


class SQLEditor(Qsci.QsciScintilla):
    font = QFont("fixed")

    def __init__(self, parent, **kwds):
        super().__init__(parent, **kwds)

        self.lexer = Qsci.QsciLexerSQL()
        self.lexer.setDefaultFont(self.font)
        self.lexer.setFont(self.font)
        self.setMarginsFont(self.font)

        fgColor = QColor(190, 190, 190, 255)
        bgColor = QColor(30, 36, 38, 255)
        black = QColor(0, 0, 0, 255)
        comment = QColor(101, 103, 99, 255)

        self.lexer.setDefaultColor(fgColor)
        self.lexer.setColor(fgColor, self.lexer.Default)
        self.lexer.setColor(comment, self.lexer.Comment)
        self.lexer.setColor(comment, self.lexer.CommentLine)
        self.lexer.setColor(comment, self.lexer.CommentDoc)
        self.lexer.setColor(QColor(204, 33, 33, 255), self.lexer.Number)
        self.lexer.setColor(QColor(114, 160, 207, 255), self.lexer.Keyword)
        self.lexer.setColor(QColor(139, 226, 51, 255), self.lexer.DoubleQuotedString)
        self.lexer.setColor(QColor(139, 226, 51, 255), self.lexer.SingleQuotedString)
        self.lexer.setColor(QColor(252, 163, 61, 255), self.lexer.PlusKeyword)
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
        self.setCaretLineBackgroundColor(QColor(44, 53, 56, 255))
        self.setMarginsForegroundColor(bgColor)
        self.setMarginsBackgroundColor(black)
        self.setMatchedBraceForegroundColor(fgColor)
        self.setMatchedBraceBackgroundColor(QColor(89, 71, 47, 255))

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
        filename, _filter = QFileDialog.getOpenFileName(self, "Load query", "", "SQL Files (*.sql *.sql.gz *.sql.bz2 *.sql.zip)")
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

            with opener(self.filename, "rb") as f:
                sql = f.read().decode("utf-8")

            self.setText(sql)

    def saveAsDialog(self):
        filename, _filter = QFileDialog.getSaveFileName(self, "Save query", "", "SQL Files (*.sql *.sql.gz *.sql.bz2 *.sql.zip)")
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

        with opener(self.filename, "wb") as f:
            f.write(self.text().encode("utf-8"))

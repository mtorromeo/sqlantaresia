# -*- coding: utf-8 -*-
from PyQt4.QtGui import QTabWidget, QToolBar, QFileDialog
from PyQt4.QtCore import pyqtSignature
from QPySqlModels import QPySelectModel
import codecs

from Ui_QueryWidget import Ui_QueryWidget


class QueryTab(QTabWidget, Ui_QueryWidget):
    def __init__(self, db, dbName, query="SHOW TABLES"):
        QTabWidget.__init__(self)

        self.db = db
        self.dbName = dbName
        self.queryFile = None
        self.queryThread = None

        self.setupUi(self)
        self.tableQueryResult.verticalHeader().hide()

        # toolbar
        self.toolbar = QToolBar(self)
        self.toolbar.addAction(self.actionLoadQuery)
        self.toolbar.addAction(self.actionSaveQuery)
        self.toolbar.addAction(self.actionSaveQueryAs)
        self.toolbarLayout.insertWidget(0, self.toolbar)

        self.txtQuery.setText(query)

        self.btnKillQuery.setVisible(False)

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
            f.write(self.txtQuery.text())

    @pyqtSignature("")
    def on_btnExecuteQuery_clicked(self):
        self.db.setDatabase(self.dbName)
        queryModel = QPySelectModel(self, self.db)

        def queryTerminated():
            self.btnExecuteQuery.setVisible(True)
            self.btnKillQuery.setVisible(False)

        def queryExecuted(t):
            queryModel.setResult(t.result, t.cursor)
            self.tableQueryResult.setModel(queryModel)

            if self.txtQuery.text().strip().lower().startswith('select'):
                self.labelQueryError.setText("%d rows returned" % t.cursor.rowcount)
            else:
                self.labelQueryError.setText("%d rows affected" % t.cursor.rowcount)

            self.labelQueryTime.setText("Query took %f sec" % t.elapsed_time)
            self.tableQueryResult.resizeColumnsToContents()
            self.tableQueryResult.resizeRowsToContents()

            warningsModel = QPySelectModel(self, self.db)
            warningsModel.setSelect("SHOW WARNINGS")
            warningsModel.select()
            self.tableWarnings.setModel(warningsModel)
            self.tableWarnings.resizeColumnsToContents()
            self.tableWarnings.resizeRowsToContents()

            height = 0
            for i in range(len(warningsModel._rows)):
                height += self.tableWarnings.rowHeight(i) + 2
            if height:
                height += 4
            self.tableWarnings.setMaximumHeight(height)

            queryTerminated()

        def queryError(errno, errmsg):
            self.labelQueryError.setText(errmsg)
            self.labelQueryTime.setText("")
            queryTerminated()

        self.labelQueryError.setText("Running query...")
        self.labelQueryTime.setText("")
        self.btnExecuteQuery.setVisible(False)
        self.btnKillQuery.setVisible(True)

        self.queryThread = self.db.asyncQuery(self.txtQuery.text(), db=self.dbName, callback=queryExecuted, callback_error=queryError)

    @pyqtSignature("")
    def on_btnKillQuery_clicked(self):
        if self.queryThread:
            self.queryThread.kill()

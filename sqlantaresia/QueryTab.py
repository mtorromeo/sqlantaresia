# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QTabWidget, QToolBar
from PyQt5.QtCore import pyqtSlot
from .QPySqlModels import QPySelectModel

from .Ui_QueryWidget import Ui_QueryWidget


class QueryTab(QTabWidget, Ui_QueryWidget):
    def __init__(self, db, dbName, query="SHOW TABLES"):
        QTabWidget.__init__(self)

        self.db = db
        self.dbName = dbName
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

    @pyqtSlot()
    def on_actionLoadQuery_triggered(self):
        self.txtQuery.loadDialog()

    @pyqtSlot()
    def on_actionSaveQuery_triggered(self):
        self.txtQuery.save()

    @pyqtSlot()
    def on_actionSaveQueryAs_triggered(self):
        self.txtQuery.saveAsDialog()

    @pyqtSlot()
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

    @pyqtSlot()
    def on_btnKillQuery_clicked(self):
        if self.queryThread:
            self.queryThread.kill()

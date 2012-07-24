# -*- coding: utf-8 -*-
from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL, QObject, pyqtSignature

from QPySqlModels import *
import MySQLdb
import _mysql_exceptions
from QueryTab import QueryTab
import delegates

from Ui_TableDetailsWidget import Ui_TableDetailsWidget


class TableDetails(QtGui.QTabWidget, Ui_TableDetailsWidget):
    defaultLimit = 100

    def __init__(self, db, dbName, tableName):
        QtGui.QTabWidget.__init__(self)

        self.db = db
        self.dbName = dbName
        self.tableName = tableName

        self.setupUi(self)
        self.txtLimit.setValue(self.defaultLimit)

        self.lblQueryDesc.setText("SELECT * FROM %s WHERE" % self.db.quoteIdentifier(self.tableName))
        QObject.connect(self.txtWhere, SIGNAL("returnPressed()"), self.refreshData)

        self.db.setDatabase(self.dbName)

        #Retrieve
        self.refreshInfo()
        self.refreshStructure()
        self.refreshIndexes()

        #Data
        self.tableModel = QPyTableModel(self, self.db)
        self.tableModel.setTable(self.tableName)
        QObject.connect(self.tableModel, SIGNAL("edited"), self.tableDataEdited)
        self.tableData.setModel(self.tableModel)

        self.refreshData()

    def refreshInfo(self):
        db = self.db.connection().cursor()
        db.execute("SELECT `TABLE_TYPE`, `ENGINE`, `ROW_FORMAT`, `TABLE_ROWS`, `DATA_LENGTH`, `AUTO_INCREMENT`, `CREATE_TIME`, `UPDATE_TIME`, `CHECK_TIME`, `TABLE_COLLATION` FROM `information_schema`.`TABLES` WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s", (self.dbName, self.tableName))
        result = db.fetchone()
        #TODO: Localize dates
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
""" % result)

    def refreshData(self):
        self.db.setDatabase(self.dbName)
        self.tableModel.setFilter(self.txtWhere.text())
        self.tableModel.setLimit(self.txtLimit.text())
        try:
            self.tableModel.select(self.primary_columns)
        except _mysql_exceptions.ProgrammingError as (errno, errmsg):
            self.lblDataSubmitResult.setText(errmsg)
        self.tableModel.reset()
        self.tableData.resizeColumnsToContents()
        self.tableData.resizeRowsToContents()

        dateDelegate = None
        timeDelegate = None
        datetimeDelegate = None

        for i, _type in enumerate(self.tableModel._types):
            if _type in MySQLdb.DATE:
                if not dateDelegate:
                    dateDelegate = delegates.DateDelegate()
                self.tableData.setItemDelegateForColumn(i, dateDelegate)
            elif _type in MySQLdb.TIME:
                if not timeDelegate:
                    timeDelegate = delegates.TimeDelegate()
                self.tableData.setItemDelegateForColumn(i, timeDelegate)
            elif _type in MySQLdb.DATETIME:
                if not datetimeDelegate:
                    datetimeDelegate = delegates.DateTimeDelegate()
                self.tableData.setItemDelegateForColumn(i, datetimeDelegate)

        self.btnUndo.setEnabled(False)
        self.btnApply.setEnabled(False)

    def refreshStructure(self):
        self.db.setDatabase(self.dbName)
        modelStructure = QPySelectModel(self, self.db)
        modelStructure.setSelect("SHOW FULL COLUMNS FROM %s" % self.db.quoteIdentifier(self.tableName))
        try:
            modelStructure.select()
        except _mysql_exceptions.ProgrammingError as (errno, errmsg):
            self.lblDataSubmitResult.setText(errmsg)
        self.tableStructure.setModel(modelStructure)
        self.tableStructure.resizeColumnsToContents()
        self.tableStructure.resizeRowsToContents()

    def refreshIndexes(self):
        self.db.setDatabase(self.dbName)

        db = self.db.cursor(MySQLdb.cursors.DictCursor)
        db.execute("SHOW INDEX FROM %s" % self.db.quoteIdentifier(self.tableName))
        data = db.fetchall()

        labels = ["Key", "Type", "Unique", "Column", "Cardinality", "Packed", "Collation", "Null", "Comment"]
        modelIndexes = QtGui.QStandardItemModel(len(data), len(labels))

        self.primary_columns = []

        if data:
            for n, row in enumerate(data):
                if row["Key_name"] == "PRIMARY":
                    self.primary_columns.append(row["Column_name"])

                modelIndexes.setItem(n, 0, QtGui.QStandardItem(row["Key_name"]))
                modelIndexes.setItem(n, 1, QtGui.QStandardItem(row["Index_type"]))
                modelIndexes.setItem(n, 2, QtGui.QStandardItem(str(not row["Non_unique"])))
                modelIndexes.setItem(n, 3, QtGui.QStandardItem(row["Column_name"]))
                modelIndexes.setItem(n, 4, QtGui.QStandardItem(str(row["Cardinality"])))
                modelIndexes.setItem(n, 5, QtGui.QStandardItem("" if row["Packed"] is None else str(row["Packed"])))
                modelIndexes.setItem(n, 6, QtGui.QStandardItem(row["Collation"]))
                modelIndexes.setItem(n, 7, QtGui.QStandardItem(str(row["Null"])))
                modelIndexes.setItem(n, 8, QtGui.QStandardItem(row["Comment"]))

            modelIndexes.setHorizontalHeaderLabels(labels)

        self.tableIndexes.setModel(modelIndexes)
        self.tableIndexes.resizeColumnsToContents()
        self.tableIndexes.resizeRowsToContents()

    def tableDataEdited(self):
        self.btnUndo.setEnabled(True)
        self.btnApply.setEnabled(True)

    @pyqtSignature("")
    def on_btnEditQuery_clicked(self):
        where = self.txtWhere.text()
        if not where:
            where = "1"
        limit = int(self.txtLimit.text())
        if limit:
            limit = " LIMIT %d" % limit
        else:
            limit = ""
        index = self.window().tabsWidget.addTab(
            QueryTab(
                db=self.db,
                dbName=self.dbName,
                query="SELECT * FROM %s WHERE %s%s" % (self.db.quoteIdentifier(self.tableName), where, limit)
            ),
            QtGui.QIcon(":/16/icons/database_edit.png"),
            "Query on %s" % (self.dbName)
        )
        self.window().tabsWidget.setCurrentIndex(index)

    @pyqtSignature("")
    def on_btnRefreshData_clicked(self):
        self.refreshData()

    @pyqtSignature("")
    def on_btnApply_clicked(self):
        self.tableModel.submitAll()
        if self.tableModel.lastError().isValid():
            self.lblDataSubmitResult.setText(self.tableModel.lastError().databaseText())
        self.btnUndo.setEnabled(False)
        self.btnApply.setEnabled(False)

    @pyqtSignature("")
    def on_btnUndo_clicked(self):
        self.tableModel.revertAll()
        self.btnUndo.setEnabled(False)
        self.btnApply.setEnabled(False)

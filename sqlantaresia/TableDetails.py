# -*- coding: utf-8 -*-
from PyQt5.QtCore import QObject, pyqtSlot
from PyQt5.QtWidgets import QTabWidget
from PyQt5.QtGui import QStandardItem, QStandardItemModel

from mysql.connector.constants import FieldType
from mysql.connector import Error as MySQLError

from .QPySqlModels import *
from .QueryTab import QueryTab
from . import delegates

from .Ui_TableDetailsWidget import Ui_TableDetailsWidget


class TableDetails(QTabWidget, Ui_TableDetailsWidget):
    defaultLimit = 100

    def __init__(self, db, dbName, tableName, **kwds):
        super().__init__(**kwds)

        self.db = db
        self.dbName = dbName
        self.tableName = tableName

        self.setupUi(self)
        self.txtLimit.setValue(self.defaultLimit)

        self.lblQueryDesc.setText("SELECT * FROM %s WHERE" % self.db.quoteIdentifier(self.tableName))
        self.txtWhere.returnPressed.connect(self.refreshData)

        self.db.setDatabase(self.dbName)

        #Retrieve
        self.refreshInfo()
        self.refreshStructure()
        self.refreshIndexes()

        #Data
        self.tableModel = QPyTableModel(self, self.db)
        self.tableModel.setTable(self.tableName)
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
        except MySQLError as exc:
            (errno, errmsg) = exc.args
            self.lblDataSubmitResult.setText(errmsg)
        self.tableModel.beginResetModel()
        self.tableModel.endResetModel()
        self.tableData.resizeColumnsToContents()
        self.tableData.resizeRowsToContents()

        self.dateDelegate = None
        self.timeDelegate = None
        self.datetimeDelegate = None

        for i, _type in enumerate(self.tableModel._types):
            if _type is FieldType.DATE:
                if not self.dateDelegate:
                    self.dateDelegate = delegates.DateDelegate()
                self.tableData.setItemDelegateForColumn(i, self.dateDelegate)
            elif _type is FieldType.TIME:
                if not self.timeDelegate:
                    self.timeDelegate = delegates.TimeDelegate()
                self.tableData.setItemDelegateForColumn(i, self.timeDelegate)
            elif _type in (FieldType.DATETIME, FieldType.TIMESTAMP):
                if not self.datetimeDelegate:
                    self.datetimeDelegate = delegates.DateTimeDelegate()
                self.tableData.setItemDelegateForColumn(i, self.datetimeDelegate)

    def refreshStructure(self):
        self.db.setDatabase(self.dbName)
        modelStructure = QPySelectModel(self, self.db)
        modelStructure.setSelect("SHOW FULL COLUMNS FROM %s" % self.db.quoteIdentifier(self.tableName))
        try:
            modelStructure.select()
        except MySQLError as exc:
            (errno, errmsg) = exc.args
            self.lblDataSubmitResult.setText(errmsg)
        self.tableStructure.setModel(modelStructure)
        self.tableStructure.resizeColumnsToContents()
        self.tableStructure.resizeRowsToContents()

    def refreshIndexes(self):
        self.db.setDatabase(self.dbName)

        db = self.db.cursor(dictionary=True)
        db.execute("SHOW INDEX FROM %s" % self.db.quoteIdentifier(self.tableName))
        data = db.fetchall()

        labels = ["Key", "Type", "Unique", "Column", "Cardinality", "Packed", "Collation", "Null", "Comment"]
        modelIndexes = QStandardItemModel(len(data), len(labels))

        self.primary_columns = []

        if data:
            for n, row in enumerate(data):
                if row["Key_name"] == "PRIMARY":
                    self.primary_columns.append(row["Column_name"])

                modelIndexes.setItem(n, 0, QStandardItem(row["Key_name"]))
                modelIndexes.setItem(n, 1, QStandardItem(row["Index_type"]))
                modelIndexes.setItem(n, 2, QStandardItem(str(not row["Non_unique"])))
                modelIndexes.setItem(n, 3, QStandardItem(row["Column_name"]))
                modelIndexes.setItem(n, 4, QStandardItem(str(row["Cardinality"])))
                modelIndexes.setItem(n, 5, QStandardItem("" if row["Packed"] is None else str(row["Packed"])))
                modelIndexes.setItem(n, 6, QStandardItem(row["Collation"]))
                modelIndexes.setItem(n, 7, QStandardItem(str(row["Null"])))
                modelIndexes.setItem(n, 8, QStandardItem(row["Comment"]))

            modelIndexes.setHorizontalHeaderLabels(labels)

        self.tableIndexes.setModel(modelIndexes)
        self.tableIndexes.resizeColumnsToContents()
        self.tableIndexes.resizeRowsToContents()

    @pyqtSlot()
    def on_btnEditQuery_clicked(self):
        where = self.txtWhere.text()
        if not where:
            where = "1"
        limit = int(self.txtLimit.text())
        if limit:
            limit = " LIMIT %d" % limit
        else:
            limit = ""

        self.window().addQueryTab(self.db, self.dbName, "SELECT * FROM %s WHERE %s%s" % (self.db.quoteIdentifier(self.tableName), where, limit))

    @pyqtSlot()
    def on_btnRefreshData_clicked(self):
        self.refreshData()

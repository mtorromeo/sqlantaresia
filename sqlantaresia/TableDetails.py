# -*- coding: utf-8 -*-
from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL, QObject, pyqtSignature

from QPySqlModels import *
import MySQLdb
from QueryTab import QueryTab
import delegates

from Ui_TableDetailsWidget import Ui_TableDetailsWidget
from _mysql_exceptions import Error as MySQLError


class QIndexButton(QtGui.QToolButton):
    def __init__(self, text, index):
        QtGui.QToolButton.__init__(self)
        self.setText(text)
        self.index = index


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
        except MySQLError as (errno, errmsg):
            self.lblDataSubmitResult.setText(errmsg)
        self.tableModel.reset()
        self.tableData.resizeColumnsToContents()
        self.tableData.resizeRowsToContents()

        self.dateDelegate = None
        self.timeDelegate = None
        self.datetimeDelegate = None

        for i, _type in enumerate(self.tableModel._types):
            if _type in MySQLdb.DATE:
                if not self.dateDelegate:
                    self.dateDelegate = delegates.DateDelegate()
                self.tableData.setItemDelegateForColumn(i, self.dateDelegate)
            elif _type in MySQLdb.TIME:
                if not self.timeDelegate:
                    self.timeDelegate = delegates.TimeDelegate()
                self.tableData.setItemDelegateForColumn(i, self.timeDelegate)
            elif _type in MySQLdb.DATETIME:
                if not self.datetimeDelegate:
                    self.datetimeDelegate = delegates.DateTimeDelegate()
                self.tableData.setItemDelegateForColumn(i, self.datetimeDelegate)

    def refreshStructure(self):
        self.columnDrops = []

        self.db.setDatabase(self.dbName)

        db = self.db.cursor(MySQLdb.cursors.DictCursor)
        db.execute("SHOW FULL COLUMNS FROM %s" % self.db.quoteIdentifier(self.tableName))
        data = db.fetchall()

        labels = ["", "Field", "Type", "Collation", "Null", "Key", "Default", "Extra", "Comment"]
        modelStructure = QtGui.QStandardItemModel(len(data), len(labels))

        for n, row in enumerate(data):
            modelStructure.setItem(n, 0, QtGui.QStandardItem(""))
            modelStructure.setItem(n, 1, QtGui.QStandardItem(row["Field"]))
            modelStructure.setItem(n, 2, QtGui.QStandardItem(row["Type"]))
            modelStructure.setItem(n, 3, QtGui.QStandardItem(row["Collation"]))
            modelStructure.setItem(n, 4, QtGui.QStandardItem(row["Null"]))
            modelStructure.setItem(n, 5, QtGui.QStandardItem(row["Key"]))
            modelStructure.setItem(n, 6, QtGui.QStandardItem(row["Default"]))
            modelStructure.setItem(n, 7, QtGui.QStandardItem(row["Extra"]))
            modelStructure.setItem(n, 8, QtGui.QStandardItem(row["Comment"]))

        modelStructure.setHorizontalHeaderLabels(labels)

        self.tableStructure.setModel(modelStructure)
        self.tableStructure.resizeColumnsToContents()
        self.tableStructure.resizeRowsToContents()

        for n in range(modelStructure.rowCount()):
            index = modelStructure.index(n, 0)
            button = QIndexButton(str(n), index)
            button.setIcon(QtGui.QIcon(":/10/icons/edit-delete-small.png"))
            button.setCheckable(True)
            button.clicked.connect(self.on_btnDeleteField_clicked)
            self.tableStructure.setIndexWidget(index, button)

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

        self.window().addQueryTab(self.db, self.dbName, "SELECT * FROM %s WHERE %s%s" % (self.db.quoteIdentifier(self.tableName), where, limit))

    @pyqtSignature("")
    def on_btnRefreshData_clicked(self):
        self.refreshData()

    def on_btnDeleteField_clicked(self):
        button = self.sender()
        n = int(button.text())
        index = self.tableStructure.model().index(n, 1)
        item = self.tableStructure.model().itemFromIndex(index)
        field_name = item.text()
        self.columnDrops.append(field_name)

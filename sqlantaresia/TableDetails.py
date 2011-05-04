# -*- coding: utf-8 -*-
from PyQt4 import QtGui
from PyQt4.QtCore import SIGNAL, QLocale, QObject, pyqtSignature

from QPySqlModels import *
import _mysql_exceptions
from QueryTab import QueryTab

from Ui_TableDetailsWidget import Ui_TableDetailsWidget

class TableDetails(QtGui.QTabWidget, Ui_TableDetailsWidget):
    def __init__(self, db, dbName, tableName):
        QtGui.QTabWidget.__init__(self)

        self.db = db
        self.dbName = dbName
        self.tableName = tableName

        self.setupUi(self)
        self.lblQueryDesc.setText( "SELECT * FROM %s WHERE" % self.db.escapeTableName(self.tableName) )
        QObject.connect(self.txtWhere, SIGNAL("returnPressed()"), self.refreshData)

        self.db.setDatabase(self.dbName)

        #Data
        self.tableModel = QPyTableModel(self, self.db)
        self.tableModel.setTable( self.tableName )
        QObject.connect(self.tableModel, SIGNAL("edited"), self.tableDataEdited)
        self.tableData.setModel( self.tableModel )

        #Retrieve
        self.refreshInfo()
        self.refreshData()
        self.refreshStructure()

    def refreshInfo(self):
        sysLocale = QLocale.system()

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
        self.tableModel.setFilter( self.txtWhere.text() )
        self.tableModel.setLimit( self.txtLimit.text() )
        try:
            self.tableModel.select()
        except _mysql_exceptions.ProgrammingError as (errno, errmsg):
            self.lblDataSubmitResult.setText( errmsg )
        self.tableModel.reset()
        self.tableData.resizeColumnsToContents()
        self.btnUndo.setEnabled(False)
        self.btnApply.setEnabled(False)

    def refreshStructure(self):
        self.db.setDatabase(self.dbName)
        modelStructure = QPySelectModel(self, self.db)
        modelStructure.setSelect("SHOW FULL COLUMNS FROM %s" % self.db.escapeTableName(self.tableName))
        try:
            modelStructure.select()
        except _mysql_exceptions.ProgrammingError as (errno, errmsg):
            self.lblDataSubmitResult.setText( errmsg )
        self.tableStructure.setModel(modelStructure)
        self.tableStructure.resizeColumnsToContents()

    def tableDataEdited(self):
        self.btnUndo.setEnabled(True)
        self.btnApply.setEnabled(True)

    @pyqtSignature("")
    def on_btnEditQuery_clicked(self):
        where = self.txtWhere.text()
        if not where:
            where = "1"
        limit = int( self.txtLimit.text() )
        if limit:
            limit = " LIMIT %d" % limit
        else:
            limit = ""
        index = self.window().tabsWidget.addTab(
            QueryTab(
                db = self.db,
                dbName = self.dbName,
                query = "SELECT * FROM %s WHERE %s%s" % (self.db.escapeTableName(self.tableName), where, limit)
            ),
            QtGui.QIcon(":/16/icons/db.png"),
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
            self.lblDataSubmitResult.setText( self.tableModel.lastError().databaseText() )
        self.btnUndo.setEnabled(False)
        self.btnApply.setEnabled(False)

    @pyqtSignature("")
    def on_btnUndo_clicked(self):
        self.tableModel.revertAll()
        self.btnUndo.setEnabled(False)
        self.btnApply.setEnabled(False)

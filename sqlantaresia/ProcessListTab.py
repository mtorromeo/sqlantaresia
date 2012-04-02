# -*- coding: utf-8 -*-
from PyQt4.QtGui import QTabWidget
from PyQt4.QtCore import pyqtSignature, QTimer
from QPySqlModels import QPySelectModel

from Ui_ProcessListWidget import Ui_ProcessListWidget

class ProcessListTab(QTabWidget, Ui_ProcessListWidget):
    def __init__(self, connection):
        QTabWidget.__init__(self)

        self.connection = connection

        self.setupUi(self)
        self.tableProcessList.verticalHeader().hide()

        cur = self.connection.cursor()
        cur.execute("SHOW TABLES IN information_schema LIKE 'PROCESSLIST'")
        self.processListInInfoSchema = cur.rowcount

        self.refresh()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer_timeout)
        self.on_spinSeconds_valueChanged( self.spinSeconds.value() )
        self.on_chkAutoRefresh_stateChanged()

    def on_chkAutoRefresh_stateChanged(self):
        if self.chkAutoRefresh.isChecked():
            self.timer.start()
        else:
            self.timer.stop()

    @pyqtSignature("int")
    def on_spinSeconds_valueChanged(self, seconds):
        self.timer.setInterval( seconds * 1000 )

    @pyqtSignature("")
    def on_btnRefresh_clicked(self):
        self.refresh()

    def on_timer_timeout(self):
        self.refresh()

    def refresh(self):
        queryModel = QPySelectModel(self, self.connection)
        if self.processListInInfoSchema:
            queryModel.setSelect( "SELECT ID, USER, HOST, DB, COMMAND, TIME + TIME_MS/1000 AS TIME, STATE, INFO, ROWS_SENT, ROWS_EXAMINED, ROWS_READ FROM information_schema.PROCESSLIST ORDER BY TIME DESC, TIME_MS DESC" )
        else:
            queryModel.setSelect( "SHOW FULL PROCESSLIST" )
        queryModel.select()
        self.tableProcessList.setModel( queryModel )
        self.tableProcessList.resizeColumnsToContents()

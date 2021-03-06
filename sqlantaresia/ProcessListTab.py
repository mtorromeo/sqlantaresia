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

        if self.processListInInfoSchema:
            self.processListColumns = []
            cur.execute("SHOW COLUMNS IN information_schema.PROCESSLIST")
            for column in cur.fetchall():
                self.processListColumns.append(column[0])

            try:
                self.processListColumns.remove("TIME_MS")
                idx_time = self.processListColumns.index("TIME")
                self.processListColumns[idx_time] = "TIME + TIME_MS/1000 AS TIME"
            except ValueError:
                pass

        else:
            self.chkShowIdle.hide()

        self.refresh()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_timer_timeout)
        self.on_spinSeconds_valueChanged(self.spinSeconds.value())
        self.on_chkAutoRefresh_stateChanged()

    def on_chkAutoRefresh_stateChanged(self):
        if self.chkAutoRefresh.isChecked():
            self.timer.start()
        else:
            self.timer.stop()

    @pyqtSignature("int")
    def on_spinSeconds_valueChanged(self, seconds):
        self.timer.setInterval(seconds * 1000)

    @pyqtSignature("")
    def on_btnRefresh_clicked(self):
        self.refresh()

    def on_timer_timeout(self):
        self.refresh()

    def refresh(self):
        queryModel = QPySelectModel(self, self.connection)
        if self.processListInInfoSchema:
            where = "" if self.chkShowIdle.isChecked() else "WHERE STATE != ''"
            queryModel.setSelect("SELECT %s FROM information_schema.PROCESSLIST %s ORDER BY TIME DESC" % (",".join(self.processListColumns), where))
        else:
            queryModel.setSelect("SHOW FULL PROCESSLIST")
        queryModel.select()
        self.tableProcessList.setModel(queryModel)
        self.tableProcessList.resizeColumnsToContents()

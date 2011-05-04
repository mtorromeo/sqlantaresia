# -*- coding: utf-8 -*-
from PyQt4.QtCore import Qt, pyqtSignature
from PyQt4.QtGui import QMessageBox, QDialog, QStringListModel
from Ui_ConnectionsDialog import Ui_ConnectionsDialog

from ConfigureConnection import ConfigureConnection

class Connections(QDialog, Ui_ConnectionsDialog):
    def __init__(self, parent=None, connections={}):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.connections = connections

        self.connectionsModel = QStringListModel()
        self.connectionsList = []
        for connection in self.connections:
            self.connectionsList.append(connection)
        self.connectionsModel.setStringList(self.connectionsList)

        self.listConnections.setModel(self.connectionsModel)

    def refreshConnections(self):
        self.connectionsModel.setStringList(self.connectionsList)
        self.connectionsModel.reset()

    @pyqtSignature("")
    def on_btnAdd_clicked(self):
        connectionOptions = {
            "host": "localhost",
            "port": 3306,
            "database": None,
            "username": "root",
            "password": "",
            "useTunnel": False,
            "tunnelPort": 0,
            "tunnelUsername": None,
            "tunnelPassword": None
        }
        configDialog = ConfigureConnection(self, "", connectionOptions)
        if configDialog.exec_() == QDialog.Accepted:
            self.connections[configDialog.connection] = connectionOptions
            self.connectionsList.append(configDialog.connection)
            self.refreshConnections()

    @pyqtSignature("")
    def on_btnDel_clicked(self):
        idx = self.listConnections.currentIndex()
        connection = self.connectionsModel.data(idx, Qt.DisplayRole)

        msgBox = QMessageBox()
        msgBox.setText('Do you really want to delete the connection "%s"?' % connection)
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msgBox.setDefaultButton(QMessageBox.No)
        if msgBox.exec_() == QMessageBox.Yes:
            try:
                self.connectionsList.remove(connection)
            except ValueError: pass
            del self.connections[connection]
            self.refreshConnections()

    @pyqtSignature("")
    def on_btnProps_clicked(self):
        idx = self.listConnections.currentIndex()
        connection = self.connectionsModel.data(idx, Qt.DisplayRole)

        configDialog = ConfigureConnection(self, connection, self.connections[connection])
        if configDialog.exec_() == QDialog.Accepted:
            if connection != configDialog.connection:
                    self.connectionsModel.setData(idx, configDialog.connection,  Qt.DisplayRole)
                    self.connections[configDialog.connection] = self.connections[connection]
                    self.connectionsList.append(configDialog.connection)
                    del self.connections[connection]
                    try:
                        self.connectionsList.remove(connection)
                    except ValueError: pass
                    self.refreshConnections()

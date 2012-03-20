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
            "use_tunnel": False,
            "tunnel_port": 0,
            "tunnel_username": None,
            "tunnel_password": None
        }
        configDialog = ConfigureConnection(self, "", connectionOptions)
        if configDialog.exec_() == QDialog.Accepted:
            name = configDialog.connection
            if name not in self.connections:
                self.connections[name] = SQLServerConnection( **connectionOptions )
                self.connectionsList.append(name)
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
        name = self.connectionsModel.data(idx, Qt.DisplayRole)
        connection = self.connections[name]
        options = {
            "host": connection.host,
            "port": connection.port,
            "database": connection.database,
            "username": connection.username,
            "password": connection.password,
            "use_tunnel": connection.use_tunnel,
            "tunnel_port": connection.tunnel_port,
            "tunnel_username": connection.tunnel_username,
            "tunnel_password": connection.tunnel_password,
        }

        configDialog = ConfigureConnection(self, name, options)
        if configDialog.exec_() == QDialog.Accepted:
            connection.host = options["host"]
            connection.port = options["port"]
            connection.database = options["database"]
            connection.username = options["username"]
            connection.password = options["password"]
            connection.use_tunnel = options["use_tunnel"]
            connection.tunnel_port = options["tunnel_port"]
            connection.tunnel_username = options["tunnel_username"]
            connection.tunnel_password = options["tunnel_password"]

            if name != configDialog.connection:
                    self.connectionsModel.setData(idx, configDialog.connection,  Qt.DisplayRole)
                    self.connections[configDialog.connection] = connection
                    self.connectionsList.append(configDialog.connection)
                    del self.connections[name]
                    try:
                        self.connectionsList.remove(name)
                    except ValueError: pass
                    self.refreshConnections()

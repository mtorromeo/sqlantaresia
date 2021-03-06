# -*- coding: utf-8 -*-
from PyQt4.QtCore import Qt, QObject,  SIGNAL
from PyQt4.QtGui import QDialog, QMessageBox
from Ui_ConfigureConnectionDialog import Ui_ConfigureConnectionDialog


class ConfigureConnection(QDialog, Ui_ConfigureConnectionDialog):
    def __init__(self, parent=None, connectionName="", connectionOptions={}):
        QDialog.__init__(self, parent)
        self.setupUi(self)

        self.connection = connectionName
        self.connectionOptions = connectionOptions

        self.txtName.setText(self.connection)
        self.txtHost.setText(self.connectionOptions["host"])
        self.txtPort.setText(str(self.connectionOptions["port"]))
        self.chkCompression.setChecked(self.connectionOptions["compression"])
        self.txtUsername.setText(self.connectionOptions["username"])
        self.txtPassword.setText(self.connectionOptions["password"])

        self.checkTunnel.setChecked(self.connectionOptions["use_tunnel"])

        if self.connectionOptions["tunnel_port"] is not None:
            self.txtTunnelPort.setText(str(self.connectionOptions["tunnel_port"]))
        if self.connectionOptions["tunnel_username"] is not None:
            self.txtTunnelUsername.setText(self.connectionOptions["tunnel_username"])
        if self.connectionOptions["tunnel_password"] is not None:
            self.txtTunnelPassword.setText(self.connectionOptions["tunnel_password"])

        QObject.connect(self, SIGNAL("accepted()"), self.onAccept)

    def on_checkTunnel_stateChanged(self, state):
        self.groupTunnel.setEnabled(state == Qt.Checked)

    def on_buttonBox_accepted(self):
        emptyChecks = (
            (self.txtName, "You have to specify the name for the connection"),
            (self.txtHost, "You have to specify the host name to connect to"),
            (self.txtUsername, "You have to specify the username of the connection"),
        )
        for check in emptyChecks:
            if check[0].text() == "" or check[0].text().isspace():
                QMessageBox.warning(self, "Data validation error", check[1])
                check[0].selectAll()
                check[0].setFocus()
                return

        if self.txtName.text()[0] == "@":
            QMessageBox.warning(self, "Data validation error", "Invalid connection name")
            self.txtName.selectAll()
            self.txtName.setFocus()
            return

        port = int(self.txtPort.text())
        if port <= 0 or port > 65535:
            QMessageBox.warning(self, "Data validation error", "The specified port for the connection is invalid")
            self.txtPort.selectAll()
            self.txtPort.setFocus()
            return

        if self.checkTunnel.isChecked():
            port = int(self.txtTunnelPort.text())
            if port <= 0 or port > 65535:
                QMessageBox.warning(self, "Data validation error", "The specified port for the tunnel is invalid")
                self.txtTunnelPort.selectAll()
                self.txtTunnelPort.setFocus()
                return

            if self.txtTunnelUsername.text() == "" or self.txtTunnelUsername.text().isspace():
                QMessageBox.warning(self, "Data validation error", "You have to specify the username for the tunnel")
                self.txtTunnelUsername.selectAll()
                self.txtTunnelUsername.setFocus()
                return

        self.accept()

    def onAccept(self):
        self.connection = self.txtName.text()
        self.connectionOptions["host"] = self.txtHost.text()
        self.connectionOptions["port"] = int(self.txtPort.text())
        self.connectionOptions["compression"] = self.chkCompression.isChecked()
        self.connectionOptions["username"] = self.txtUsername.text()
        self.connectionOptions["password"] = self.txtPassword.text()
        self.connectionOptions["use_tunnel"] = self.checkTunnel.isChecked()
        self.connectionOptions["tunnel_port"] = int(self.txtTunnelPort.text())
        self.connectionOptions["tunnel_username"] = self.txtTunnelUsername.text()
        self.connectionOptions["tunnel_password"] = self.txtTunnelPassword.text()

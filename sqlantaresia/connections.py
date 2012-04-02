# -*- coding: utf-8 -*-

import os
import select
import paramiko
import socket
import _mysql_exceptions
import MySQLdb
import SocketServer

from threading import Thread
from PyQt4.QtGui import QMessageBox, QApplication
from DBUtils.PersistentDB import PersistentDB

try:
    import Crypto.Random as Random
except ImportError:
    Random = None

class ForwardServer(SocketServer.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True

class Handler(SocketServer.BaseRequestHandler):
    def handle(self):
        try:
            chan = self.ssh_transport.open_channel('direct-tcpip', (self.chain_host, self.chain_port), self.request.getpeername())
        except Exception, e:
            return

        if chan is None:
            return

        while True:
            r, w, x = select.select([self.request, chan], [], [])
            if self.request in r:
                data = self.request.recv(1024)
                if len(data) == 0:
                    break
                chan.send(data)
            if chan in r:
                data = chan.recv(1024)
                if len(data) == 0:
                    break
                self.request.send(data)
        chan.close()
        self.request.close()

class TunnelThread(Thread):
    def __init__(self, ssh_server, local_port=0, ssh_port=22, remote_host="localhost", remote_port=None, username=None, password=None):
        Thread.__init__(self)
        if Random:
            Random.atfork()
        if remote_port is None:
            remote_port = local_port
        self.local_port = local_port
        self.remote_host = remote_host
        self.remote_port = remote_port

        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.load_system_host_keys()
        self.ssh_client.set_missing_host_key_policy(paramiko.WarningPolicy())
        self.ssh_client.connect(ssh_server, ssh_port, username=username, password=password, look_for_keys=True)

        transport = self.ssh_client.get_transport()
        transport.set_keepalive(30)

        class SubHandler(Handler):
            chain_host = remote_host
            chain_port = remote_port
            ssh_transport = transport
        self.ffwd_server = ForwardServer(('', self.local_port), SubHandler)
        self.ip, self.local_port = self.ffwd_server.server_address

    def run(self):
        self.ffwd_server.serve_forever()

    def join(self):
        if self.ffwd_server is not None:
            self.ffwd_server.shutdown()
        self.ssh_client.close()
        del self.ffwd_server
        del self.ssh_client
        Thread.join(self)

class SQLServerConnection(object):
    tunnel = None
    dbpool = None

    def __init__(self, username = None, password = "", host = "localhost", port = 3306, database = "", use_tunnel = False, tunnel_username = None, tunnel_password = None, tunnel_port = 22):
        if username is None:
            try:
                self.username = os.getlogin()
            except:
                self.username = ""
        else:
            self.username = username

        self.password = password
        self.host = host
        self.port = port
        self.database = database
        self.use_tunnel = use_tunnel

        if use_tunnel and tunnel_username is None:
            try:
                tunnel_username = os.getlogin()
            except:
                tunnel_username = ""

        self.tunnel_username = tunnel_username
        self.tunnel_password = tunnel_password
        self.tunnel_port = tunnel_port

    def connection(self):
        if not self.isOpen():
            self.open()
        return self.dbpool.connection()

    def cursor(self):
        return self.connection().cursor()

    def setDatabase(self, database):
        return self.cursor().execute("USE `%s`" % database)

    def enableTunnel(self, username, password):
        self.use_tunnel = True
        self.tunnel_username = username
        self.tunnel_password = password

    def disableTunnel(self):
        self.use_tunnel = False
        self.close()

    def isOpen(self):
        return self.dbpool is not None

    def open(self):
        try:
            if self.use_tunnel and self.tunnel is None:
                self.tunnel = TunnelThread(username = self.tunnel_username, password = self.tunnel_password, ssh_server = self.host, ssh_port = self.tunnel_port, remote_port = self.port)
                self.tunnel.start()
                host = "127.0.0.1"
                port = self.tunnel.local_port
            else:
                host = self.host
                port = self.port
            self.dbpool = PersistentDB(creator = MySQLdb, host = host, port = port, user = self.username, passwd = self.password, charset = "utf8", use_unicode = True, setsession = ['SET AUTOCOMMIT = 1'])
            # test connection
            self.cursor().execute("SELECT 1")
        except (socket.error, _mysql_exceptions.OperationalError) as e:
            self.close()
            raise e


    def close(self):
        if self.tunnel is not None:
            self.tunnel.join()
            del self.tunnel
            self.tunnel = None
        self.dbpool = None

    def reconnect(self):
        self.close()
        self.open()

    def escapeTableName(self, tableName):
        return "`%s`" % tableName

    def confirmQuery(self, sql):
        if QMessageBox.question(QApplication.activeWindow(), "Query confirmation request", "%s\nAre you sure?" % sql, QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            db = self.connection().cursor()
            try:
                db.execute(sql)
            except _mysql_exceptions.ProgrammingError as (errno, errmsg):
                QMessageBox.critical(QApplication.activeWindow(), "Query result", errmsg)

# -*- coding: utf-8 -*-

import os
import time
import select
import paramiko
import socket
import MySQLdb
import SocketServer

from threading import Thread
from PyQt4.QtCore import QThread, pyqtSignal
from PyQt4.QtGui import QMessageBox, QApplication
from DBUtils.PersistentDB import PersistentDB
from _mysql_exceptions import Error as MySQLError

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
        except Exception:
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


class QueryThread(QThread):
    query_success = pyqtSignal(object)
    query_error = pyqtSignal(int, str)
    query_terminated = pyqtSignal(object)

    def __init__(self, connection, query, query_params=None, db=None):
        QThread.__init__(self)
        self.connection = connection
        self.query = query
        self.query_params = query_params
        self.db = db
        self.running = False
        self.daemon = True
        self.elapsed_time = -1

    def run(self):
        if self.db:
            self.connection.setDatabase(self.db)
        self.cursor = self.connection.cursor()
        self.pid = self.connection.pid()
        self.elapsed_time = -1

        try:
            self.running = True
            elapsed = time.time()
            self.dbworker()
            elapsed = time.time() - elapsed

        except MySQLError as (errno, errmsg):
            self.query_error.emit(errno, errmsg)

        else:
            self.elapsed_time = elapsed
            self.query_success.emit(self)

        finally:
            self.running = False
            self.query_terminated.emit(self)

    def dbworker(self):
        self.cursor.execute(self.query, self.query_params)
        self.result = self.cursor.fetchall()

    def kill(self):
        if self.running:
            self.connection.kill(self.pid)


class SQLServerConnection(object):
    tunnel = None
    dbpool = None

    def __init__(self, username=None, password="", host="localhost", port=3306, compression=False, use_tunnel=False, tunnel_username=None, tunnel_password=None, tunnel_port=22):
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
        self.compression = compression
        self.use_tunnel = use_tunnel

        if use_tunnel and tunnel_username is None:
            try:
                tunnel_username = os.getlogin()
            except:
                tunnel_username = ""

        self.tunnel_username = tunnel_username
        self.tunnel_password = tunnel_password
        self.tunnel_port = tunnel_port

        self.async_queries = []

    def iterdb(self, cursor, arraysize=1000):
        while True:
            results = cursor.fetchmany(arraysize)
            if not results:
                break
            for result in results:
                yield result

    def connection(self):
        if not self.isOpen():
            self.open()
        return self.dbpool.connection()

    def cursor(self, *args, **kwargs):
        return self.connection().cursor(*args, **kwargs)

    def iterall(self, query, query_params=None, cursor=None):
        if not cursor:
            cursor = self.cursor()
        cursor.execute(query, query_params)
        return self.iterdb(cursor)

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
                self.tunnel = TunnelThread(username=self.tunnel_username, password=self.tunnel_password, ssh_server=self.host, ssh_port=self.tunnel_port, remote_port=self.port)
                self.tunnel.start()
                host = "127.0.0.1"
                port = self.tunnel.local_port
            else:
                host = self.host
                port = self.port
            self.dbpool = PersistentDB(creator=MySQLdb, host=host, port=port, user=self.username, passwd=self.password, charset="utf8", use_unicode=True, compress=self.compression, setsession=['SET AUTOCOMMIT = 1'])
            # test connection
            self.cursor().execute("SELECT 1")
        except (socket.error, MySQLError) as e:
            self.close()
            raise e

    def pid(self):
        cur = self.cursor()
        cur.execute('SELECT CONNECTION_ID()')
        return cur.fetchall()[0][0]

    def kill(self, pid):
        return self.connection()._con.kill(pid)

    def asyncQuery(self, query, query_params=None, db=None, callback=None, callback_error=None, callback_terminated=None):
        t = QueryThread(self, query, query_params, db)
        if callback:
            t.query_success.connect(callback)
        if callback_error:
            t.query_error.connect(callback_error)
        if callback_terminated:
            t.query_terminated.connect(callback_terminated)
        t.start()
        self.async_queries.append(t)
        return t

    def close(self):
        for query in self.async_queries:
            query.kill()
        self.async_queries = []

        if self.tunnel is not None:
            self.tunnel.join()
            del self.tunnel
            self.tunnel = None

        self.dbpool = None

    def reconnect(self):
        self.close()
        self.open()

    def quoteIdentifier(self, identifier):
        return "`" + identifier.replace("`", "``") + "`"

    def escapeString(self, value):
        return self.connection()._con.escape_string(value)

    def quotedQuery(self, query, values):
        db = self.connection()._con
        return query % tuple([db.literal(item) for item in values])

    def confirmQuery(self, sql):
        if QMessageBox.question(QApplication.activeWindow(), "Query confirmation request", "%s\nAre you sure?" % sql, QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            db = self.connection().cursor()
            try:
                db.execute(sql)
            except MySQLError as (errno, errmsg):
                QMessageBox.critical(QApplication.activeWindow(), "Query result", errmsg)

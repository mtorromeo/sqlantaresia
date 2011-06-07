import paramiko, select, SocketServer
from threading import Thread
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

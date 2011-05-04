import paramiko, select, SocketServer
from threading import Thread

class ForwardServer(SocketServer.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True

class Handler(SocketServer.BaseRequestHandler):
    def handle(self):
        try:
            chan = self.ssh_transport.open_channel('direct-tcpip', (self.chain_host, self.chain_port), self.request.getpeername())
        except Exception, e:
            #verbose('Incoming request to %s:%d failed: %s' % (self.chain_host, self.chain_port, repr(e)))
            return

        if chan is None:
            #verbose('Incoming request to %s:%d was rejected by the SSH server.' % (self.chain_host, self.chain_port))
            return

        #verbose('Connected! Tunnel open %r -> %r -> %r' % (self.request.getpeername(), chan.getpeername(), (self.chain_host, self.chain_port)))
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
        #verbose('Tunnel closed from %r' % (self.request.getpeername(),))

def forward_tunnel(local_port, remote_host, remote_port, transport):
    # this is a little convoluted, but lets me configure things for the Handler
    # object. (SocketServer doesn't give Handlers any way to access the outer
    # server normally.)
    class SubHander(Handler):
        chain_host = remote_host
        chain_port = remote_port
        ssh_transport = transport
    ForwardServer(('', local_port), SubHander).serve_forever()

class SSHForwarder(Thread):
    def __init__(self, ssh_server, local_port, ssh_port=22, remote_host="localhost", remote_port=None, username=None, password=None):
        Thread.__init__(self)
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

        class SubHander(Handler):
            chain_host = remote_host
            chain_port = remote_port
            ssh_transport = transport
        self.ffwd_server = ForwardServer(('', self.local_port), SubHander)

    def run(self):
        self.ffwd_server.serve_forever()

    def join(self):
        if self.ffwd_server is not None:
            self.ffwd_server.shutdown()
        self.ssh_client.close()
        del self.ffwd_server
        del self.ssh_client
        Thread.join(self)

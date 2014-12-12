import socket

from pytest_django.live_server_helper import parse_addr
from django.test.testcases import LiveServerThread as LiveServerThreadBase
from django.db import connections
from tornado import ioloop

from keybar.server import get_server


class LiveServerThread(LiveServerThreadBase):
    ports = range(49152, 65535)

    def run(self):
        if self.connections_override:
            # Override this thread's database connections with the ones
            # provided by the main thread.
            for alias, conn in self.connections_override.items():
                connections[alias] = conn
        try:
            # Go through the list of possible ports, hoping that we can find
            # one that is free to use for the WSGI server.
            try:
                server = get_server(debug=False)
                for port in self.ports:
                    try:
                        server.listen(port, 'keybar.local')
                    except OSError as exc:
                        if port == 65535:
                            raise exc
            except socket.error as exc:
                raise exc
            else:
                self.port = port

            self.is_ready.set()
            self.loop = ioloop.IOLoop.instance()
            self.loop.start()
        except Exception as exc:
            self.terminate()
            self.error = exc
            self.is_ready.set()

    def terminate(self):
        if hasattr(self, 'loop'):
            # Stop the WSGI server
            self.loop.stop()


class LiveServer(object):
    def __init__(self, addr):
        host, possible_ports = parse_addr(addr)
        self.thread = LiveServerThread(host, possible_ports, None)
        self.thread.daemon = True
        self.thread.start()
        self.thread.is_ready.wait()

        if self.thread.error:
            raise self.thread.error

    def stop(self):
        """Stop the server"""
        terminate = getattr(self.thread, 'terminate', lambda: None)
        terminate()
        self.thread.join()

    @property
    def url(self):
        return 'https://{0}'.format(self.domain)

    @property
    def domain(self):
        return '{0}:{1}'.format(self.thread.host, self.thread.port)

    def __str__(self):
        return self.url

    def __add__(self, other):
        return str(self) + other

    def __repr__(self):
        return '<LiveServer listening at {0}>'.format(self.url)

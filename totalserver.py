from threading import Thread
import socket
import struct
import os
import os.path as op
import re
import sys
import hashlib
import mimetypes
import stat

class Server(Thread):

    def __init__(self, port, direc):
        Thread.__init__(self)
        self.port = port
        self.host = ""

        self.mypath = "./" + direc + "/"
        self.commandlist = []

        self.listedfiles = [f for f in os.listdir(self.mypath) if op.isfile(op.join(self.mypath, f))]

    def index(self, flag, args):
        table = [['Name', 'Size', 'Timestamp', 'Type']]

        self.listedfiles = [f for f in os.listdir(self.mypath) if op.isfile(op.join(self.mypath, f))]

        for f in self.listedfiles:
            fpath = op.join(self.mypath, f)
            time = op.getmtime(fpath)

            if flag == "shortlist":
                if time < float(args[0]) or time > float(args[1]):
                    continue
            elif flag == "regex":
                if not re.fullmatch('.*' + args[0], f):
                    continue

            ftype = mimetypes.guess_type(fpath)[0]
            if not ftype:
                ftype = "text/plain"
            table.append([f, str(op.getsize(fpath)), str(time), ftype])

        return table

    def dohash(self, file):
        fpath = op.join(self.mypath, file)
        hashedval = hashlib.md5(open(fpath,'rb').read()).hexdigest()
        return [file, hashedval, str(op.getmtime(fpath))]

    def dohash2(self, file):
        fpath = op.join(self.mypath, file)
        hashedval = hashlib.md5(open(fpath,'rb').read()).hexdigest()
        table = [['Name', 'Filesize', 'Timestamp', 'Hash']]
        table.append([file, str(op.getmtime(fpath)), str(op.getsize(fpath)), hashedval])
        return table

    def run(self):
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.host, self.port))
        sudp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sudp.bind((self.host, self.port))

        s.listen(5)

        while True:
            conn, address = s.accept()
            data = conn.recv(struct.calcsize('cI'))
            command, argsize = struct.unpack('cI', data)
            command = command.decode()

            if command == "i":
                myargs = conn.recv(argsize)
                myargs = myargs.decode()
                myargs = myargs.split(' ')
                flag = myargs[0]
                myargs = myargs[1:]

                output = self.index(flag, myargs)
                result = ""
                for out in output:
                    for i in out:
                        result += i
                        result += "   "
                    result += "\n"

                conn.send(struct.pack('I',sys.getsizeof(result)))
                conn.send(result.encode())

            elif command == "h":
                myargs = conn.recv(argsize)
                myargs = myargs.decode()
                myargs = myargs.split(' ')
                flag = myargs[0]
                myargs = myargs[1:]
                # print(flag)
                # print(myargs)

                self.listedfiles = [f for f in os.listdir(self.mypath) if op.isfile(op.join(self.mypath, f))]
                output = []
                output.append(["Filename", "Checksum", "Last mod time"])
                if flag == "checkall":
                    for f in self.listedfiles:
                        # print("hashing for ", f)
                        output.append(self.dohash(f))
                else:
                    output.append(self.dohash(myargs[0]))

                result = ""
                for out in output:
                    for i in out:
                        result += str(i)
                        result += "   "
                    result += "\n"

                conn.send(struct.pack('I',sys.getsizeof(result)))
                conn.send(result.encode())

            elif command == "d":

                myargs = conn.recv(argsize)
                myargs = myargs.decode()
                myargs = myargs.split(' ')
                flag = myargs[0]
                # print("myargs are:", myargs)
                if flag == "TCP":
                    arg = myargs[1]
                    #read and send file to client
                    fpath = self.mypath + arg
                    f = open(fpath, 'rb')

                    size = os.path.getsize(fpath)
                    size = struct.pack('i', size)
                    conn.send(size)

                    l = f.read(1024)
                    while (l):
                       conn.send(l)
                       l = f.read(1024)
                    f.close()

                    output = self.dohash2(arg)
                    result = ""
                    for out in output:
                        for i in out:
                            result += str(i)
                            result += "   "
                        result += "\n"


                    #maintain permission
                    st = os.stat(fpath)
                    st = st.st_mode
                    conn.send(struct.pack('I',st))

                    conn.send(struct.pack('I',sys.getsizeof(result)))
                    conn.send(result.encode())

                elif flag == "UDP":
                    arg = myargs[1]
                    #read and send file to client
                    fpath = self.mypath + arg
                    f = open(fpath, 'rb')

                    size = os.path.getsize(fpath)
                    size = struct.pack('i', size)
                    # print("11")
                    conn.send(size)
                    # print("22")
                    data, add = sudp.recvfrom(2048)
                    # print("33")
                    l = f.read(1024)
                    while (l):
                       sudp.sendto(l, add)
                       l = f.read(1024)
                    f.close()

                    output = self.dohash2(arg)
                    result = ""
                    for out in output:
                        for i in out:
                            result += str(i)
                            result += "   "
                        result += "\n"

                    st = os.stat(fpath)
                    st = st.st_mode
                    sudp.sendto(struct.pack('I',st), add)

                    sudp.sendto(struct.pack('I',sys.getsizeof(result)), add)
                    sudp.sendto(result.encode(), add)

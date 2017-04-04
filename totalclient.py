from threading import Thread
import socket
import struct
import os
import os.path as op
import re
import sys
import hashlib
import mimetypes
import time
from totalserver import Server

class Client(Thread):

    def __init__(self, port, direc):
        Thread.__init__(self)
        self.port = port
        self.host = ""
        self.path = "./" + direc + "/"
        self.commandlist = []
        self.lastupdatetime = time.time()

    def doindex(self, command):
        s = socket.socket()
        s.connect((self.host, self.port))
        #sendcommand
        myargs = command[1:]
        s.send(struct.pack('cI', 'i'.encode(), sys.getsizeof(myargs)))

        myargs = ' '.join(myargs)
        s.send(myargs.encode())

        size2 = s.recv(4)
        size2, = struct.unpack('I', size2)
        output = s.recv(size2)
        output = output.decode()
        s.close()
        return output

    def dohash(self, command):
        s = socket.socket()
        s.connect((self.host, self.port))
        #sendcommand
        myargs = command[1:]
        s.send(struct.pack('cI', 'h'.encode(), sys.getsizeof(myargs)))

        myargs = ' '.join(myargs)
        s.send(myargs.encode())

        size2 = s.recv(4)
        size2, = struct.unpack('I', size2)
        output = s.recv(size2)
        output = output.decode()
        s.close()
        return output

    def dodownload(self, command):

        s = socket.socket()
        s.connect((self.host, self.port))
        #sendcommand
        myargs = command[1:]
        s.send(struct.pack('cI', 'd'.encode(), sys.getsizeof(myargs)))

        myargs = ' '.join(myargs)
        s.send(myargs.encode())
        #downloadfile
        fpath = self.path + command[2]

        if command[1] == "TCP":
            f = open(fpath, "wb")
            # data = s.recv(40000)
            # f.write(data)

            size = s.recv(4)
            size, = struct.unpack('i', size)
            recvtn = 0
            while True:
                # print('receiving data...')
                data = s.recv(1024)
                # print('data=%s', (data))
                if not data:
                    break
                # write data to a file
                f.write(data)
                recvtn += 1024
                if recvtn > size:
                    break
            f.close()

            perm= s.recv(4)
            perm, = struct.unpack('I', perm)
            os.chmod(fpath, perm)

            size2 = s.recv(4)
            size2, = struct.unpack('I', size2)
            dat = s.recv(size2)
            s.close()
            return dat.decode()

        elif command[1] == "UDP":
            size = s.recv(4)
            size, = struct.unpack('I', size)
            s.close()
            # print("1")
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((self.host, self.port))
            # s.send('something'.encode())
            # print("2")
            s.send(fpath.encode())
            # print("3")

            f = open(fpath, "wb")

            # print("5")

            recvtn = 0
            while True:
                # print('receiving data...')
                data = s.recv(1024)
                # print('data=%s', (data))
                if not data:
                    break
                # write data to a file
                f.write(data)
                recvtn += 1024
                if recvtn > size:
                    break
            f.close()

            # print("6")

            perm= s.recv(4)
            perm, = struct.unpack('I', perm)
            os.chmod(fpath, perm)

            size2 = s.recv(4)
            size2, = struct.unpack('I', size2)
            dat = s.recv(size2)
            s.close()
            return dat.decode()

    def run(self):
        while True:

            nowtime = time.time()
            if nowtime - self.lastupdatetime > 5:
                self.lastupdatetime = nowtime
                print("sync start")

                filelist = [f for f in os.listdir(self.path) if op.isfile(op.join(self.path, f))]

                # print(filelist)
                output = self.dohash(["hash", "checkall"])

                output = output.split("\n")
                del output[-1]
                output = [i.split("   ") for i in output]
                output = output[1:]

                # print(output)

                for row in output:
                    curfile = row[0]
                    # print("doing for ", curfile)
                    if curfile in filelist:
                        hashedval = hashlib.md5(open(self.path + curfile,'rb').read()).hexdigest()
                        if hashedval != row[1]:
                            print(self.dodownload(["download", "TCP", curfile]))
                    else:
                        print(self.dodownload(["download", "TCP", curfile]))
                print("sync done")


            command = input("prompt>>")
            self.commandlist.append(command)
            command = command.split(' ')

            if command[0] == "index":
                output = self.doindex(command)
                print(output)

            elif command[0] == "hash":
                output = self.dohash(command)
                print(output)

            elif command[0] == "download":
                output = self.dodownload(command)
                print(output)


if __name__ == '__main__':

    info = input("val, my file directory:")
    info = info.split(" ")
    x = int(info[0])
    if x == 1:
        otherport = 60001
        myport = 60000
    else:
        otherport = 60000
        myport = 60001
    mydir = info[1]

    myThreadOb1 = Client(otherport, mydir)
    myThreadOb1.setName('Client')

    myThreadOb2 = Server(myport, mydir)
    myThreadOb2.setName('Server')

   # Start running the threads!
    myThreadOb1.start()
    myThreadOb2.start()

   # Wait for the threads to finish...
    myThreadOb1.join()
    myThreadOb2.join()

    print('Main Terminating...')

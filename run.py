import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
s.bind(('', 9090))

try:
    while True:
        data, addr = s.recvfrom(1024)
        print("my-ip:%s" % socket.gethostbyname(socket.gethostname()))
        print(data)

except:
    s.close()
    print("exit")

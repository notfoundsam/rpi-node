import socket, sys, time
from .service import RpiNode, DiscoverCatcher
from .models import Rc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import logger

class App():
    host = None
    port = 32001
    ads = {}
    db_uri = None

    def __init__(self):
        self.catcher = DiscoverCatcher()
        self.host_name = socket.gethostname()

    def createSession(self):
        engine = create_engine(self.db_uri)
        Session = sessionmaker(bind=engine)
        session = Session()
        return session

    def run(self, debug = False):
        self.debug = debug
        self.interrupt = False
        self.createDbUri()

        while True:
            self.host = self.catcher.catchIP()
            
            if self.host is not None:
                self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

                try:
                    self.sock.connect((self.host, self.port))
                    logger.info('Handshake with the server')
                    request = "%s:%s" % (socket.gethostname(), 'handshake')
                    self.sock.send(request.encode())

                    # Wait for handshake
                    data = self.sock.recv(1024)

                    if data:
                        udata = data.decode()

                        if udata != 'accept':
                            logger.warning('Did not accept')
                            self.sock.close()
                            continue
                        else:
                            logger.info('Accepted')
                    else:
                        logger.warning('Empty response')
                        self.sock.close()
                        continue
                
                except Exception as e:
                    logger.error('The server closed the connection')
                    for arduino in self.ads:
                        self.ads[arduino].close()
                    self.sock.close()
                    continue

                node = RpiNode(self)
                node.run()

                if self.interrupt == True:
                    for arduino in self.ads:
                        self.ads[arduino].close()
                    time.sleep(2)
                    self.sock.close()
                    break

    def createDbUri(self):
        self.db_uri = 'mysql+mysqlconnector://%s:%s@%s:%s/%s' % (self.DB_USER,self.DB_PASS,self.DB_HOST,self.DB_PORT,self.DB_NAME)

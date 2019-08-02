import socket, sys, time, logging
from .service import EventParser, DiscoverCatcher
from .models import Rc, Node
from .drivers import ArduinoDriver
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class App():
    host = None
    port = 32001
    ads = {}
    db_session = None

    def __init__(self):
        self.catcher = DiscoverCatcher()
        self.host_name = socket.gethostname()

    def run(self, debug = False):
        logging.basicConfig(
            format='%(asctime)s - [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            level= logging.DEBUG if debug else logging.ERROR,
            handlers=[
                logging.FileHandler("app.log"),
                logging.StreamHandler()
            ])

        self.debug = debug
        self.interrupt = False
        self.status = 'stopped'
        
        logging.info('New db session')
        engine = create_engine(self.createDbUri(), echo=self.debug, pool_recycle=3600, pool_pre_ping=True)
        self.db_session = sessionmaker(bind=engine)

        while True:
            self.host = self.catcher.catchIP()
            
            if self.host is not None:
                time.sleep(1)
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                try:
                    self.sock.connect((self.host, self.port))
                    logging.info('Handshake with the server')
                    request = "%s:%s\n" % (socket.gethostname(), 'handshake')
                    self.sock.send(request.encode())

                    # Wait for handshake
                    data = self.sock.recv(1024)

                    if data:
                        udata = data.decode()

                        if udata != 'accept':
                            logging.warning('Did not accept')
                            self.sock.close()
                            continue
                        else:
                            logging.info('Accepted')
                    else:
                        logging.warning('Empty response')
                        self.sock.close()
                        continue
                
                except Exception as e:
                    logging.exception('The server closed the connection. Try again')
                    self.sock.close()
                    self.ads = {}
                    time.sleep(2)
                    continue

                self.runRpiNode()

                if self.interrupt == True:
                    break

    def runRpiNode(self):
        logging.info('Configure arduinos')
        logging.info('Debug: %r' % self.debug)
        
        if self.createArduinoDrivers() == False:
            logging.error('The node not found in DB')
            self.sock.close()
            return

        try:
            logging.info('Strat listening')
            message_buff = ''
            while True:
                data = self.sock.recv(1)
                
                if data:
                    udata = data.decode()

                    if udata != "\n":
                        message_buff += udata
                        continue

                    parser = EventParser(self, message_buff)
                    parser.run()
                    message_buff = ''
                else:
                    logging.warning('Connection closed, empty response')
                    break

        except KeyboardInterrupt:
            self.interrupt = True
            logging.exception('Keyboard Interrupt')

        except Exception as e:
            self.interrupt = True
            logging.exception('Main thread error')

        for arduino in self.ads:
            self.ads[arduino].close()
        
        self.ads = {}
        self.sock.close()
        time.sleep(2)
    
    def createArduinoDrivers(self):
        session = self.db_session()

        node = session.query(Node).filter_by(host_name=self.host_name).first()

        if node is None:
            return False

        arduinos = node.arduinos.all()
        session.close()

        if arduinos is not None:
            for arduino in arduinos:
                logging.info(str(arduino))
                ad = ArduinoDriver(self)
                ad.connect(arduino.usb)
                self.ads[arduino.usb] = ad

        self.status = 'started'

        return True

    def createDbUri(self):
        return 'mysql+mysqlconnector://%s:%s@%s:%s/%s' % (self.DB_USER,self.DB_PASS,self.DB_HOST,self.DB_PORT,self.DB_NAME)

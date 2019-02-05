import threading, socket, sys, json
from .models import Node, Arduino, Button, Radio
from .drivers import ArduinoDriver, ArduinoQueueItem
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import logger, ir_reader

class DiscoverCatcher:

    def catchIP(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(('', 32000))

        logger.info('Discovering...')

        data, addr = sock.recvfrom(1024)
        sock.close()
        
        host = addr[0]

        # Check if IPv4 is valid
        try:
            socket.inet_aton(host)
            return host

        except socket.error:
            return None

class RpiNode:

    def __init__(self, app):
        self.app = app
        self.interrupt = False
        
    def run(self):
        logger.info('Configure arduinos')
        logger.info('Debug: %r' % self.app.debug)
        
        if self.createArduinoDrivers() == False:
            logger.error('The node not found in DB')
            self.app.sock.close()
            return

        try:
            logger.info('Strat listening')
            while True:
                data = self.app.sock.recv(1024)
                
                if data:
                    udata = data.decode()
                    parser = EventParser(udata, self.app)
                    parser.start()
                else:
                    logger.warning('Connection closed, empty response')
                    for arduino in self.app.ads:
                        self.app.ads[arduino].close()
                    self.app.sock.close()
                    break

        except KeyboardInterrupt:
            self.app.interrupt = True

        except Exception as e:
            for arduino in self.app.ads:
                self.app.ads[arduino].close()
                                
            self.app.sock.close()

    def createArduinoDrivers(self):
        session = self.app.createSession()
        node = session.query(Node).filter_by(host_name=self.app.host_name).first()

        if node is None:
            session.close()
            return False

        arduinos = node.arduinos.all()
        session.close()

        if arduinos is not None:
            for arduino in arduinos:
                logger.info(str(arduino))
                ad = ArduinoDriver(self.app, arduino.mode)
                ad.connect(arduino.usb)
                self.app.ads[arduino.usb] = ad

        return True

class SocketEvent:

    def __init__(self):
        self.user_id = None
        self.button_id = None
        self.sock = None
        self.button = None
        self.radio = None

class EventParser(threading.Thread):

    def __init__(self, udata, app):
        threading.Thread.__init__(self)
        self.udata = udata
        self.app = app

    def run(self):
        data = json.loads(self.udata)

        if 'event' in data and data['event'] == 'pushButton':
            self.pushButton(data)
        elif 'event' in data and data['event'] == 'catchIr':
            logger.info(data['host_name'])
            ir_signal = ir_reader.read_signal()
            response = json.dumps({'type': 'ir', 'result': 'success', 'ir_signal': ir_signal})
            self.app.sock.send(response.encode())

    def pushButton(self, data):
        session = self.app.createSession()
        button, arduino, radio = session.query(Button, Arduino, Radio).filter(Button.id == data['button_id']).first()
        session.close()

        # Debug
        # logger.info(str(button))
        # logger.info(str(button.execute))

        if arduino is not None and radio is not None:
            if arduino.usb in self.app.ads:
                props = {
                    'button_type': button.type,
                    'button_exec': button.execute,
                    'radio_pipe': radio.pipe,
                    'user_id': data['user_id']
                }

                item = ArduinoQueueItem(props, 1)
                self.app.ads[arduino.usb].queue.putItem(item)
        else:
            logger.warning('Bad settings')

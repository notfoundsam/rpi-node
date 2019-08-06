import threading, socket, sys, json, time, logging
from .models import Node, Arduino, Button, Radio
from .drivers import ArduinoQueueItem
from app import helper

class DiscoverCatcher:

    def catchIP(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(('', 32000))

        logging.info('Discovering...')

        data, addr = sock.recvfrom(1024)
        sock.close()
        
        host = addr[0]

        # Check if IPv4 is valid
        try:
            socket.inet_aton(host)
            return host

        except socket.error:
            return None

class EventParser():

    def __init__(self, app, udata):
        # threading.Thread.__init__(self)
        self.app = app
        self.udata = udata

    def run(self):
        try:
            data = json.loads(self.udata)
        except ValueError as e:
            logging.debug(self.udata)
            logging.exception('Broken json from socket')
            return

        # Stop listenning Arduinos
        if self.app.status == 'started' and 'event' in data and data['event'] == 'stop':
            logging.info('Try to stop service')
            self.app.status == 'stopping'

            for arduino in self.app.ads:
                self.app.ads[arduino].close()

            time.sleep(2)
            self.app.status = 'stopped'
            response = "%s\n" % json.dumps({'type': 'system', 'result': 'success', 'service': 'stopped'})
            self.app.sock.send(response.encode())

        # Start listenning Arduinos
        elif self.app.status == 'stopped' and 'event' in data and data['event'] == 'start':
            logging.info('Try to start service')
            if self.app.createArduinoDrivers() == False:
                logging.error('The node not found in DB')
                self.app.sock.close()

            response = "%s\n" % json.dumps({'type': 'system', 'result': 'success', 'service': 'started'})
            self.app.sock.send(response.encode())

        # Restart listenning Arduinos
        elif self.app.status == 'started' and 'event' in data and data['event'] == 'restart':
            logging.info('Try to restart service')
            self.app.status == 'restarting'

            for arduino in self.app.ads:
                self.app.ads[arduino].close()

            time.sleep(2)

            if self.app.createArduinoDrivers() == False:
                logging.error('The node not found in DB')
                self.app.sock.close()

            response = "%s\n" % json.dumps({'type': 'system', 'result': 'success', 'service': 'restarted'})
            self.app.sock.send(response.encode())
            
        elif self.app.status == 'started' and 'event' in data and data['event'] == 'pushButton':
            self.pushButton(data)

        elif self.app.status == 'started' and 'event' in data and data['event'] == 'catchIr':
            logging.info(data['host_name'])
            ir_signal = helper.read_signal()
            ir_signal = helper.compress_signal(ir_signal)
            response = "%s\n" % json.dumps({'type': 'ir', 'result': 'success', 'ir_signal': ir_signal})
            self.app.sock.send(response.encode())

    def pushButton(self, event):
        session = self.app.db_session()
        button = session.query(Button).get(event['button_id'])
        radio = session.query(Radio).get(button.radio_id)
        arduino = radio.arduino
        # button, arduino, radio = session.query(Radio).filter(Button.id == data['button_id']).first()
        session.close()

        # Debug
        # logging.info(str(button))
        # logging.info(str(button.execute))

        if arduino is not None and radio is not None:
            if arduino.usb in self.app.ads:
                # props = {
                #     'radio_pipe': radio.pipe,
                #     'radio_type': radio.type,
                #     'message': button.message,
                #     'event': event
                # }

                # pre_data.append('%si' % chr(self.props['radio_pipe']))
                full_message = '%s%s\n' % (chr(int(radio.pipe)), button.message)
                
                if radio.on_request == 1:
                    item = ArduinoQueueItem(full_message, 1)
                    item.setExpiration(radio.expired_after)
                    item.setRadioPipe(radio.pipe)
                    item.setOriginEvent(event)
                    self.app.ads[arduino.usb].addToRequestBuffer(item)
                else:
                    item = ArduinoQueueItem(full_message, 2)
                    item.setOriginEvent(event)
                    self.app.ads[arduino.usb].addToQueue(item)
        else:
            logging.warning('Bad settings')

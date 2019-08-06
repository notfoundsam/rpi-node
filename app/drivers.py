import threading, queue, sys, logging
import serial
import time, random, json

class ArduinoDriver():
    ser = None
    ser_timeout = 0.5
    ser_baudrate = 500000
    queue = None
    items_buffer = []

    def __init__(self, app):
        self.app = app
        self.writer = SerialWriter()

    def connect(self, port):
        if self.app.emulation == True:
            self.ser = SerialEmulator(self.writer)
        else:
            self.ser = serial.Serial()
            
        self.ser.baudrate = self.ser_baudrate
        self.ser.port = '/dev/%s' % port
        self.ser.timeout = self.ser_timeout
        self.ser.open()

        # Only after write sketch into Arduino
        time.sleep(0.5)
        self.ser.flushInput()
        self.ser.flushOutput()
        self.pm = PackageManager(self, self.app)
        self.aq = ArduinoQueue(self.app, self.ser, self.pm)
        self.pm.setDaemon(True)
        self.aq.setDaemon(True)
        self.pm.start()
        self.aq.start()

    def close(self):
        logging.info('Close Driver %s' % self.ser.port)
        self.writer.is_running = False
        self.aq.is_running = False
        self.pm.is_running = False

    def addToQueue(self, item):
        self.aq.workQueue.put(item)
    
    def addToRequestBuffer(self, item):
        order = 1

        for i in self.items_buffer:
            if i.getRadioPipe() == item.getRadioPipe():
                order += 1

        item.setOrder(order)
        self.items_buffer.append(item)
        logging.info('Add with order: %d pipe: %s' % (order, item.getRadioPipe()))

    def getFromRequestBuffer(self, pipe):
        first = None
        expired = []

        for i in self.items_buffer:
            if i.isExpired():
                expired.append(self.items_buffer.index(i))
                continue

            if i.getRadioPipe() == pipe:
                if first == None:
                    first = i
                else:
                    if i.getOrder() < first.getOrder():
                        first = i

        if first is not None:
            index = self.items_buffer.index(first)
            first = self.items_buffer.pop(index)

        for ex in expired:
            self.items_buffer.pop(ex)

        return first
    
    def checkRequest(self, package):
        item = self.getFromRequestBuffer(package.getRadioPipe())
        
        if item == None:
            full_message = '%scempty\n' % package.getRadioPipe()
            item = ArduinoQueueItem(full_message, 1)

        self.addToQueue(item)

class PackageManager(threading.Thread):

    def __init__(self, ad, app):
        threading.Thread.__init__(self)
        self.is_running = True
        self.ad = ad
        self.app = app
        self.packageQueue = queue.Queue()
        self.buffer = {}

    def run(self):
        while True:
            # Terminate the process
            if self.is_running == False:
                logging.info('Stop PackageManager')
                break
            
            if not self.packageQueue.empty():
                sp = self.packageQueue.get()
                pipe = sp.getRadioPipe()

                if pipe not in self.buffer:
                    if sp.getPackageNumber() == 0:
                        self.buffer[pipe] = Package(sp)
                else:
                    self.buffer[pipe].append(sp)

                self.checkPackages()
            else:
                self.checkPackages()
                time.sleep(0.01)

    def addPackage(self, sp):
        self.packageQueue.put(sp)

    def checkPackages(self):
        for_del = []

        for package in self.buffer:
            if self.buffer[package].complete:
                if self.buffer[package].getType() == 'ev':
                    logging.info('ev')
                    se = SocketEvent(self.app, self.buffer[package])
                    se.run()
                elif self.buffer[package].getType() == 'rq':
                    logging.info('rq')
                    self.ad.checkRequest(self.buffer[package])
                
                for_del.append(package)
                    
            elif self.buffer[package].expired():
                for_del.append(package)
        
        for p in for_del:
            del self.buffer[p]

class ArduinoQueue(threading.Thread):

    def __init__(self, app, ser, pm):
        threading.Thread.__init__(self)
        self.is_running = True
        self.app = app
        self.ser = ser
        self.pm = pm
        self.workQueue = queue.Queue()
        # self.workQueue = queue.PriorityQueue()

    def run(self):
        while True:
            # Terminate the process
            if self.is_running == False:
                logging.info('Stop ArduinoQueue')
                break

            if self.app.status != 'started':
                time.sleep(1)
                continue

            if not self.workQueue.empty():
                queue_item = self.workQueue.get()
                queue_item.run(self.app, self.pm, self.ser)
            else:
                if self.ser.in_waiting > 0:
                    # logging.info('AAAA')
                    response = self.ser.readline()
                    response = response.decode('ascii', 'replace')
                    self.pm.addPackage(SerialPackage(response, self.ser.port))
                else:
                    # logging.info('BBB')
                    # time.sleep(1)
                    time.sleep(0.05)

class ArduinoQueueItem():

    def __init__(self, message, priority):
        self.buffer   = 64
        self.execute  = ''
        self.message  = message
        self.priority = priority
        self.expired_at = None
        self.radio_id = None
        self.order = None
        self.origin_event = None

    def setExpiration(self, expire_after):
        self.expired_at = time.time() + expire_after

    def setRadioPipe(self, radio_id):
        self.radio_id = chr(int(radio_id))

    def setOrder(self, order):
        self.order = order
    
    def setOriginEvent(self, origin_event):
        self.origin_event = origin_event

    def getRadioPipe(self):
        return self.radio_id

    def getOrder(self):
        return self.order

    def isExpired(self):
        return (self.expired_at < time.time())

    def run(self, app, pm, ser):
        partial_signal = [self.message[i:i+self.buffer] for i in range(0, len(self.message), self.buffer)]
        
        for part in partial_signal:
            logging.info(part)
            b_arr = bytearray(part.encode())
            ser.write(b_arr)
            ser.flush()

            error = False
            start_at = time.time()

            while True:
                response = ser.readline()
                response = response.decode('ascii', 'replace')

                if int(time.time() - start_at) > 0.5:
                    logging.warning('waiting timeout')
                    error = 'waiting timeout'
                    break
                elif response.strip() == '':
                    logging.warning('empty response')
                elif response.strip() == ':next:':
                    break
                elif response.strip() == ':overflow:':
                    logging.warning('overflow')
                    error = 'overflow'
                    break
                elif response.strip() == ':timeout:':
                    logging.warning('timeout')
                    error = 'timeout'
                    break
                elif response.strip() == ':ack:':
                    continue
                elif response.strip() == ':fail:':
                    logging.info('fail')
                    error = 'fail'
                    break
                elif response.strip() == ':success:':
                    logging.info('success')
                    response = "%s\n" % json.dumps({'type': 'response', 'result': 'success', 'origin_event': self.origin_event})
                    app.sock.send(response.encode())
                    break
                else:
                    pm.addPackage(SerialPackage(response, ser.port))
                    logging.info(response.strip())

            if error != False:
                response = "%s\n" % json.dumps({'type': 'response', 'result': 'error', 'error': error, 'origin_event': self.origin_event})
                app.sock.send(response.encode())
                break

class SerialPackage():

    def __init__(self, package, serial_port):
        self.serial_port = serial_port
        self.package = package.strip()
        self.is_last = self.package[-1].encode() == b"\x17"

    def getPackage(self):
        return self.package
    
    def getRadioPipe(self):
        return self.package[:1]

    def getPackageNumber(self):
        if self.package[1:2].isdigit():
            return int(self.package[1:2])
        else:
            logging.debug('broken package: %s' % self.package)
            logging.debug('package length: %r' % len(self.package))
            return None

    def getPayload(self):
        return self.package[2:]

    def getSerialPort(self):
        return self.serial_port

class Package():

    def __init__(self, sp):
        self.complete = False
        self.updated_at = time.time()
        self.radio_pipe = sp.getRadioPipe()
        self.package_number = 1
        self.payload = sp.getPayload()
        self.serial_port = sp.getSerialPort()
        self.type = None
        self.message = ''

        self.isComplete(sp)

    def expired(self):
        ex = (time.time() - self.updated_at) > 0.1
        return ex

    def append(self, sp):
        self.updated_at = time.time()

        if sp.getPackageNumber() == self.package_number:
            self.package_number += 1
            self.payload += sp.getPayload()
            self.isComplete(sp)
        else:
            logging.warning('The same package: %s' % sp.getPackage())

    def getPayload(self):
        return self.payload[:-1]

    def getMessage(self):
        return self.message

    def getSerialPort(self):
        return self.serial_port

    def getRadioPipe(self):
        return self.radio_pipe

    def getRadioPipeOrd(self):
        return ord(self.radio_pipe)

    def getType(self):
        return self.type

    def isComplete(self, sp):
        if sp.is_last:
            self.complete = True

            try:
                message = dict(s.split(' ') for s in self.getPayload().split(','))
            except Exception as e:
                logging.error('Incorrect message: %s' % self.getPayload())
                return

            if 'tp' in message and message['tp'] in ['ev', 'rs', 'rq']:
                self.type = message['tp']
                del message['tp']
                self.message = message

class SocketEvent():

    def __init__(self, app, package):
        # threading.Thread.__init__(self)
        self.app = app
        self.package = package

    def run(self):
        response = "%s\n" % json.dumps({
            'type': 'event',
            'result': 'success',
            'port': self.package.getSerialPort(),
            'message': self.package.getMessage(),
            'radio_pipe': self.package.getRadioPipeOrd()
        })

        logging.info(response)
        self.app.sock.send(response.encode())

class SerialWriter(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.event_timer = time.time()
        self.request_timer = time.time()
        self.is_running = True
        self.emulator = None

    def setEmulator(self, emulator):
        self.emulator = emulator

    def run(self):
        logging.info('Writer started on %s' % self.emulator.port)
        while True:
            # Terminate the process
            if self.is_running == False:
                logging.info('Stop SerialWriter')
                break
            if self.event_timer + 5 < time.time():
                self.event_timer = time.time()
                self.emulator.addToBuffer(self.radioEvent())
                self.emulator.setInwating()
            if self.request_timer + 8 < time.time():
                self.request_timer = time.time()
                self.emulator.addToBuffer(self.radioRequest())
                self.emulator.setInwating()
            else:
                time.sleep(1)
    
    def radioEvent(self):
        temp  = random.uniform(18, 26)
        hum   = random.uniform(40, 65)
        press = random.uniform(1020.00, 1060.00)
        bat   = random.uniform(3.8, 4.2)
        pipe  = random.choice(['0', '1', '2'])

        output = '%s0tp ev,t %.2f,h %.2f,p %.2f,b %.2f\x17\n' % (pipe, temp, hum, press, bat)
        return output.encode()
    
    def radioRequest(self):
        # pipe  = random.choice(['0', '1', '2'])
        pipe = '2'

        output = '%s0tp rq\x17\n' % (pipe)
        return output.encode()

class SerialEmulator():

    def __init__(self, writer):
        self.writer = writer
        self.in_waiting = 0
        self.baudrate = 9600
        self.timeout = 0
        self.port = None
        
        self.buffering = False
        self.writing = False

        self.input_buffer = []

    def addToBuffer(self, item):
        self.input_buffer.append(item)
    
    def getFromBuffer(self):
        return self.input_buffer.pop()
    
    def setInwating(self):
        self.in_waiting = 1

    def open(self):
        logging.info('SERIAL %s: Opened' % self.port)
        self.writer.setEmulator(self)
        self.writer.setDaemon(True)
        self.writer.start()

    def flushInput(self):
        logging.info('SERIAL %s: flushInput' % self.port)

    def flushOutput(self):
        logging.info('SERIAL %s: flushOutput' % self.port)

    def flush(self):
        logging.info('SERIAL %s: flush' % self.port)

    def write(self, data):
        self.writing = True
        logging.info('SERIAL %s: Recieved bytearray' % self.port)
        logging.info(data.decode())

        if data[-1] == 10:
            self.buffering = False
        else:
            self.buffering = True

    def readline(self):
        if self.writing:
            if self.buffering == False:
                self.writing = False
                return ":success:\n".encode()
            else:
                return ":next:\n".encode()
        else:
            if len(self.input_buffer) > 0:
                i = self.getFromBuffer()
                if len(self.input_buffer) == 0:
                    self.in_waiting = 0

                return i
            else:
                time.sleep(1)
                return ''.encode()

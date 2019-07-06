import threading, queue, sys
import serial
import time, random, json
from app import logger

class ArduinoDriver():
    ser = None
    ser_timeout = 0.5
    ser_baudrate = 500000
    queue = None

    def __init__(self, app, mode):
        self.app = app
        self.mode = mode
        self.writer = SerialWriter()

    def connect(self, port):
        if self.app.debug == True:
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
        self.queue = ArduinoQueue(self.app, self.ser, self.mode)
        self.queue.start()

    def close(self):
        logger.info('Close AD')
        self.writer.is_running = False
        self.queue.is_running = False

class ArduinoQueue(threading.Thread):

    def __init__(self, app, ser, mode):
        threading.Thread.__init__(self)
        self.is_running = True
        self.app = app
        self.ser = ser
        self.mode = mode
        self.workQueue = queue.PriorityQueue()

    def run(self):
        # Transmitter mode
        if self.mode == 'tx':
            while True:
                if self.app.status != 'started':
                    time.sleep(1)
                    continue

                # Terminate the process
                if self.is_running == False:
                    break

                if not self.workQueue.empty():
                    queue_item = self.workQueue.get()
                    queue_item.run(self.app.sock, self.ser)
                else:
                    time.sleep(0.05)

        # Receiver mode
        elif self.mode == 'rx':
            self.ser.timeout = 1
            
            while True:
                if self.app.status != 'started':
                    time.sleep(1)
                    continue

                # Terminate the process
                if self.is_running == False:
                    break

                # if self.ser.in_waiting > 0:
                response = self.ser.readline()
                response = response.rstrip().decode('ascii', 'replace') # or ignore
                
                if response == '':
                    continue
                
                parser = SerialEventParser(self.app.sock, self.ser.port, response)
                parser.start()
                # else:
                #     time.sleep(0.05)
        # Both
        elif self.mode == 'rt':

            while True:
                if self.app.status != 'started':
                    time.sleep(1)
                    continue

                # Terminate the process
                if self.is_running == False:
                    break

                if not self.workQueue.empty():
                    queue_item = self.workQueue.get()
                    queue_item.run(self.app.sock, self.ser)
                else:
                    if self.ser.in_waiting > 0:
                        response = self.ser.readline()
                        response = response.rstrip().decode('ascii', 'replace')
                        parser = SerialEventParser(self.app.sock, self.ser.port, response)
                        parser.start()
                    else:
                        time.sleep(0.05)
        else:
            logger.warning('Unknown mode')

    def putItem(self, item):
        if self.mode != 'rx':
            self.workQueue.put(item)

class ArduinoQueueItem():

    def __init__(self, props, priority):
        self.buffer   = 32
        self.execute  = ''
        self.props    = props
        self.priority = priority

        if self.props['button_type'] == 'ir':
            self.createIrSignal()
        elif self.props['button_type'] == 'cmd':
            self.createCommand()
        elif self.props['button_type'] == 'bc':
            self.createBroadcast()

    def __cmp__(self, other):
        return cmp(self.priority, other.priority)

    def createIrSignal(self):
        nec_protocol = 0
        pre_data = []
        data = []
        pre_data.append('%si' % self.props['radio_pipe'].replace('0x', ''))

        zero = []
        one = []
        zero_bit = 0
        one_bit = 0
        compressed = ''

        for value in self.props['button_exec'].split(' '):
            if nec_protocol < 2:
                data.append(value)
                nec_protocol += 1
                continue

            x = int(value)

            if x <= 1000:
                # 0
                zero.append(x)
                if one_bit > 0:
                    compressed += "%db" % one_bit
                    one_bit = 0
                    zero_bit = 1
                else:
                    zero_bit += 1

            elif x < 1800:
                # 1
                one.append(x)
                if zero_bit > 0:
                    compressed += "%da" % zero_bit
                    zero_bit = 0
                    one_bit = 1
                else:
                    one_bit += 1
            else:
                # as it
                if zero_bit > 0:
                    compressed += "%da" % zero_bit
                    zero_bit = 0
                if one_bit > 0:
                    compressed += "%db" % one_bit
                    one_bit = 0
                if compressed:
                    data.append("[%s]" % compressed)
                    compressed = ''
                # Arduino int is too small, so cut it
                if x > 65000:
                    value = '65000'
                data.append(value)

        if zero_bit > 0:
            compressed += "%da" % zero_bit
        if one_bit > 0:
            compressed += "%db" % one_bit
        if compressed:
            data.append("[%s]" % compressed)

        data.append('\n')

        pre_data.append(str(round(sum(zero)/len(zero))))
        pre_data.append(str(round(sum(one)/len(one))))

        self.execute = ' '.join(pre_data + data)

    def createCommand(self):
        self.execute = '%sc%s\n' % (self.props['radio_pipe'].replace('0x', ''), self.props['button_exec'])

    def createBroadcast(self):
        self.execute = '%sb%s\n' % (self.props['radio_pipe'].replace('0x', ''), self.props['button_exec'])

    def run(self, sock, ser):
        ser.flushInput()
        ser.flushOutput()

        partial_signal = [self.execute[i:i+self.buffer] for i in range(0, len(self.execute), self.buffer)]

        # logger.info(partial_signal)
        
        response = ""

        for part in partial_signal:
            logger.info(part)
            b_arr = bytearray(part.encode())
            ser.write(b_arr)
            ser.flush()

            response = ser.readline()
            response = response.rstrip().decode()

            if response != 'next':
                break;

            response = ""
        
        # if response == "":
        #     response = ser.readline().rstrip().decode()

        # parser = SerialResponseParser(sock, self.props, response)
        # parser.start()

class SerialWriter(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.start_time = time.time()
        self.is_running = True
        self.emulator = None

    def run(self):
        while True:
            # Terminate the process
            if self.is_running == False:
                break
            if self.start_time + 5 < time.time():
                self.start_time = time.time()
                self.emulator.in_waiting = 10
            else:
                time.sleep(1)

class SerialEventParser(threading.Thread):

    def __init__(self, sock, port, response):
        threading.Thread.__init__(self)
        self.sock = sock
        self.port = port
        self.response = response

    def run(self):
        data = self.response.split(':')

        if 1 < len(data):
            if data[1] == 'FAIL':
                logger.warning('%s:%s' % (data[0], data[1]))
                response = json.dumps({'type': 'event', 'result': 'error', 'port': self.port, 'message': data[0]})
                self.sock.send(response.encode())
            elif data[1] == 'OK':
                logger.info('%s:%s' % (data[0], data[1]))
                response = json.dumps({'type': 'event', 'result': 'success', 'port': self.port, 'message': data[0]})
                self.sock.send(response.encode())
        else:
            logger.error(data[0])

class SerialResponseParser(threading.Thread):

    def __init__(self, sock, props, response):
        threading.Thread.__init__(self)
        self.sock = sock
        self.props = props
        self.response = response

    def run(self):
        data = self.response.split(':')

        if 1 < len(data):
            if data[1] == 'FAIL':
                logger.warning('%s:%s' % (data[0], data[1]))
                response = json.dumps({'type': 'response', 'result': 'error', 'user_id': self.props['user_id'], 'message': data[0]})
                self.sock.send(response.encode())
            elif data[1] == 'OK':
                logger.info('%s:%s' % (data[0], data[1]))
                response = json.dumps({'type': 'response', 'result': 'success', 'user_id': self.props['user_id'], 'message': data[0]})
                self.sock.send(response.encode())
        else:
            logger.error(data[0])

class SerialEmulator():

    def __init__(self, writer):
        self.writer = writer
        self.in_waiting = 0
        self.baudrate = 9600
        self.timeout = 0
        self.port = None
        
        self.buffering = False
        self.execute_type = 0

    def createOutput(self):
        temp = random.uniform(18, 26)
        hum = random.uniform(40, 65)
        bat = random.uniform(3.8, 4.2)
        pipe = random.choice(['AABBCCCC22', 'AABBCCDD99', 'AABBCCDD11'])

        output = 'r %s,type e,t %.2f,h %.2f,b %.2f:OK\n' % (pipe, temp, hum, bat)
        return output.encode()

    def open(self):
        logger.info('SERIAL %s: Opened' % self.port)
        self.writer.emulator = self
        self.writer.start()

    def flushInput(self):
        logger.info('SERIAL %s: flushInput' % self.port)

    def flushOutput(self):
        logger.info('SERIAL %s: flushOutput' % self.port)

    def flush(self):
        logger.info('SERIAL %s: flush' % self.port)

    def write(self, data):
        logger.info('SERIAL %s: Recieved bytearray' % self.port)
        
        if self.buffering == False:
            self.execute_type = data[10]

        if data.endswith("\n"):
            self.buffering = False
        else:
            self.buffering = True
        logger.info(data)

    def readline(self):
        if self.execute_type == 0:
            if self.in_waiting > 0:
                self.in_waiting = 0
                return self.createOutput()
            else:
                time.sleep(1)
                return ''.encode()
        else:
            if self.buffering == False:
                if self.execute_type == 105:
                    self.execute_type = 0
                    return 'ok:OK\n'.encode()
                elif self.execute_type == 99:
                    temp = random.uniform(18, 26)
                    hum = random.uniform(35, 65)
                    bat = random.uniform(0.1, 1)
                    self.execute_type = 0
                    output = "t %.2f,h %.2f,b %.2f:OK\n" % (temp, hum, bat)
                    return output.encode()

                return 'unknown type:FAIL\n'.encode()
            else:
                return "next\n".encode()

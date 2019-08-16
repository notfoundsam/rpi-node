import os, sys, math, time, random, logging
from datetime import datetime

def read_signal():
    # This pin is also referred to as GPIO18
    INPUT_WIRE = 12

    # Timeout after 15s
    t_end = time.time() + 15

    # Using for development
    if 'APP_ENV' in os.environ and os.environ['APP_ENV'] == 'development':
        # time.sleep(3)
        # return ''
        # signal = ''
        
        # for x in range(1,40):
        #     signal += random.choice(['1200 ', '500 '])
        # logging.info('Caught %s' % signal)

        # return signal
        return "8851 4435 565 1644 591 512 568 565 566 540 567 1642 568 565 567 1644 592 539 540 565 592 1623 592 1647 594 511 589 1650 562 1646 593 1643 594 513 595 511 590 516 565 569 592 510 595 1615 570 564 592 514 593 513 566 565 541 567 591 515 592 513 567 565 541 565 592 515 565 565 541 565 591 517 564 541 590 515 591 541 591 1619 568 564 538 568 566 539 591 513 592 543 561 545 589 516 593 512 565 567 565 539 566 1644 565 567 593 1618 593 1643 594 515 590 514 565 1675 589 514 593"
    else:
        import RPi.GPIO as GPIO

    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(INPUT_WIRE, GPIO.IN)

    logging.info('--- Waiting for signal ---')
    value = 1
    # Loop until we read a 0
    while value and time.time() < t_end:
        value = GPIO.input(INPUT_WIRE)
    if value:
        logging.info('--- Timeout ---')
        return False

    logging.info('--- Start to catch signal ---')
    # Grab the start time of the command
    startTime = datetime.now()

    # Used to buffer the command pulses
    command = []

    # The end of the "command" happens when we read more than
    # a certain number of 1s (1 is off for my IR receiver)
    numOnes = 0

    # Used to keep track of transitions from 1 to 0
    previousVal = 0

    while True:
        if value != previousVal:
            # The value has changed, so calculate the length of this run
            now = datetime.now()
            pulseLength = now - startTime
            startTime = now

            command.append((previousVal, pulseLength.microseconds))

        if value:
            numOnes = numOnes + 1
        else:
            numOnes = 0

        # 10000 is arbitrary, adjust as necessary
        if numOnes > 80000:
            break

        previousVal = value
        value = GPIO.input(INPUT_WIRE)
    
    logging.info('--- Finish to catch signal ---')

    result = []

    for (val, pulse) in command:
        result.append(str(pulse))

    text = ' '.join(result)

    return text

def compress_signal(signal):
    nec_protocol = 0
    pre_data = []
    data = []

    zero = []
    one = []
    zero_bit = 0
    one_bit = 0
    compressed = ''

    for value in signal.split(' '):
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

    pre_data.append(str(round(sum(zero)/len(zero))))
    pre_data.append(str(round(sum(one)/len(one))))

    message = ' '.join(pre_data + data)
    return 'i%s' % message

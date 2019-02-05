import os, sys, math, time
from datetime import datetime
from app import logger

def read_signal():
    # This pin is also referred to as GPIO18
    INPUT_WIRE = 12

    # Timeout after 15s
    t_end = time.time() + 15

    # Using for development
    if 'APP_ENV' in os.environ and os.environ['APP_ENV'] == 'development':
        time.sleep(5)
        signal = ''
        
        for x in xrange(1,40):
            signal += random.choice(['1200', '500'])
        logger.info('Caught %s' % signal)

        return signal    
    else:
        import RPi.GPIO as GPIO

    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(INPUT_WIRE, GPIO.IN)

    logger.info('--- Waiting for signal ---')
    value = 1
    # Loop until we read a 0
    while value and time.time() < t_end:
        value = GPIO.input(INPUT_WIRE)
    if value:
        logger.info('--- Timeout ---')
        return False

    logger.info('--- Start to catch signal ---')
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
    
    logger.info('--- Finish to catch signal ---')

    result = []

    for (val, pulse) in command:
        result.append(str(pulse))

    text = ' '.join(result)

    return text

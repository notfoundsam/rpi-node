import sys
import datetime

def debug(message):
    sys.stderr.write('%s - [debug] ' % get_log_time())
    sys.stderr.write('%s\n' % message)

def info(message):
    sys.stderr.write('%s - [info] ' % get_log_time())
    sys.stderr.write('%s\n' % message)

def warning(message):
    sys.stderr.write('%s - [warning] ' % get_log_time())
    sys.stderr.write('%s\n' % message)
    
def error(message):
    sys.stderr.write('%s - [error] ' % get_log_time())
    sys.stderr.write('%s\n' % message)

def get_log_time():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

#!/usr/bin/env python3
import os
from app import App

if 'APP_ENV' in os.environ and os.environ['APP_ENV'] == 'development':
    debug = True
else:
    debug = False

app = App()

if 'APP_DOCKER' in os.environ:
    app.DB_HOST = 'db'
    app.DB_PORT = '3306'
    app.DB_NAME = 'smart_remote'
    app.DB_USER = 'root'
    app.DB_PASS = 'root'

    app.emulation = True
else:
    app.DB_HOST = '192.168.100.111'
    app.DB_PORT = '3306'
    app.DB_NAME = 'smart_remote'
    app.DB_USER = 'root'
    app.DB_PASS = 'root'

    app.emulation = False

if __name__ == '__main__':
    app.run(debug=debug)

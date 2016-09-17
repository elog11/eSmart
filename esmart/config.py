#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  config.py - Global eSmart configuration settings
#

#
#  This file is part of eSmart
#
#  eSmart is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  eSmart is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with eSmart. 

import os

ESMART_VERSION = '1.0.0'

INSTALL_DIRECTORY = os.path.dirname(os.path.realpath(__file__)) + '/..'

LOCK_PATH = '/var/lock'
DAEMON_PID_FILE = os.path.join(LOCK_PATH, 'esmart.pid')

LOG_PATH = '/var/log/esmart' # Where generated logs are stored

LOGIN_LOG_FILE = os.path.join(LOG_PATH, 'login.log')
DAEMON_LOG_FILE = os.path.join(LOG_PATH, 'esmart.log')
HTTP_LOG_FILE = '/var/log/apache2/error.log'
UPDATE_LOG_FILE = os.path.join(LOG_PATH, 'esmartupdate.log')
RESTORE_LOG_FILE = os.path.join(LOG_PATH, 'esmartrestore.log')

# Logs that are on the tempfs and are written to every sensor read
# DAEMON_LOG_FILE_TMP = os.path.join(LOG_PATH, "daemon-tmp.log")
# SENSOR_T_LOG_FILE_TMP = os.path.join(LOG_PATH, "sensor-t-tmp.log")
# SENSOR_HT_LOG_FILE_TMP = os.path.join(LOG_PATH, "sensor-ht-tmp.log")
# SENSOR_CO2_LOG_FILE_TMP = os.path.join(LOG_PATH, "sensor-co2-tmp.log")
# SENSOR_PRESS_LOG_FILE_TMP = os.path.join(LOG_PATH, "sensor-press-tmp.log")
# RELAY_LOG_FILE_TMP = os.path.join(LOG_PATH, "relay-tmp.log")

# Logs that are periodically concatenated (every 6 hours) to the SD card
# DAEMON_LOG_FILE = os.path.join(LOG_PATH, "daemon.log")
# SENSOR_T_LOG_FILE = os.path.join(LOG_PATH, "sensor-t.log")
# SENSOR_HT_LOG_FILE = os.path.join(LOG_PATH, "sensor-ht.log")
# SENSOR_CO2_LOG_FILE = os.path.join(LOG_PATH, "sensor-co2.log")
# SENSOR_PRESS_LOG_FILE = os.path.join(LOG_PATH, "sensor-press.log")
# RELAY_LOG_FILE = os.path.join(LOG_PATH, "relay.log")

DATABASE_PATH = os.path.join(INSTALL_DIRECTORY, 'databases')
SQL_DATABASE_ESMART = os.path.join(DATABASE_PATH, 'esmart.db')
SQL_DATABASE_USER = os.path.join(DATABASE_PATH, 'users.db')
SQL_DATABASE_NOTE = os.path.join(DATABASE_PATH, 'notes.db')

# Influxdb
INFLUXDB_HOST = 'localhost'
INFLUXDB_PORT = 8086
INFLUXDB_USER = 'esmart'
INFLUXDB_PASSWORD = 'mmdu77sj3nIoiajjs'
INFLUXDB_DATABASE = 'esmart_db'

# Anonymous usage statistics
STATS_CSV = os.path.join(DATABASE_PATH, 'statistics.csv')
ID_FILE = os.path.join(DATABASE_PATH, 'statistics.id')

# Camera
LOCK_FILE_STREAM = os.path.join(DATABASE_PATH, 'esmart-camera-stream.pid')
LOCK_FILE_TIMELAPSE = os.path.join(DATABASE_PATH, 'esmart-camera-timelapse.pid')
FILE_TIMELAPSE_PARAM = os.path.join(DATABASE_PATH, 'timelapse_parameters.csv')

# Anonymous statistics
STATS_INTERVAL = 86400  # 1 day
STATS_HOST = 'fungi.kylegabriel.com'
STATS_PORT = 8086
STATS_USER = 'esmart_stats'
STATS_PASSWORD = 'Io8Nasr5JJDdhPOj32222'
STATS_DATABASE = 'esmart_stats'

# Login
LOGIN_ATTEMPTS = 5
LOGIN_BAN_TIME_SECONDS = 600 # 10 minutes

# Relay
MAX_AMPS = 15

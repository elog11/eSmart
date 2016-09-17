#!/usr/bin/python
# coding=utf-8
#
# controller_pid.py - PID controller that manages descrete control of a
#                     regulation system of sensors, relays, and devices
#
# PID controller code was used from the source below, with modifications.
#
# Copyright (c) 2010 cnr437@gmail.com
#
# Licensed under the MIT License <http://opensource.org/licenses/MIT>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# <http://code.activestate.com/recipes/577231-discrete-pid-controller/>

import calendar
import datetime
import threading
import time as t
import timeit

from config import INFLUXDB_HOST
from config import INFLUXDB_PORT
from config import INFLUXDB_USER
from config import INFLUXDB_PASSWORD
from config import INFLUXDB_DATABASE
from config import SQL_DATABASE_ESMART
from databases.esmart_db.models import Method
from databases.esmart_db.models import PID
from databases.esmart_db.models import Relay
from databases.utils import session_scope
from esmart_client import DaemonControl
from utils.influx import read_last_influxdb, write_influxdb
from utils.method import sine_wave_y_out

ESMART_DB_PATH = 'sqlite:///' + SQL_DATABASE_ESMART


class PIDController(threading.Thread):
    """
    Class to operate discrete PID controller

    """

    def __init__(self, ready, logger, pid_id):
        threading.Thread.__init__(self)

        self.thread_startup_timer = timeit.default_timer()
        self.thread_shutdown_timer = 0
        self.ready = ready
        self.logger = logger
        self.pid_id = pid_id
        self.control = DaemonControl()

        with session_scope(ESMART_DB_PATH) as new_session:
            pid = new_session.query(PID).filter(PID.id == self.pid_id).first()
            self.sensor_id = pid.sensor_id
            self.measure_type = pid.measure_type
            self.method_id = pid.method_id
            self.direction = pid.direction
            self.raise_relay_id = pid.raise_relay_id
            self.raise_min_duration = pid.raise_min_duration
            self.raise_max_duration = pid.raise_max_duration
            self.lower_relay_id = pid.lower_relay_id
            self.lower_min_duration = pid.lower_min_duration
            self.lower_max_duration = pid.lower_max_duration
            self.Kp = pid.p
            self.Ki = pid.i
            self.Kd = pid.d
            self.measure_interval = pid.period
            self.default_set_point = pid.setpoint
            self.set_point = pid.setpoint

        self.Derivator = 0
        self.Integrator = 0
        self.Integrator_max = 500
        self.Integrator_min = -500
        self.error = 0.0
        self.P_value = None
        self.I_value = None
        self.D_value = None
        self.raise_seconds_on = 0
        self.timer = t.time()+self.measure_interval

        # Check if a method is set for this PID
        if self.method_id:
            with session_scope(ESMART_DB_PATH) as new_session:
                method = new_session.query(Method)
                method = method.filter(Method.method_id == self.method_id)
                method = method.filter(Method.method_order == 0).first()
                self.method_type = method.method_type
                self.method_start_time = method.start_time
            if self.method_type == 'Duration':
                if self.method_start_time == 'Ended':
                    # Method has ended and hasn't been instructed to begin again
                    pass
                elif self.method_start_time == 'Ready' or self.method_start_time == None:
                    # Method has been instructed to begin
                    with session_scope(ESMART_DB_PATH) as db_session:
                        mod_method = db_session.query(Method)
                        mod_method = mod_method.filter(Method.method_id == self.method_id)
                        mod_method = mod_method.filter(Method.method_order == 0).first()
                        mod_method.start_time = datetime.datetime.now()
                        self.method_start_time = mod_method.start_time
                        db_session.commit()
                else:
                    # Method neither instructed to begin or not to
                    # Likely there was a daemon restart ot power failure
                    # Resume method with saved start_time
                    self.method_start_time = datetime.datetime.strptime(
                        self.method_start_time, '%Y-%m-%d %H:%M:%S.%f')
                    self.logger.warning("[PID {}] Resuming method {} started at {}".format(
                        self.pid_id, self.method_id, self.method_start_time))


    def run(self):
        try:
            self.running = True
            self.logger.info("[PID {}] Activated in {}ms".format(
                self.pid_id,
                (timeit.default_timer()-self.thread_startup_timer)*1000))
            self.ready.set()

            while (self.running):
                if t.time() > self.timer:
                    self.timer = self.timer+self.measure_interval
                    self.get_last_measurement()
                    self.manipulate_relays()
                t.sleep(0.1)

            if self.raise_relay_id:
                self.control.relay_off(self.raise_relay_id)
            if self.lower_relay_id:
                self.control.relay_off(self.lower_relay_id)

            self.running = False
            self.logger.info("[PID {}] Deactivated in {}ms".format(
                self.pid_id,
                (timeit.default_timer()-self.thread_shutdown_timer)*1000))
        except Exception as except_msg:
                self.logger.exception("[PID {}] Error: {}".format(self.pid_id,
                                                                except_msg))


    def update(self, current_value):
        """
        Calculate PID output value from reference input and feedback

        :return: Manipulated, or control, variable. This is the PID output.
        :rtype: float

        :param current_value: The input, or process, variable (the actual
            measured condition by the sensor)
        :type current_value: float
        """
        self.error = self.set_point - current_value

        # Calculate P-value
        self.P_value = self.Kp * self.error

        # Calculate I-value
        self.Integrator += self.error
        # Old method for managing Integrator
        # if self.Integrator > self.Integrator_max:
        #     self.Integrator = self.Integrator_max
        # elif self.Integrator < self.Integrator_min:
        #     self.Integrator = self.Integrator_min
        # New method for regulating Integrator
        if self.measure_interval is not None:  
            if self.Integrator * self.Ki > self.measure_interval:
                self.Integrator = self.measure_interval / self.Ki
            elif self.Integrator * self.Ki < -self.measure_interval:
                self.Integrator = -self.measure_interval / self.Ki
        self.I_value = self.Integrator * self.Ki

        # Calculate D-value
        self.D_value = self.Kd * (self.error - self.Derivator)
        self.Derivator = self.error

        # Produce output form P, I, and D values
        PID = self.P_value + self.I_value + self.D_value
        return PID


    def get_last_measurement(self):
        """
        Retrieve the latest sensor measurement from InfluxDB

        :rtype: None
        """
        self.last_measurement_success = False
        # Get latest measurement (from within the past minute) from influxdb
        try:
            self.last_measurement = read_last_influxdb(
                INFLUXDB_HOST,
                INFLUXDB_PORT,
                INFLUXDB_USER,
                INFLUXDB_PASSWORD,
                INFLUXDB_DATABASE,
                self.sensor_id,
                self.measure_type)
            if self.last_measurement:
                measurement_list = list(self.last_measurement.get_points(
                    measurement=self.measure_type))
                self.last_time = measurement_list[0]['time']
                self.last_measurement = measurement_list[0]['value']
                utc_dt = datetime.datetime.strptime(self.last_time.split(".")[0], '%Y-%m-%dT%H:%M:%S')
                utc_timestamp = calendar.timegm(utc_dt.timetuple())
                local_timestamp = str(datetime.datetime.fromtimestamp(utc_timestamp))
                self.logger.debug("[PID {}] Latest {}: {} @ {}".format(
                    self.pid_id, self.measure_type,
                    self.last_measurement, local_timestamp))
                self.last_measurement_success = True
            else:
                self.logger.warning("[PID {}] No data returned "
                                    "from influxdb".format(self.pid_id))
        except Exception as except_msg:
            self.logger.exception("[PID {}] Failed to read "
                                "measurement from the influxdb "
                                "database: {}".format(self.pid_id,
                                                      except_msg))


    def manipulate_relays(self):
        """
        Activate a relay based on PID output (control variable) and whether
        the manipulation directive is to raise, lower, or both.

        :rtype: None
        """
        # If there was a measurement able to be retrieved from
        # influxdb database that was entered within the past minute
        if self.last_measurement_success:

            # Update setpoint if a method is selected
            if self.method_id != '':
                self.calculate_method_setpoint(self.method_id)

            self.addSetpointInfluxdb(self.pid_id, self.set_point)

            # Update PID and get control variable
            self.control_variable = self.update(self.last_measurement)

            #
            # PID control variable positive to raise environmental condition
            #
            if self.direction in ['raise', 'both'] and self.raise_relay_id:
                if self.control_variable > 0:
                    # Ensure the relay on duration doesn't exceed the set maximum
                    if (self.raise_max_duration and
                            self.control_variable > self.raise_max_duration):
                        self.raise_seconds_on = self.raise_max_duration
                    else:
                        self.raise_seconds_on = float("{0:.2f}".format(self.control_variable))

                    # Turn off lower_relay if active, because we're now raising
                    if self.lower_relay_id:
                        with session_scope(ESMART_DB_PATH) as new_session:
                            relay = new_session.query(Relay).filter(
                                Relay.id == self.lower_relay_id).first()
                            if relay.is_on():
                                self.control.relay_off(self.lower_relay_id)

                    if self.raise_seconds_on > self.raise_min_duration:
                        # Activate raise_relay for a duration
                        self.logger.debug("[PID {}] Setpoint: {} "
                            "Output: {} to relay {}".format(
                                self.pid_id,
                                self.set_point,
                                self.control_variable,
                                self.raise_relay_id))
                        self.control.relay_on(self.raise_relay_id,
                                         self.raise_seconds_on)
                else:
                    self.control.relay_off(self.raise_relay_id)

            #
            # PID control variable negative to lower environmental condition
            #
            if self.direction in ['lower', 'both'] and self.lower_relay_id:
                if self.control_variable < 0:
                    # Ensure the relay on duration doesn't exceed the set maximum
                    if (self.lower_max_duration and
                            abs(self.control_variable) > self.lower_max_duration):
                        self.lower_seconds_on = self.lower_max_duration
                    else:
                        self.lower_seconds_on = abs(float("{0:.2f}".format(self.control_variable)))

                    # Turn off raise_relay if active, because we're now lowering
                    if self.raise_relay_id:
                        with session_scope(ESMART_DB_PATH) as new_session:
                            relay = new_session.query(Relay).filter(
                                Relay.id == self.raise_relay_id).first()
                            if relay.is_on():
                                self.control.relay_off(self.raise_relay_id)

                    if self.lower_seconds_on > self.lower_min_duration:
                        # Activate lower_relay for a duration
                        self.logger.debug("[PID {}] Setpoint: {} "
                            "Output: {} to relay {}".format(
                                self.pid_id,
                                self.set_point,
                                self.control_variable,
                                self.lower_relay_id))
                        self.control.relay_on(self.lower_relay_id,
                                         self.lower_seconds_on)
                else:
                    self.control.relay_off(self.lower_relay_id)

        else:
            if self.direction in ['raise', 'both'] and self.raise_relay_id:
                self.control.relay_off(self.raise_relay_id)
            if self.direction in ['lower', 'both'] and self.lower_relay_id:
                self.control.relay_off(self.lower_relay_id)


    def now_in_range(self, start_time, end_time):
        """
        Check if the current time is between start_time and end_time

        :return: 1 is within range, 0 if not within range
        :rtype: int
        """
        start_hour = int(start_time.split(":")[0])
        start_min = int(start_time.split(":")[1])
        end_hour = int(end_time.split(":")[0])
        end_min = int(end_time.split(":")[1])
        now_time = datetime.datetime.now().time()
        now_time = now_time.replace(second=0, microsecond=0)
        if ((start_hour < end_hour) or
                (start_hour == end_hour and start_min < end_min)):
            if now_time >= datetime.time(start_hour, start_min) and now_time <= datetime.time(end_hour, end_min):
                return 1  # Yes now within range
        else:
            if now_time >= datetime.time(start_hour, start_min) or now_time <= datetime.time(end_hour, end_min):
                return 1  # Yes now within range
        return 0 # No now not within range


    def calculate_method_setpoint(self, method_id):
        with session_scope(ESMART_DB_PATH) as new_session:
            method = new_session.query(Method)
            new_session.expunge_all()
            new_session.close()

        method_key = method.filter(Method.method_id == method_id)
        method_key = method_key.filter(Method.method_order == 0).first()

        method = method.filter(Method.method_id == method_id)
        method = method.filter(Method.relay_id == None)
        method = method.filter(Method.method_order > 0)
        method = method.order_by(Method.method_order.asc()).all()

        now = datetime.datetime.now()

        # Calculate where the current time/date is within the time/date method
        if method_key.method_type == 'Date':
            for each_method in method:
                start_time = datetime.datetime.strptime(each_method.start_time, '%Y-%m-%d %H:%M:%S')
                end_time = end_time = datetime.datetime.strptime(each_method.end_time, '%Y-%m-%d %H:%M:%S')
                if start_time < now < end_time:
                    start_setpoint = each_method.start_setpoint
                    if each_method.end_setpoint:
                        end_setpoint = each_method.end_setpoint
                    else:
                        end_setpoint = each_method.start_setpoint

                    setpoint_diff = abs(end_setpoint-start_setpoint)
                    total_seconds = (end_time-start_time).total_seconds()
                    part_seconds = (now-start_time).total_seconds()
                    percent_total = part_seconds/total_seconds

                    if start_setpoint < end_setpoint:
                        new_setpoint = start_setpoint+(setpoint_diff*percent_total)
                    else:
                        new_setpoint = start_setpoint-(setpoint_diff*percent_total)

                    self.logger.debug("[Method] Start: {} End: {}".format(
                        start_time, end_time))
                    self.logger.debug("[Method] Start: {} End: {}".format(
                        start_setpoint, end_setpoint))
                    self.logger.debug("[Method] Total: {} Part total: {} ({}%)".format(
                        total_seconds, part_seconds, percent_total))
                    self.logger.debug("[Method] New Setpoint: {}".format(
                        new_setpoint))
                    self.set_point = new_setpoint
                    return 0

        # Calculate where the current Hour:Minute:Seconds is within the Daily method
        elif method_key.method_type == 'Daily':
            daily_now = datetime.datetime.now().strftime('%H:%M:%S')
            daily_now = datetime.datetime.strptime(str(daily_now), '%H:%M:%S')
            for each_method in method:
                start_time = datetime.datetime.strptime(each_method.start_time, '%H:%M:%S')
                end_time = end_time = datetime.datetime.strptime(each_method.end_time, '%H:%M:%S')
                if start_time < daily_now < end_time:
                    start_setpoint = each_method.start_setpoint
                    if each_method.end_setpoint:
                        end_setpoint = each_method.end_setpoint
                    else:
                        end_setpoint = each_method.start_setpoint

                    setpoint_diff = abs(end_setpoint-start_setpoint)
                    total_seconds = (end_time-start_time).total_seconds()
                    part_seconds = (daily_now-start_time).total_seconds()
                    percent_total = part_seconds/total_seconds

                    if start_setpoint < end_setpoint:
                        new_setpoint = start_setpoint+(setpoint_diff*percent_total)
                    else:
                        new_setpoint = start_setpoint-(setpoint_diff*percent_total)

                    self.logger.debug("[Method] Start: {} End: {}".format(
                        start_time.strftime('%H:%M:%S'), end_time.strftime('%H:%M:%S')))
                    self.logger.debug("[Method] Start: {} End: {}".format(
                        start_setpoint, end_setpoint))
                    self.logger.debug("[Method] Total: {} Part total: {} ({}%)".format(
                        total_seconds, part_seconds, percent_total))
                    self.logger.debug("[Method] New Setpoint: {}".format(
                        new_setpoint))
                    self.set_point = new_setpoint
                    return 0

        elif method_key.method_type == 'DailySine':
            new_setpoint = sine_wave_y_out(method_key.amplitude,
                                           method_key.frequency,
                                           method_key.shift_angle,
                                           method_key.shift_y)
            self.set_point = new_setpoint
            return 0

        # Calculate the duration in the method based on self.method_start_time
        elif method_key.method_type == 'Duration' and self.method_start_time != 'Ended':
            seconds_from_start = (now-self.method_start_time).total_seconds()
            total_sec = 0
            previous_total_sec = 0
            for each_method in method:
                total_sec += each_method.duration_sec
                if previous_total_sec <= seconds_from_start < total_sec:
                    row_start_time = float(self.method_start_time.strftime('%s'))+previous_total_sec
                    row_since_start_sec = (now-(self.method_start_time+datetime.timedelta(0, previous_total_sec))).total_seconds()
                    percent_row = row_since_start_sec/each_method.duration_sec

                    start_setpoint = each_method.start_setpoint
                    if each_method.end_setpoint:
                        end_setpoint = each_method.end_setpoint
                    else:
                        end_setpoint = each_method.start_setpoint
                    setpoint_diff = abs(end_setpoint-start_setpoint)
                    if start_setpoint < end_setpoint:
                        new_setpoint = start_setpoint+(setpoint_diff*percent_row)
                    else:
                        new_setpoint = start_setpoint-(setpoint_diff*percent_row)
                    
                    self.logger.debug("[Method] Start: {} Seconds Since: {}".format(
                        self.method_start_time, seconds_from_start))
                    self.logger.debug("[Method] Start time of row: {}".format(
                        datetime.datetime.fromtimestamp(row_start_time)))
                    self.logger.debug("[Method] Sec since start of row: {}".format(
                        row_since_start_sec))
                    self.logger.debug("[Method] Percent of row: {}".format(
                        percent_row))
                    self.logger.debug("[Method] New Setpoint: {}".format(
                        new_setpoint))
                    self.set_point = new_setpoint
                    return 0
                previous_total_sec = total_sec

            # Duration method has ended, reset start_time locally and in DB
            if self.method_start_time:
                with session_scope(ESMART_DB_PATH) as db_session:
                    mod_method = db_session.query(Method).filter(
                        Method.method_id == self.method_id)
                    mod_method = mod_method.filter(Method.method_order == 0).first()
                    mod_method.start_time = 'Ended'
                    db_session.commit()
                self.method_start_time = 'Ended'

        # Setpoint not needing to be calculated, use default setpoint
        self.set_point = self.default_set_point


    def addSetpointInfluxdb(self, pid_id, setpoint):
        """
        Add a setpoint entry to InfluxDB

        :rtype: None
        """
        write_db = threading.Thread(
            target=write_influxdb,
            args=(self.logger, INFLUXDB_HOST,
                  INFLUXDB_PORT, INFLUXDB_USER,
                  INFLUXDB_PASSWORD, INFLUXDB_DATABASE,
                  'pid', pid_id, 'setpoint', setpoint,))
        write_db.start()


    def setPoint(self, set_point):
        """Initilize the setpoint of PID"""
        self.set_point = set_point
        self.Integrator = 0
        self.Derivator = 0


    def setIntegrator(self, Integrator):
        """Set the Integrator of the controller"""
        self.Integrator = Integrator


    def setDerivator(self, Derivator):
        """Set the Derivator of the controller"""
        self.Derivator = Derivator


    def setKp(self, P):
        """Set Kp gain of the controller"""
        self.Kp = P


    def setKi(self, I):
        """Set Ki gain of the controller"""
        self.Ki = I


    def setKd(self, D):
        """Set Kd gain of the controller"""
        self.Kd = D


    def getPoint(self):
        return self.set_point


    def getError(self):
        return self.error


    def getIntegrator(self):
        return self.Integrator


    def getDerivator(self):
        return self.Derivator


    def isRunning(self):
        return self.running


    def stopController(self):
        self.thread_shutdown_timer = timeit.default_timer()
        self.running = False
        # Unset method start time
        if self.method_id:
            with session_scope(ESMART_DB_PATH) as db_session:
                mod_method = db_session.query(Method)
                mod_method = mod_method.filter(Method.method_id == self.method_id)
                mod_method = mod_method.filter(Method.method_order == 0).first()
                mod_method.start_time = 'Ended'
                db_session.commit()

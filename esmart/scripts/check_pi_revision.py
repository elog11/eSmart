#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  check_pi_revision.py - Output the Raspbery Pi revision
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
#  along with eSmart. If not, see <http://www.gnu.org/licenses/>.
#
#  Contact at kylegabriel.com

import RPi.GPIO as GPIO
print(GPIO.RPI_REVISION)
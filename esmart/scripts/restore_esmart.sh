#!/bin/bash
#
#  restore_esmart.sh - Restore eSmart from a backup
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


if [ "$EUID" -ne 0 ]; then
    printf "Please run as root\n"
    exit
fi

INSTALL_DIRECTORY=$( cd "$( dirname "${BASH_SOURCE[0]}" )/../../" && pwd -P )
cd $INSTALL_DIRECTORY

if [ ! -e $2 ]; then         
   echo "Directory does not exist"         
   exit 1
elif [ ! -d $2 ]; then         
    echo "Input not a directory"        
    exit 2
fi

NOW=$(date +"%m-%d-%Y %H:%M:%S")
printf "#### Restore of backup $2 initiated $NOW ####\n"

printf "#### Stopping Daemon and HTTP server ####\n"
service esmart stop
/etc/init.d/apache2 stop

CURCOMMIT=$(git rev-parse --short HEAD)
printf "#### Creating backup /var/eSmart-backups/eSmart-$NOW-$CURCOMMIT ####\n"
mkdir -p /var/eSmart-backups
mkdir -p /var/eSmart-backups/eSmart-$NOW-$CURCOMMIT

if cp -a $INSTALL_DIRECTORY/. /var/eSmart-backups/eSmart-$NOW-$CURCOMMIT/
then
    directory=$2
    commit=${directory:47}
    printf "#### Resetting to commit $commit ####\n"
    git reset --hard $commit

    printf "#### Restoring all files from $2 ####\n"
    rm -rf $INSTALL_DIRECTORY/*
    cp -R $2/* $INSTALL_DIRECTORY/

    printf "#### Starting Daemon and HTTP server ####\n"
    service esmart start
    /etc/init.d/apache2 start

    printf "#### Restore Complete ####\n\n"
else
    printf "Error: Unable to create backup"
    exit 3

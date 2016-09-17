#!/bin/bash
#
#  update_post.sh - Extra commands to execute for the update process.
#                   Used as a way to provide additional commands to
#                   execute that wouldn't be possible from the running
#                   update script.
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
    printf "Please run as root\n";
    exit
fi

INSTALL_DIRECTORY=$( cd "$( dirname "${BASH_SOURCE[0]}" )/../../" && pwd -P )
cd $INSTALL_DIRECTORY

ln -snf $INSTALL_DIRECTORY /var/www/esmart
cp -f $INSTALL_DIRECTORY/esmart_flask_apache.conf /etc/apache2/sites-available/

if [ -f "$INSTALL_DIRECTORY/esmart_flask/ssl_certs/cert.pem" ] && [ ! -d "$INSTALL_DIRECTORY/esmart/frontend/ssl_certs/" ]; then
    mkdir -p $INSTALL_DIRECTORY/esmart/frontend/ssl_certs/
    cp $INSTALL_DIRECTORY/esmart_flask/ssl_certs/* $INSTALL_DIRECTORY/esmart/frontend/ssl_certs/
fi

$INSTALL_DIRECTORY/esmart/scripts/update_esmart.sh upgrade-packages

printf "#### Enable esmart service ####\n"
rm -rf /etc/systemd/system/esmart.service
rm -rf /etc/systemd/system/multi-user.target.wants/esmart.service
systemctl enable $INSTALL_DIRECTORY/esmart/scripts/esmart.service

printf "#### Checking if python modules are up-to-date ####\n"
# Make sure python modules are installed/updated
pip install --upgrade -r $INSTALL_DIRECTORY/requirements.txt

printf "#### Upgrading database ####\n"
cd $INSTALL_DIRECTORY/databases
alembic upgrade head

printf "#### Removing statistics file ####\n"
rm $INSTALL_DIRECTORY/databases/statistics.csv

printf "#### Setting permissions ####\n"
$INSTALL_DIRECTORY/esmart/scripts/update_esmart.sh initialize

printf "#### Starting eSmart daemon and reloading Apache ####\n"
$INSTALL_DIRECTORY/esmart/esmart_daemon.py
touch $INSTALL_DIRECTORY/esmart_flask.wsgi

#!/bin/bash
#
# eSmart install script
#
# Usage: sudo ./setup.sh
#

if [ "$EUID" -ne 0 ]; then
    printf "Please run as root with \"sudo ./setup.sh\"\n";
    exit
fi

INSTALL_DIRECTORY=$( cd "$( dirname "${BASH_SOURCE[0]}" )/" && pwd -P )
cd $INSTALL_DIRECTORY

LOG_LOCATION=$INSTALL_DIRECTORY/setup.log
exec > >(tee -i $LOG_LOCATION)
exec 2>&1

abort()
{
    echo >&2 '
***************
*** ABORTED ***
***************
'
    echo "An error occurred. Exiting..." >&2
    exit 1
}

trap 'abort' 0

set -e

NOW=$(date +"%m-%d-%Y %H:%M:%S")
printf "### eSmart installation began at $NOW\n\n"

printf "#### Uninstall current version of pip\n"
apt-get update -y
apt-get purge -y python-pip

printf "#### Install latest pip\n"
apt-get upgrade -y
apt-get install -y libav-tools libffi-dev libi2c-dev python-dev python-setuptools python-smbus sqlite3
easy_install pip
pip install -U pip

# printf "#### Uninstalling specific prerequisites\n"
# pip uninstall -y Adafruit_ADS1x15
# pip uninstall -y Adafruit_BMP
# pip uninstall -y Adafruit_DHT
# pip uninstall -y Adafruit_GPIO
# pip uninstall -y Adafruit_Python_DHT
# pip uninstall -y Adafruit_TMP
# pip uninstall -y MCP342x

printf "#### Installing prerequisites\n"
wget --quiet --show-progress -P $INSTALL_DIRECTORY/ abyz.co.uk/rpi/pigpio/pigpio.zip
unzip pigpio.zip
cd $INSTALL_DIRECTORY/PIGPIO
make -j4
make install

git clone git://git.drogon.net/wiringPi $INSTALL_DIRECTORY/wiringPi
cd $INSTALL_DIRECTORY/wiringPi
./build

wget --quiet --show-progress -P $INSTALL_DIRECTORY/ https://dl.influxdata.com/influxdb/releases/influxdb_0.13.0_armhf.deb
dpkg -i $INSTALL_DIRECTORY/influxdb_0.13.0_armhf.deb
service influxdb start

cd $INSTALL_DIRECTORY
pip install -r requirements.txt --upgrade

rm -rf ./PIGPIO ./pigpio.zip ./wiringPi ./influxdb_0.13.0_armhf.deb

printf "#### Creating InfluxDB database and user\n"
influx -execute "CREATE DATABASE esmart_db"
influx -database esmart_db -execute "CREATE USER esmart WITH PASSWORD 'mmdu77sj3nIoiajjs'"

printf "#### Creating cron entry to start pigpiod at boot\n"
$INSTALL_DIRECTORY/esmart/scripts/crontab.sh esmart

printf "#### Installing and configuring apache2 web server\n"
apt-get install -y apache2 libapache2-mod-wsgi
a2enmod wsgi ssl
ln -sf $INSTALL_DIRECTORY/esmart_flask_apache.conf /etc/apache2/sites-enabled/000-default.conf

printf "#### Creating SSL certificates at $INSTALL_DIRECTORY/esmart/frontend/ssl_certs (replace with your own if desired)\n"
mkdir -p $INSTALL_DIRECTORY/esmart/frontend/ssl_certs
cd $INSTALL_DIRECTORY/esmart/frontend/ssl_certs/

openssl req \
    -new \
    -x509 \
    -sha512 \
    -days 365 \
    -nodes \
    -out cert.pem \
    -keyout privkey.pem\
    -subj "/C=US/ST=Georgia/L=Atlanta/O=esmart/OU=esmart/CN=esmart"

openssl genrsa -out certificate.key 1024

openssl req \
    -new \
    -key certificate.key \
    -out certificate.csr \
    -subj "/C=US/ST=Georgia/L=Atlanta/O=esmart/OU=esmart/CN=esmart"

openssl x509 -req \
    -days 365 \
    -in certificate.csr -CA cert.pem \
    -CAkey privkey.pem \
    -set_serial $RANDOM \
    -out chain.pem

rm -f certificate.csr

printf "#### Enabling esmart startup script\n"
systemctl enable $INSTALL_DIRECTORY/esmart/scripts/esmart.service

printf "#### Creating SQLite databases\n"
$INSTALL_DIRECTORY/init_databases.py -i all

$INSTALL_DIRECTORY/esmart/scripts/update_esmart.sh initialize

trap : 0

echo >&2 '
************
*** DONE *** 
************
'

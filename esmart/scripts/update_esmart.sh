#!/bin/bash
#
#  update_esmart.sh - Update eSmart to the lastest version on GitHub
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

case "${1:-''}" in
    'backup')
        NOW=$(date +"%Y-%m-%d_%H-%M-%S")
        CURCOMMIT=$(git rev-parse --short HEAD)
        printf "#### $INSTALL_DIRECTORY Creating backup /var/eSmart-backups/eSmart-$NOW-$CURCOMMIT ####\n"
        mkdir -p /var/eSmart-backups
        mkdir -p /var/eSmart-backups/eSmart-$NOW-$CURCOMMIT
        rsync -ah --stats --exclude old --exclude .git --exclude src $INSTALL_DIRECTORY/ /var/eSmart-backups/eSmart-$NOW-$CURCOMMIT
    ;;
    'upgrade')
        echo "1" > $INSTALL_DIRECTORY/.updating
        NOW=$(date +"%m-%d-%Y %H:%M:%S")
        printf "#### Update Initiated $NOW ####\n"

        printf "#### Checking for Update ####\n"
        git fetch origin

        if git status -uno | grep 'Your branch is behind' > /dev/null; then
            git status -uno | grep 'Your branch is behind'
            printf "The remote git repository is newer than yours. This could mean there is an update to eSmart.\n"

            if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
                printf "#### Stopping eSmart Daemon ####\n"
                $INSTALL_DIRECTORY/esmart/esmart_client.py -t

                # Create backup
                $INSTALL_DIRECTORY/esmart/scripts/update_esmart.sh backup

                printf "#### Updating From GitHub ####\n"
                git fetch
                git reset --hard origin/master

                printf "#### Executing Post-Upgrade Commands ####\n"
                if [ -f $INSTALL_DIRECTORY/esmart/scripts/update_post.sh ]; then
                    $INSTALL_DIRECTORY/esmart/scripts/update_post.sh
                    printf "#### End Post-Upgrade Commands ####\n"
                else
                    printf "Error: update_post.sh not found\n"
                fi
                
                END=$(date +"%m-%d-%Y %H:%M:%S")
                printf "#### Update Finished $END ####\n\n"

                echo '0' > $INSTALL_DIRECTORY/.updating
                exit 0
            else
                printf "Error: No git repository found. Update stopped.\n\n"
                echo '0' > $INSTALL_DIRECTORY/.updating
                exit 1
            fi
        else
            printf "Your version of eSmart is already the latest version.\n\n"
            echo "1" > $INSTALL_DIRECTORY/.updating
            exit 0
        fi
    ;;
    'upgrade-packages')
        printf "#### Installing prerequisite apt packages.\n"
        apt-get update -y
        apt-get install -y libav-tools libffi-dev libi2c-dev python-dev python-setuptools python-smbus sqlite3
        easy_install pip
    ;;
    'initialize')
        useradd -M esmart
        adduser esmart gpio
        adduser esmart adm
        adduser esmart video

        if [ ! -e $INSTALL_DIRECTORY/.updating ]; then
            echo '0' > $INSTALL_DIRECTORY/.updating
        fi
        chown -LR esmart.esmart $INSTALL_DIRECTORY
        ln -sf $INSTALL_DIRECTORY/ /var/www/esmart

        mkdir -p /var/log/esmart

        if [ ! -e /var/log/esmart/esmart.log ]; then
            touch /var/log/esmart/esmart.log
        fi
        
        if [ ! -e /var/log/esmart/esmartupdate.log ]; then
            touch /var/log/esmart/esmartupdate.log
        fi

        if [ ! -e /var/log/esmart/esmartrestore.log ]; then
            touch /var/log/esmart/esmartrestore.log
        fi

        if [ ! -e /var/log/esmart/login.log ]; then
            touch /var/log/esmart/login.log
        fi

        chown -R esmart.esmart /var/log/esmart

        find $INSTALL_DIRECTORY/ -type d -exec chmod u+wx,g+wx {} +
        find $INSTALL_DIRECTORY/ -type f -exec chmod u+w,g+w,o+r {} +
        # find $INSTALL_DIRECTORY/esmart -type f -name '.?*' -prune -o -exec chmod 770 {} +
        chown root:esmart $INSTALL_DIRECTORY/esmart/scripts/esmart_wrapper
        chmod 4770 $INSTALL_DIRECTORY/esmart/scripts/esmart_wrapper
    ;;
esac

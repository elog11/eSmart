#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#  init_databases.py - Create and update eSmart SQLite databases
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

import argparse
import getpass
import os
import sys

import sqlalchemy

from esmart.config import SQL_DATABASE_USER, SQL_DATABASE_NOTE, SQL_DATABASE_ESMART
from esmart.databases.users_db.models import Users
from esmart.databases.utils import session_scope
from esmart.scripts.utils import test_username, test_password, is_email, query_yes_no

if sys.version[0] == "3":
    raw_input = input  # Make sure this works in PY3

USER_DB_PATH = 'sqlite:///' + SQL_DATABASE_USER
ESMART_DB_PATH = 'sqlite:///' + SQL_DATABASE_ESMART
NOTES_DB_PATH = 'sqlite:///' + SQL_DATABASE_NOTE


def add_user(admin=False):
    new_user = Users()

    print('\nAdd user to database')

    while True:
        user_name = raw_input('User (a-z, A-Z, 2-64 chars): ')
        if test_username(user_name):
            new_user.user_name = user_name
            break

    while True:
        user_password = getpass.getpass('Password: ')
        user_password_again = getpass.getpass('Password (again): ')
        if user_password != user_password_again:
            print("Passwords don't match")
        else:
            if test_password(user_password):
                new_user.set_password(user_password)
                break

    while True:
        user_email = raw_input('Email: ')
        if is_email(user_email):
            new_user.user_email = user_email
            break

    if admin:
        new_user.user_restriction = 'admin'
    else:
        new_user.user_restriction = 'guest'

    new_user.user_theme = 'dark'
    try:
        with session_scope(USER_DB_PATH) as db_session:
            db_session.add(new_user)
        sys.exit(0)
    except sqlalchemy.exc.OperationalError:
        print("Failed to create user.  You most likely need to "
              "create the DB before trying to create users.")
        sys.exit(1)
    except sqlalchemy.exc.IntegrityError:
        print("Username already exists.")
        sys.exit(1)


def delete_user(username):
    if query_yes_no("Confirm delete user '{}' from user database.".format(username)):
        try:
            with session_scope(USER_DB_PATH) as db_session:
                user = db_session.query(Users).filter(Users.user_name == username).one()
                db_session.delete(user)
                print("User deleted.")
                sys.exit(0)
        except sqlalchemy.orm.exc.NoResultFound:
            print("No user found with this name.")
            sys.exit(1)


def change_password(username):
    print('Changing password for {}'.format(username))

    with session_scope(USER_DB_PATH) as db_session:
        user = db_session.query(Users).filter(Users.user_name == username).one()

        while True:
            user_password = getpass.getpass('Password: ')
            user_password_again = getpass.getpass('Password (again): ')
            if user_password != user_password_again:
                print("Passwords don't match")
            else:
                try:
                    if test_password(user_password):
                        user.set_password(user_password)
                        sys.exit(0)
                except sqlalchemy.orm.exc.NoResultFound:
                    print("No user found with this name.")
                    sys.exit(1)


def create_dbs(db_name, create_all=False):
    if not os.path.exists(os.path.dirname(SQL_DATABASE_USER)):
        try:
            os.makedirs(os.path.dirname(SQL_DATABASE_USER))
        except OSError as exc: # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise

    if db_name == 'esmart' or create_all:
        print("Creating/verifying {} at {} ...".format(db_name, ESMART_DB_PATH))

        from esmart.databases.esmart_db import init_db
        from esmart.databases.esmart_db import populate_db
        init_db(ESMART_DB_PATH)
        populate_db(ESMART_DB_PATH)

    if db_name == 'notes' or create_all:
        print("Creating/verifying {} at {} ...".format(db_name, NOTES_DB_PATH))

        from esmart.databases.notes_db import init_db
        init_db(NOTES_DB_PATH)

    if db_name == 'users' or create_all:
        print("Creating/verifying {} at {} ...".format(db_name, USER_DB_PATH))

        from esmart.databases.users_db import init_db
        init_db(USER_DB_PATH)
    sys.exit(0)


def menu():
    parser = argparse.ArgumentParser(description="Initialize eSmart Database "
                                                 "structure and manage users")

    parser.add_argument('-i', '--install_db', type=str,
                        choices=['users', 'esmart', 'notes', 'all'],
                        help="Create new users.db, esmart.db and/or note.db")

    parser.add_argument('-A', '--addadmin', action='store_true',
                        help="Add admin user to users database")

    parser.add_argument('-a', '--adduser', action='store_true',
                        help="Add user to users database")

    parser.add_argument('-d', '--deleteuser',
                        help="Remove user from users database")

    parser.add_argument('-p', '--pwchange',
                        help="Create a new password for user")

    args = parser.parse_args()

    if args.adduser:
        add_user()

    if args.addadmin:
        add_user(admin=True)

    if args.install_db:
        if args.install_db == 'all':
            create_dbs('', create_all=True)
        else:
            create_dbs(args.install_db)

    if args.deleteuser:
        delete_user(args.deleteuser)

    if args.pwchange:
        change_password(args.pwchange)


if __name__ == "__main__":
    menu()

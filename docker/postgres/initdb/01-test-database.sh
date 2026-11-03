#!/bin/sh
# Runs once, when the data volume is first created: a separate database for the backend test suite.
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
    CREATE DATABASE ${POSTGRES_DB}_test OWNER $POSTGRES_USER ENCODING 'UTF8';
SQL

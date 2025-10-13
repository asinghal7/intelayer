#!/bin/bash
set -e

# Create the intelayer_meta database for Metabase
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE intelayer_meta;
    GRANT ALL PRIVILEGES ON DATABASE intelayer_meta TO inteluser;
EOSQL

echo "Database intelayer_meta created successfully"


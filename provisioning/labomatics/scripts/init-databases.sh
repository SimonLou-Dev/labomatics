#!/bin/bash
# Initialiser les 3 bases de données PostgreSQL pour labomatics

set -e

LABOMATICS_DB_PASSWORD="${LABOMATICS_DB_PASSWORD:-$(openssl rand -base64 16)}"
KEYCLOAK_DB_PASSWORD="${KEYCLOAK_DB_PASSWORD:-$(openssl rand -base64 16)}"
POWERDNS_DB_PASSWORD="${POWERDNS_DB_PASSWORD:-$(openssl rand -base64 16)}"

echo "Initializing labomatics databases..."

# DB labomatics
psql -v ON_ERROR_STOP=1 <<-EOSQL
    CREATE USER labomatics WITH PASSWORD '$LABOMATICS_DB_PASSWORD';
    CREATE DATABASE labomatics OWNER labomatics;
    GRANT ALL PRIVILEGES ON DATABASE labomatics TO labomatics;
EOSQL

# DB keycloak
psql -v ON_ERROR_STOP=1 <<-EOSQL
    CREATE USER keycloak WITH PASSWORD '$KEYCLOAK_DB_PASSWORD';
    CREATE DATABASE keycloak OWNER keycloak;
    GRANT ALL PRIVILEGES ON DATABASE keycloak TO keycloak;
EOSQL

# DB powerdns
psql -v ON_ERROR_STOP=1 <<-EOSQL
    CREATE USER powerdns WITH PASSWORD '$POWERDNS_DB_PASSWORD';
    CREATE DATABASE powerdns OWNER powerdns;
    GRANT ALL PRIVILEGES ON DATABASE powerdns TO powerdns;
EOSQL

echo "Databases initialized"

#!/bin/bash
# Initialize databases and users for labomatics stack

set -e

# Attendre que postgres soit prêt
until pg_isready -U postgres; do
  echo "Waiting for postgres..."
  sleep 1
done

echo "Creating labomatics database and user..."
psql -U postgres <<EOF
-- labomatics database
CREATE DATABASE labomatics;
CREATE USER labomatics WITH PASSWORD '{{ LABOMATICS_DB_PASSWORD }}';
GRANT ALL PRIVILEGES ON DATABASE labomatics TO labomatics;
ALTER USER labomatics CREATEDB;

-- keycloak database
CREATE DATABASE keycloak;
CREATE USER keycloak WITH PASSWORD '{{ KEYCLOAK_DB_PASSWORD }}';
GRANT ALL PRIVILEGES ON DATABASE keycloak TO keycloak;
ALTER USER keycloak CREATEDB;
EOF

echo "Granting schema permissions..."
psql -U postgres labomatics <<EOF
GRANT ALL PRIVILEGES ON SCHEMA public TO labomatics;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO labomatics;
ALTER DEFAULT PRIVILEGES FOR USER postgres IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO labomatics;
EOF

psql -U postgres keycloak <<EOF
GRANT ALL PRIVILEGES ON SCHEMA public TO keycloak;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO keycloak;
ALTER DEFAULT PRIVILEGES FOR USER postgres IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO keycloak;
EOF

echo "Databases initialized successfully"

#!/bin/sh
# Cloud-init pour Alpine VM centrale labomatics
# Services: Docker, Keycloak, RADIUS, PostgreSQL, Traefik, DNS

set -e

echo "=== labomatics bootstrap ==="

# Variables (injectées par le CLI)
HOSTNAME="${LABOMATICS_HOSTNAME:-labomatics}"
DOMAIN="${LABOMATICS_DOMAIN:-lab.local}"
POSTGRES_PASSWORD="${LABOMATICS_POSTGRES_PASSWORD:-$(openssl rand -base64 16)}"
KEYCLOAK_PASSWORD="${LABOMATICS_KEYCLOAK_PASSWORD:-$(openssl rand -base64 16)}"

# Idempotent check
if [ -f /etc/labomatics-provisioned ]; then
  echo "Already provisioned, exiting"
  exit 0
fi

echo "Starting provisioning..."

# Update system
apk update
apk add --no-cache docker docker-compose curl openssl ca-certificates

# Enable Docker
rc-update add docker default
rc-service docker start

# Create directories
mkdir -p /opt/labomatics/{data,config,certs}
mkdir -p /opt/labomatics/data/{postgres,keycloak,radius}

# Generate self-signed certs for Traefik
openssl req -x509 -newkey rsa:2048 -keyout /opt/labomatics/certs/key.pem -out /opt/labomatics/certs/cert.pem \
  -days 365 -nodes -subj "/CN=${HOSTNAME}.${DOMAIN}" 2>/dev/null || true

# Create docker-compose.yml
cat > /opt/labomatics/docker-compose.yml <<'COMPOSE_EOF'
version: '3.8'

services:
  # PostgreSQL database
  postgres:
    image: postgres:15-alpine
    container_name: labomatics-postgres
    environment:
      POSTGRES_USER: labomatics
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: labomatics
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - labomatics
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U labomatics"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Keycloak - Identity & Access Management
  keycloak:
    image: quay.io/keycloak/keycloak:latest
    container_name: labomatics-keycloak
    environment:
      KC_DB: postgres
      KC_DB_URL: jdbc:postgresql://postgres:5432/labomatics
      KC_DB_USERNAME: labomatics
      KC_DB_PASSWORD: ${POSTGRES_PASSWORD}
      KEYCLOAK_ADMIN: admin
      KEYCLOAK_ADMIN_PASSWORD: ${KEYCLOAK_PASSWORD}
      KC_PROXY: edge
      KC_HOSTNAME_STRICT: false
    command:
      - start
      - --optimized
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - keycloak_data:/opt/keycloak/data
    networks:
      - labomatics
    labels:
      traefik.enable: "true"
      traefik.http.routers.keycloak.rule: Host(`keycloak.lab.local`)
      traefik.http.services.keycloak.loadbalancer.server.port: "8080"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health/ready"]
      interval: 30s
      timeout: 10s
      retries: 3

  # FreeRADIUS - Authentication server
  radius:
    image: alpine:latest
    container_name: labomatics-radius
    command: sh -c "apk add --no-cache freeradius freeradius-client && radiusd -f"
    volumes:
      - ./config/radius:/etc/raddb
      - radius_data:/var/lib/freeradius
    networks:
      - labomatics
    ports:
      - "1812:1812/udp"
      - "1813:1813/udp"
    depends_on:
      - postgres

  # DNS server (dnsmasq)
  dns:
    image: jpillora/dnsmasq:latest
    container_name: labomatics-dns
    volumes:
      - ./config/dnsmasq.conf:/etc/dnsmasq.conf:ro
    networks:
      - labomatics
    ports:
      - "53:53/udp"
      - "53:53/tcp"

  # Traefik - Reverse Proxy
  traefik:
    image: traefik:v3.0
    container_name: labomatics-traefik
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./certs:/etc/traefik/certs:ro
    networks:
      - labomatics

volumes:
  postgres_data:
  keycloak_data:
  radius_data:

networks:
  labomatics:
    driver: bridge
COMPOSE_EOF

# Create dnsmasq config
mkdir -p /opt/labomatics/config
cat > /opt/labomatics/config/dnsmasq.conf <<'DNS_EOF'
domain-needed
bogus-priv
no-resolv
address=/lab.local/127.0.0.1
address=/keycloak.lab.local/127.0.0.1
cache-size=1000
DNS_EOF

# Export variables for docker-compose
export POSTGRES_PASSWORD
export KEYCLOAK_PASSWORD

# Start services
cd /opt/labomatics
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
for i in {1..30}; do
  if docker exec labomatics-keycloak curl -s http://localhost:8080/health/ready > /dev/null 2>&1; then
    echo "✓ Services ready"
    break
  fi
  echo "Waiting... ($i/30)"
  sleep 2
done

# Mark provisioning complete
touch /etc/labomatics-provisioned

# Output credentials
echo ""
echo "=== labomatics provisioning complete ==="
echo "Keycloak: https://keycloak.lab.local"
echo "Admin user: admin"
echo "Admin password: ${KEYCLOAK_PASSWORD}"
echo "PostgreSQL password: ${POSTGRES_PASSWORD}"
echo ""
echo "Save these credentials securely!"

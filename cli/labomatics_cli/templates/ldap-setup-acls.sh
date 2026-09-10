#!/bin/bash
# Setup LDAP ACLs for keycloak-bind to create users

set -e

echo "Waiting for LDAP to be ready..."
for i in {1..30}; do
  if ldapsearch -x -H ldap://ldap:389 -D "cn=admin,${LDAP_INIT_ORG_DN}" -w "${LDAP_INIT_ROOT_USER_PW}" -b "${LDAP_INIT_ORG_DN}" -s base >/dev/null 2>&1; then
    echo "✓ LDAP is ready"
    break
  fi
  echo "  Waiting... ($i/30)"
  sleep 1
done

LDAP_CONFIG_DN="cn=admin,cn=config"
KEYCLOAK_BIND_DN="cn=keycloak-bind,ou=svcaccounts,${LDAP_INIT_ORG_DN}"

echo "Setting up LDAP ACLs for keycloak-bind..."
echo "  Config DN: $LDAP_CONFIG_DN"
echo "  Keycloak Bind DN: $KEYCLOAK_BIND_DN"

# Allow keycloak-bind to read and write users under ou=users
ldapmodify -H ldap://ldap:389 -D "$LDAP_CONFIG_DN" -w "$LDAP_INIT_ROOT_USER_PW" <<EOF
dn: olcDatabase={1}mdb,cn=config
changetype: modify
add: olcAccess
olcAccess: {0}to dn.subtree="ou=users,${LDAP_INIT_ORG_DN}" by dn="$KEYCLOAK_BIND_DN" write by self write by * read
olcAccess: {1}to dn.subtree="ou=groups,${LDAP_INIT_ORG_DN}" by dn="$KEYCLOAK_BIND_DN" write by self write by * read
EOF

echo "✓ LDAP ACLs configured successfully"

"""Représentation Keycloak de la fédération LDAP et de ses mappers."""

from __future__ import annotations

from typing import Any

from labomatics_cli.installer.directory import DirectoryInfo

FEDERATION_NAME = "ldap-labomatics"
FEDERATION_TYPE = "org.keycloak.storage.UserStorageProvider"
MAPPER_TYPE = "org.keycloak.storage.ldap.mappers.LDAPStorageMapper"
CHANGED_SYNC_SECONDS = "300"
SYNC_DISABLED = "-1"


def _values(config: dict[str, Any]) -> dict[str, list[str]]:
    """Convertit une configuration en valeurs de liste, format imposé par Keycloak.

    Args:
        config: Paramètres à valeur simple (chaîne ou booléen).

    Returns:
        Les mêmes paramètres, chaque valeur étant une liste d'une chaîne.
    """
    out: dict[str, list[str]] = {}
    for key, value in config.items():
        text = str(value).lower() if isinstance(value, bool) else str(value)
        out[key] = [text]
    return out


class LdapFederation:
    """Construit la configuration de la fédération LDAP : identique en local et en externe."""

    def __init__(self, info: DirectoryInfo) -> None:
        """Initialise le constructeur.

        Args:
            info: Paramètres de l'annuaire.
        """
        self.info = info

    def provider(self, realm_id: str) -> dict[str, Any]:
        """Composant « User Federation » du realm.

        Args:
            realm_id: Identifiant interne du realm (parent du composant).

        Returns:
            La représentation Keycloak du composant.
        """
        info = self.info
        sync = CHANGED_SYNC_SECONDS if info.periodic_sync else SYNC_DISABLED
        config = {
            "enabled": True,
            "vendor": "other",
            "connectionUrl": info.url,
            "bindDn": info.bind_dn,
            "bindCredential": info.bind_password,
            "startTls": info.starttls,
            "useTruststoreSpi": "always",
            "connectionPooling": False,
            "authType": "simple",
            "usersDn": f"ou=users,{info.base_dn}",
            "usernameLDAPAttribute": "uid",
            "rdnLDAPAttribute": "uid",
            "uuidLDAPAttribute": info.uuid_attr,
            "userObjectClasses": "inetOrgPerson, organizationalPerson, person",
            "editMode": "WRITABLE",
            "pagination": True,
            "batchSizeForSync": "1000",
            "importEnabled": True,
            "syncRegistrations": True,
            "cachePolicy": "DEFAULT",
            "validatePasswordPolicy": False,
            "trustEmail": False,
            "fullSyncPeriod": SYNC_DISABLED,
            "changedSyncPeriod": sync,
        }
        return {
            "name": FEDERATION_NAME,
            "providerId": "ldap",
            "providerType": FEDERATION_TYPE,
            "parentId": realm_id,
            "config": _values(config),
        }

    def mappers(self, provider_id: str) -> list[dict[str, Any]]:
        """Mappers attributs, nom complet et groupes.

        Args:
            provider_id: Identifiant du composant de fédération (parent des mappers).

        Returns:
            Les représentations Keycloak, à créer ou mettre à jour par nom.
        """
        base = self.info.base_dn
        attributes = [
            ("username", "username", "uid"),
            ("first name", "firstName", "givenName"),
            ("last name", "lastName", "sn"),
        ]
        mappers = [
            self._mapper(
                provider_id,
                name,
                "user-attribute-ldap-mapper",
                {
                    "user.model.attribute": model,
                    "ldap.attribute": ldap,
                    "read.only": False,
                    "always.read.value.from.ldap": False,
                    "is.mandatory.in.ldap": True,
                },
            )
            for name, model, ldap in attributes
        ]
        mappers.append(
            self._mapper(
                provider_id,
                "full name",
                "full-name-ldap-mapper",
                {
                    "ldap.full.name.attribute": "cn",
                    "read.only": False,
                    "write.only": True,
                },
            )
        )
        mappers.append(
            self._mapper(
                provider_id,
                "groups",
                "group-ldap-mapper",
                {
                    "groups.dn": f"ou=groups,{base}",
                    "group.name.ldap.attribute": "cn",
                    "group.object.classes": "groupOfNames",
                    "membership.ldap.attribute": "member",
                    "membership.attribute.type": "DN",
                    "membership.user.ldap.attribute": "uid",
                    "mode": "LDAP_ONLY",
                    "user.roles.retrieve.strategy": "LOAD_GROUPS_BY_MEMBER_ATTRIBUTE",
                    "preserve.group.inheritance": True,
                    "ignore.missing.groups": False,
                    "drop.non.existing.groups.during.sync": False,
                    "groups.path": "/",
                },
            )
        )
        return mappers

    @staticmethod
    def _mapper(
        provider_id: str, name: str, kind: str, config: dict[str, Any]
    ) -> dict[str, Any]:
        """Construit un mapper LDAP.

        Args:
            provider_id: Composant de fédération parent.
            name: Nom du mapper.
            kind: Identifiant du type de mapper Keycloak.
            config: Paramètres du mapper.

        Returns:
            La représentation Keycloak du mapper.
        """
        return {
            "name": name,
            "providerId": kind,
            "providerType": MAPPER_TYPE,
            "parentId": provider_id,
            "config": _values(config),
        }

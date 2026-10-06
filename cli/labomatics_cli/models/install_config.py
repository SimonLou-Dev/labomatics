import unicodedata
from enum import Enum
from typing import Any, Mapping, Optional

from pydantic import BaseModel, ValidationError, model_validator

SCHEMA_VERSION = 1


class ProxmoxSection(BaseModel):
    """Page « Proxmox » : connexion à l'API du cluster."""

    cluster_name: str
    url: str
    user: str
    token_id: str
    token_secret: str


class VmSection(BaseModel):
    """Page « VM Labomatics » : réseau d'administration et paramètres de la VM."""

    domain: str
    admin_iface: str
    admin_network: str
    admin_gateway: str
    vm_ip: str
    dns_upstream: list[str]
    ssh_keys: list[str] = []
    name: str = "labomatics"
    memory: int = 8192
    cores: int = 4
    node: Optional[str] = None
    timezone: str = "Europe/Paris"


class WanSection(BaseModel):
    """Page « Labs : WAN » : réseau des routeurs étudiants."""

    iface: str
    network: str
    gateway: str
    exclusions: list[str] = []
    name: Optional[str] = None


class VxlanSection(BaseModel):
    """Page « Labs : VXLAN » : zone SDN et réseau découpé en /24."""

    zone: str = "labo"
    network: str = "10.96.0.0/12"
    storage: str
    vni_min: int = 1000
    vni_max: int = 4000
    vni_exclusions: list[str] = []
    mtu: int = 1350
    vnet_name: Optional[str] = None


class AdminSection(BaseModel):
    """Page « Compte d'administration » : premier administrateur Keycloak."""

    email: str
    first_name: str
    last_name: str

    @property
    def username(self) -> str:
        """Identifiant de connexion calculé à partir du prénom et du nom.

        Returns:
            « prenom.nom » en minuscules, sans accents, espaces remplacés par « - ».
        """

        def clean(value: str) -> str:
            """Normalise une partie du nom pour un identifiant.

            Args:
                value: Prénom ou nom saisi.

            Returns:
                La valeur en minuscules, sans accents, espaces remplacés par « - ».
            """
            decomposed = unicodedata.normalize("NFKD", value)
            ascii_only = "".join(c for c in decomposed if not unicodedata.combining(c))
            return "-".join(ascii_only.lower().split())

        return f"{clean(self.first_name)}.{clean(self.last_name)}"


class DirectoryMode(str, Enum):
    """Type d'annuaire choisi à la page « Authentification »."""

    none = "none"
    local = "local"
    external = "external"


class AuthSection(BaseModel):
    """Page « Authentification » : annuaire et RADIUS."""

    directory: DirectoryMode = DirectoryMode.local
    radius: bool = False


class LdapSection(BaseModel):
    """Page « Fédération LDAP externe » : connexion à l'annuaire existant."""

    url: str
    starttls: bool = False
    base_dn: str
    bind_dn: str
    bind_password: str
    uuid_attr: str = "entryUUID"
    periodic_sync: bool = False


class ProxySection(BaseModel):
    """Page « Reverse proxy » : proxies amont de confiance."""

    trusted_hosts: list[str] = []


class MailSection(BaseModel):
    """Page « E-mail » : Brevo pour le backend, SMTP pour Keycloak."""

    enabled: bool = True
    brevo_api_key: str = ""
    from_email: str = ""
    from_name: str = "Labomatics"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True


class NodeAccess(BaseModel):
    """Accès SSH à un nœud Proxmox (propagation des CA)."""

    user: str = "root"
    password: str
    host: Optional[str] = None


SECTIONS: dict[str, type[BaseModel]] = {
    "proxmox": ProxmoxSection,
    "vm": VmSection,
    "wan": WanSection,
    "vxlan": VxlanSection,
    "admin": AdminSection,
    "auth": AuthSection,
    "ldap": LdapSection,
    "proxy": ProxySection,
    "mail": MailSection,
}


def _try_build(model: type[BaseModel], data: dict[str, Any]) -> Optional[Any]:
    """Construit un modèle s'il est complet.

    Args:
        model: Classe pydantic à instancier.
        data: Valeurs des champs.

    Returns:
        L'instance validée, ou None si un champ requis manque ou est invalide.
    """
    try:
        return model.model_validate(data)
    except ValidationError:
        return None


class InstallConfig(BaseModel):
    """Réponses du wizard d'installation, une section par page (None tant que non validée)."""

    version: int = SCHEMA_VERSION
    proxmox: Optional[ProxmoxSection] = None
    vm: Optional[VmSection] = None
    wan: Optional[WanSection] = None
    vxlan: Optional[VxlanSection] = None
    admin: Optional[AdminSection] = None
    auth: Optional[AuthSection] = None
    ldap: Optional[LdapSection] = None
    proxy: Optional[ProxySection] = None
    mail: Optional[MailSection] = None
    nodes: dict[str, NodeAccess] = {}

    @model_validator(mode="after")
    def _derive_logical_names(self) -> "InstallConfig":
        """Donne par défaut le nom du cluster aux noms logiques WAN et VNet.

        Returns:
            La configuration, avec `wan.name` et `vxlan.vnet_name` renseignés si possible.
        """
        if self.proxmox is not None:
            if self.wan is not None and not self.wan.name:
                self.wan.name = self.proxmox.cluster_name
            if self.vxlan is not None and not self.vxlan.vnet_name:
                self.vxlan.vnet_name = self.proxmox.cluster_name
        return self

    def to_flat(self) -> dict[str, Any]:
        """Aplatit la configuration en clés « section.champ » pour le wizard.

        Returns:
            Les valeurs des sections renseignées, nœuds en « nodes.<nœud>.<champ> ».
        """
        flat: dict[str, Any] = {}
        for name in SECTIONS:
            section = getattr(self, name)
            if section is not None:
                for field, value in section.model_dump(mode="json").items():
                    flat[f"{name}.{field}"] = value
        for node, access in self.nodes.items():
            for field, value in access.model_dump(mode="json").items():
                flat[f"nodes.{node}.{field}"] = value
        return flat

    def merge_flat(
        self, values: Mapping[str, Any], section: Optional[str] = None
    ) -> "InstallConfig":
        """Fusionne des valeurs plates du wizard dans une nouvelle configuration.

        Une section incomplète (champ requis manquant) est ignorée.

        Args:
            values: Valeurs à clés « section.champ » ou « nodes.<nœud>.<champ> ».
            section: Si fourni, seules les clés de cette section sont appliquées.

        Returns:
            Une nouvelle configuration validée ; l'instance courante n'est pas modifiée.
        """
        incoming: dict[str, dict[str, Any]] = {}
        node_incoming: dict[str, dict[str, Any]] = {}
        for key, value in values.items():
            head, _, rest = key.partition(".")
            if section is not None and head != section:
                continue
            if head == "nodes" and "." in rest:
                node, _, field = rest.rpartition(".")
                node_incoming.setdefault(node, {})[field] = value
            elif head in SECTIONS and rest:
                incoming.setdefault(head, {})[rest] = value

        updates: dict[str, Any] = {}
        for name, fields in incoming.items():
            current = getattr(self, name)
            base = current.model_dump() if current is not None else {}
            built = _try_build(SECTIONS[name], {**base, **fields})
            if built is not None:
                updates[name] = built

        nodes = dict(self.nodes)
        for node, fields in node_incoming.items():
            existing = nodes.get(node)
            base = existing.model_dump() if existing is not None else {}
            built = _try_build(NodeAccess, {**base, **fields})
            if built is not None:
                nodes[node] = built
        updates["nodes"] = nodes
        merged = self.model_copy(update=updates)
        return InstallConfig.model_validate(merged.model_dump())

    def locked_keys(self) -> set[str]:
        """Clés déjà présentes dans la configuration, verrouillées en mode édition.

        Returns:
            L'ensemble des clés plates renseignées.
        """
        return set(self.to_flat())

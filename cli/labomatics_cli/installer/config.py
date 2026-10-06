import unicodedata
from enum import Enum
from typing import Any, Mapping, Optional

from pydantic import BaseModel, ValidationError


class ProxmoxSection(BaseModel):
    cluster_name: str
    url: str
    user: str
    token_id: str
    token_secret: str


class VmSection(BaseModel):
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


class WanSection(BaseModel):
    iface: str
    network: str
    gateway: str
    exclusions: list[str] = []


class VxlanSection(BaseModel):
    zone: str = "labo"
    network: str = "10.96.0.0/12"
    storage: str
    vni_min: int = 1000
    vni_max: int = 4000
    mtu: int = 1350


class AdminSection(BaseModel):
    email: str
    first_name: str
    last_name: str

    @property
    def username(self) -> str:
        def clean(value: str) -> str:
            decomposed = unicodedata.normalize("NFKD", value)
            ascii_only = "".join(c for c in decomposed if not unicodedata.combining(c))
            return "-".join(ascii_only.lower().split())

        return f"{clean(self.first_name)}.{clean(self.last_name)}"


class DirectoryMode(str, Enum):
    none = "none"
    local = "local"
    external = "external"


class AuthSection(BaseModel):
    directory: DirectoryMode = DirectoryMode.local
    radius: bool = False


class LdapSection(BaseModel):
    url: str
    starttls: bool = False
    base_dn: str
    bind_dn: str
    bind_password: str
    uuid_attr: str = "entryUUID"
    periodic_sync: bool = False


class ProxySection(BaseModel):
    trusted_hosts: list[str] = []


class MailSection(BaseModel):
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
    user: str = "root"
    password: str


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
    try:
        return model.model_validate(data)
    except ValidationError:
        return None


class InstallConfig(BaseModel):
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

    def to_flat(self) -> dict[str, Any]:
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
        """Fusionne les valeurs; une section incomplète (champ requis manquant) est ignorée."""
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
        return self.model_copy(update=updates)

    def locked_keys(self) -> set[str]:
        return set(self.to_flat())

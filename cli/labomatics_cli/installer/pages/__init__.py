"""Pages du wizard `labomatics install`, dans l'ordre d'affichage."""

from labomatics_cli.installer.pages.admin import AdminPage
from labomatics_cli.installer.pages.auth import AuthPage, LdapPage
from labomatics_cli.installer.pages.base import Page
from labomatics_cli.installer.pages.cluster import NEW_CLUSTER, ClusterChoice
from labomatics_cli.installer.pages.mail import MailPage
from labomatics_cli.installer.pages.nodes import NodesPage
from labomatics_cli.installer.pages.proxmox import ProxmoxPage
from labomatics_cli.installer.pages.proxy import ProxyPage
from labomatics_cli.installer.pages.vm import VmPage
from labomatics_cli.installer.pages.vxlan import VxlanPage
from labomatics_cli.installer.pages.wan import WanPage

PAGE_CLASSES: tuple[type[Page], ...] = (
    ProxmoxPage,
    VmPage,
    WanPage,
    VxlanPage,
    AdminPage,
    AuthPage,
    LdapPage,
    ProxyPage,
    MailPage,
    NodesPage,
)

PAGE_SECTIONS: dict[str, str] = {cls.title: cls.section for cls in PAGE_CLASSES}

__all__ = [
    "AdminPage",
    "AuthPage",
    "ClusterChoice",
    "LdapPage",
    "MailPage",
    "NEW_CLUSTER",
    "NodesPage",
    "PAGE_CLASSES",
    "PAGE_SECTIONS",
    "Page",
    "ProxmoxPage",
    "ProxyPage",
    "VmPage",
    "VxlanPage",
    "WanPage",
]

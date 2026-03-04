"""Re-export de toutes les commandes CLI."""

from .apply import cmd_apply, cmd_diff
from .build_template import cmd_build_template
from .creds import cmd_credentials
from .find import cmd_find
from .init import cmd_init
from .inspect import cmd_pools, cmd_vnets, cmd_vms, cmd_zones
from .ips import cmd_ips
from .recreate import cmd_recreate
from .status import cmd_status

__all__ = [
    "cmd_apply",
    "cmd_diff",
    "cmd_pools",
    "cmd_zones",
    "cmd_vnets",
    "cmd_vms",
    "cmd_find",
    "cmd_credentials",
    "cmd_ips",
    "cmd_status",
    "cmd_recreate",
    "cmd_build_template",
    "cmd_init",
]

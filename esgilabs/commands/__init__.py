"""
Package ``esgilabs.commands`` — implémentation des sous-commandes CLI.

Chaque module correspond à une ou plusieurs commandes :

- :mod:`.apply`   — ``apply``, ``diff``
- :mod:`.inspect` — ``pools``, ``zones``, ``vnets``, ``vms``
- :mod:`.find`    — ``find``
- :mod:`.creds`   — ``credentials``

Les helpers partagés (connexion, chargement CSV, confirmation) sont dans
:mod:`._helpers`.
"""

from .apply import cmd_apply, cmd_diff
from .inspect import cmd_pools, cmd_zones, cmd_vnets, cmd_vms
from .find import cmd_find
from .creds import cmd_credentials

__all__ = [
    "cmd_apply",
    "cmd_diff",
    "cmd_pools",
    "cmd_zones",
    "cmd_vnets",
    "cmd_vms",
    "cmd_find",
    "cmd_credentials",
]

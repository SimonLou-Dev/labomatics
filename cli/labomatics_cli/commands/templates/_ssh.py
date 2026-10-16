"""Options SSH partagées pour les commandes `template` (build-openwrt + VM templates).

Module séparé pour éviter un import circulaire entre `build_openwrt.py` et
`orchestrator.py`, qui s'importent déjà l'un l'autre.
"""

from __future__ import annotations

from ...installer.ssh import CliKey

# Clé dédiée du CLI, déployée sur les nœuds par `labomatics install` (pas la
# clé personnelle de l'opérateur : voir `installer.ssh.CliKey`).
SSH_OPTS = [
    "-i",
    str(CliKey().path),
    "-o",
    "StrictHostKeyChecking=no",
    "-o",
    "ConnectTimeout=10",
]

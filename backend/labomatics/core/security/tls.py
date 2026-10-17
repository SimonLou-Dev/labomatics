"""Résolution de la vérification TLS pour les clients HTTP sortants."""

from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import gettempdir

from labomatics.core.config.settings import settings

_CA_CACHE_DIR = Path(gettempdir()) / "labomatics-cluster-ca"


def resolve_verify(ca_cert: str | None) -> str | bool:
    """Détermine la valeur `verify=` à utiliser pour un cluster Proxmox donné.

    Chaque cluster Proxmox a sa propre CA auto-signée (`/etc/pve/pve-root-ca.pem`),
    indépendante de la CA interne Labomatics référencée par `CA_BUNDLE`. Si une CA
    de cluster est fournie, elle est écrite sur disque (cache par contenu) pour
    être passée telle quelle à `httpx`/`requests`, qui n'acceptent qu'un chemin.

    Args:
        ca_cert: CA (PEM) propre au cluster, ou `None` pour retomber sur `CA_BUNDLE`.

    Returns:
        Un chemin de CA bundle, ou `settings.tls_verify` si `ca_cert` est `None`.
    """
    if not ca_cert:
        return settings.tls_verify

    _CA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(ca_cert.encode()).hexdigest()
    path = _CA_CACHE_DIR / f"{digest}.pem"
    if not path.exists():
        path.write_text(ca_cert)
    return str(path)

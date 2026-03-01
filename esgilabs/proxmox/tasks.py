#!/usr/bin/env python3
"""
Attente des tâches asynchrones Proxmox.

Proxmox exécute la plupart des opérations lourdes (clone, delete, stop…)
de manière asynchrone et retourne immédiatement un ``task_id`` (UPID).
Ce module fournit :func:`wait_for_task` pour attendre la fin d'une tâche
avant de continuer.
"""

import time

from proxmoxer import ProxmoxAPI


def wait_for_task(
    proxmox: ProxmoxAPI,
    node: str,
    task_id: str,
    timeout: int = 300,
    poll_interval: int = 3,
) -> None:
    """Attend la fin d'une tâche Proxmox (polling toutes les *poll_interval* secondes).

    Args:
        proxmox: Client API Proxmox authentifié.
        node: Nom du nœud qui exécute la tâche.
        task_id: UPID de la tâche retourné par l'API Proxmox.
        timeout: Délai maximum d'attente en secondes (défaut : 300).
        poll_interval: Intervalle de polling en secondes (défaut : 3).

    Raises:
        RuntimeError: Si la tâche se termine avec un statut différent de ``OK``.
        TimeoutError: Si la tâche ne se termine pas avant *timeout* secondes.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = proxmox.nodes(node).tasks(task_id).status.get()
        if status["status"] == "stopped":
            if status.get("exitstatus") != "OK":
                raise RuntimeError(
                    f"Task {task_id} failed: {status.get('exitstatus')}"
                )
            return
        time.sleep(poll_interval)
    raise TimeoutError(f"Task {task_id} timeout after {timeout}s")

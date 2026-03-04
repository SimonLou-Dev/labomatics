#!/usr/bin/env python3
"""
Attente des tâches asynchrones Proxmox (polling UPID).
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
    """Attend la fin d'une tâche Proxmox.

    Args:
        proxmox: Client API Proxmox authentifié.
        node: Nœud qui exécute la tâche.
        task_id: UPID retourné par l'API.
        timeout: Délai maximum en secondes (défaut : 300).
        poll_interval: Intervalle de polling en secondes (défaut : 3).

    Raises:
        RuntimeError: Si la tâche échoue.
        TimeoutError: Si la tâche dépasse le délai.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = proxmox.nodes(node).tasks(task_id).status.get()
        if status["status"] == "stopped":
            if status.get("exitstatus") != "OK":
                raise RuntimeError(f"Task {task_id} failed: {status.get('exitstatus')}")
            return
        time.sleep(poll_interval)
    raise TimeoutError(f"Task {task_id} timeout after {timeout}s")

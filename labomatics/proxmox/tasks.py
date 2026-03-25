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
    progress_label: str | None = None,
) -> None:
    """Attend la fin d'une tâche Proxmox.

    Args:
        proxmox: Client API Proxmox authentifié.
        node: Nœud qui exécute la tâche.
        task_id: UPID retourné par l'API.
        timeout: Délai maximum en secondes (défaut : 300).
        poll_interval: Intervalle de polling en secondes (défaut : 3).
        progress_label: Si fourni, affiche la progression (dernière ligne de log + elapsed).

    Raises:
        RuntimeError: Si la tâche échoue.
        TimeoutError: Si la tâche dépasse le délai.
    """
    import sys

    start = time.time()
    deadline = start + timeout
    last_log_line = ""

    while time.time() < deadline:
        status = proxmox.nodes(node).tasks(task_id).status.get()
        if status["status"] == "stopped":
            if progress_label:
                sys.stderr.write("\r\033[K")
                sys.stderr.flush()
            if status.get("exitstatus") != "OK":
                raise RuntimeError(f"Task {task_id} failed: {status.get('exitstatus')}")
            return

        if progress_label:
            elapsed = int(time.time() - start)
            # Lire la dernière ligne du log pour afficher le contexte
            try:
                logs = proxmox.nodes(node).tasks(task_id).log.get(limit=1, start=0)
                # Proxmox retourne les lignes en ordre croissant — prendre la dernière
                lines = [e.get("t", "") for e in logs if e.get("t")]
                if lines:
                    last_log_line = lines[-1][:60]
            except Exception:
                pass
            msg = f"\r  ⏳ {progress_label} [{elapsed}s] {last_log_line}"
            sys.stderr.write(f"{msg:<100}")
            sys.stderr.flush()

        time.sleep(poll_interval)

    raise TimeoutError(f"Task {task_id} timeout after {timeout}s")

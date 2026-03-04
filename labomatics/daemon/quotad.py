#!/usr/bin/env python3
"""
labomatics-quotad — daemon de surveillance des quotas de ressources.

Fonctionnement :
  - Vérification au démarrage puis toutes les ``quotad.interval`` secondes
  - Pour chaque pool géré, lit les ressources CPU/RAM/disk des VMs running
  - Compare aux limites du flavor de l'étudiant
  - Si dépassement : arrête la VM qui consomme le plus de RAM (hors OpenWrt)
  - Écrit un message dans la description Proxmox de la VM arrêtée

Exclusions :
  - La VM OpenWrt de l'étudiant (vmid = vmid_start + student.id) n'est jamais arrêtée
  - Les pools sans flavor défini sont ignorés

Installation systemd :
  systemctl enable --now labomatics-quotad
"""

import logging
import signal
import time

from ..config import load_config, load_proxmox_settings
from ..credentials import _find_students_csv
from ..proxmox import (
    connect,
    get_pool_lxcs,
    get_pool_vms,
    list_managed_pools,
    wait_for_task,
)
from ..students import load_students

log = logging.getLogger("labomatics.quotad")


def _setup_logging(debug: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _get_running_resources(proxmox, pool_name: str) -> dict:
    """Retourne les ressources agrégées des VMs running dans un pool.

    Returns:
        Dict ``{cpu_cores, ram_mb, disk_gb, vms}`` où ``vms`` est la liste
        des membres running avec leurs stats.
    """
    vms = get_pool_vms(proxmox, pool_name)
    lxcs = get_pool_lxcs(proxmox, pool_name)
    all_members = vms + lxcs

    running = [m for m in all_members if m.get("status") == "running"]

    cpu_cores = sum(m.get("cpus", 0) for m in running)
    ram_mb = sum(m.get("maxmem", 0) for m in running) // (1024 * 1024)
    disk_gb = sum(m.get("disk", 0) for m in all_members) // (1024 * 1024 * 1024)

    return {
        "cpu_cores": cpu_cores,
        "ram_mb": ram_mb,
        "disk_gb": disk_gb,
        "running": running,
        "all": all_members,
    }


def _stop_highest_ram_vm(proxmox, pool_name: str, running: list[dict], openwrt_vmid: int) -> None:
    """Arrête la VM running qui consomme le plus de RAM, en excluant OpenWrt.

    Écrit un message dans la description de la VM arrêtée.

    Args:
        proxmox: Client API Proxmox.
        pool_name: Nom du pool pour les logs.
        running: Liste des membres running (avec vmid, node, maxmem).
        openwrt_vmid: VMID de la VM OpenWrt de l'étudiant (à exclure).
    """
    # Exclure OpenWrt
    candidates = [m for m in running if m.get("vmid") != openwrt_vmid]
    if not candidates:
        log.warning("[%s] Dépassement quota mais aucune VM arrêtable (uniquement OpenWrt)", pool_name)
        return

    # VM qui consomme le plus de RAM
    victim = max(candidates, key=lambda m: m.get("maxmem", 0))
    vmid = victim.get("vmid")
    node: str | None = victim.get("node")
    name = victim.get("name", str(vmid))

    if node is None:
        log.warning("[%s] VM victime %s sans nœud, impossible d'arrêter", pool_name, name)
        return

    log.warning(
        "[%s] Quota dépassé → arrêt de %s (vmid=%s, RAM=%dMB)",
        pool_name, name, vmid, victim.get("maxmem", 0) // (1024 * 1024),
    )

    try:
        # Annoter la description
        import datetime
        msg = f"[labomatics-quotad] Arrêtée automatiquement le {datetime.datetime.now():%Y-%m-%d %H:%M} — quota dépassé"
        proxmox.nodes(node).qemu(vmid).config.put(description=msg)
    except Exception:
        pass

    try:
        task = proxmox.nodes(node).qemu(vmid).status.stop.post()
        wait_for_task(proxmox, node, task, timeout=120)
        log.info("[%s] VM %s (vmid=%s) arrêtée", pool_name, name, vmid)
    except Exception as e:
        log.error("[%s] Échec arrêt VM %s : %s", pool_name, name, e)


def check_quotas(proxmox, config, student_map: dict) -> None:
    """Vérifie les quotas de tous les pools gérés et applique l'action si nécessaire."""
    pools = list_managed_pools(proxmox)

    for pool in pools:
        pool_name = pool["poolid"]
        student = student_map.get(pool_name)
        if not student or not student.flavor:
            continue

        flavor = config.get_flavor(student.flavor)
        if flavor.cpu == 0 and flavor.ram == 0 and flavor.disk == 0:
            continue  # Pas de limite définie

        res = _get_running_resources(proxmox, pool_name)
        openwrt_vmid = student.vmid(config.openwrt.vmid_start)

        violations = []
        if flavor.cpu > 0 and res["cpu_cores"] > flavor.cpu:
            violations.append(f"CPU {res['cpu_cores']}/{flavor.cpu}")
        if flavor.ram > 0 and res["ram_mb"] > flavor.ram:
            violations.append(f"RAM {res['ram_mb']}/{flavor.ram}MB")
        if flavor.disk > 0 and res["disk_gb"] > flavor.disk:
            violations.append(f"Disk {res['disk_gb']}/{flavor.disk}GB")

        if not violations:
            continue

        log.warning("[%s] Quota dépassé : %s", pool_name, ", ".join(violations))

        if config.quotad.action == "stop":
            _stop_highest_ram_vm(proxmox, pool_name, res["running"], openwrt_vmid)
        else:
            log.info("[%s] Action = alert-only, aucun arrêt", pool_name)


def run_daemon() -> None:
    """Boucle principale du daemon."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="labomatics-quotad",
        description="Daemon de surveillance des quotas labomatics",
    )
    parser.add_argument("--debug", action="store_true", help="Mode debug (logs verbeux)")
    parser.add_argument("--once", action="store_true", help="Exécuter une seule vérification et quitter")
    args = parser.parse_args()

    _setup_logging(args.debug)
    log.info("labomatics-quotad démarré")

    # Arrêt propre sur SIGTERM
    running = True

    def _handle_sigterm(signum, frame):
        nonlocal running
        log.info("SIGTERM reçu, arrêt en cours...")
        running = False

    signal.signal(signal.SIGTERM, _handle_sigterm)

    while running:
        try:
            config = load_config()
            settings = load_proxmox_settings()
            proxmox = connect(settings)

            # Construire l'index nom → étudiant
            try:
                students = load_students(_find_students_csv(config))
                student_map = {s.nom: s for s in students}
            except Exception as e:
                log.warning("Impossible de charger le CSV étudiants : %s", e)
                student_map = {}

            check_quotas(proxmox, config, student_map)

        except KeyboardInterrupt:
            break
        except Exception as e:
            log.error("Erreur lors de la vérification des quotas : %s", e)

        if args.once:
            break

        interval = 30
        try:
            config = load_config()
            interval = config.quotad.interval
        except Exception:
            pass

        log.debug("Prochaine vérification dans %ds", interval)
        # Attente interruptible (SIGTERM)
        for _ in range(interval):
            if not running:
                break
            time.sleep(1)

    log.info("labomatics-quotad arrêté")


if __name__ == "__main__":
    run_daemon()

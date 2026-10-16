"""Build de la template OpenWrt à distance, sur un nœud du cluster choisi.

Contrairement à l'ancien `OpenWRTBuilder`, qui suppose d'être exécuté en root
directement sur un nœud Proxmox (`qm`, `losetup`, `mount` locaux), cette
commande se lance depuis n'importe quelle machine : elle lit la connexion
Proxmox d'un cluster déjà configuré par `labomatics install`
(`~/.labomatics/clusters/<nom>/install.yaml`), puis exécute tout le build
(téléchargement, montage loopback, injection des fichiers,
`qm create/importdisk/template`) en une seule session SSH root sur le nœud
ciblé — qui reste, lui, le seul endroit où un accès root local est requis.
Cette session SSH utilise la clé dédiée du CLI (`installer.ssh.CliKey`),
déployée sur les nœuds par `labomatics install`.
"""

from __future__ import annotations

import base64
import os
import re
import subprocess
import urllib.request
from datetime import date
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm

from ...installer.ssh import CliKey
from ...installer.store import DEFAULT_BASE_DIR, InstallStore
from ...utils.proxmox import ProxmoxClient
from ...utils.theme import info, prompt_with_retry, step, success, title
from ._ssh import SSH_OPTS as _SSH_OPTS
from .orchestrator import _delete_existing_template

console = Console()

_TEMPLATES_ENV_VAR = "LABOMATICS_TEMPLATES_DIR"
_REPO_TEMPLATES_DIR = Path(
    os.environ.get(_TEMPLATES_ENV_VAR)
    or Path(__file__).resolve().parents[4] / "templates"
)
_OPENWRT_INIT = _REPO_TEMPLATES_DIR / "openwrt" / "OPENWRT_INIT"
_OPENWRT_RELEASES_URL = "https://downloads.openwrt.org/releases/"

DEFAULT_VMID = 90200
DEFAULT_PASSWORD = "labomatics"  # noqa: S105


def _get_latest_openwrt_version() -> str:
    """Récupère la dernière version stable d'OpenWrt depuis downloads.openwrt.org."""
    with urllib.request.urlopen(_OPENWRT_RELEASES_URL, timeout=10) as resp:
        html = resp.read().decode()
    # Dossiers de version stables (ex: 23.05.5/, 24.10.0/) — exclut snapshots/rc.
    versions = re.findall(r'href="(\d+\.\d+\.\d+)/"', html)
    if not versions:
        raise RuntimeError("Impossible de récupérer la liste des versions OpenWrt")
    return sorted(versions, key=lambda v: tuple(int(x) for x in v.split(".")))[-1]


def _resolve_proxmox_connection(args) -> tuple[str, str, str, str]:
    """Résout url/user/token_id/token_secret : options CLI, sinon cluster installé.

    Pas de prompt interactif de secours : soit les 4 options sont fournies en
    ligne de commande, soit `--cluster <nom>` pointe un cluster déjà configuré
    par `labomatics install` (`~/.labomatics/clusters/<nom>/install.yaml`),
    soit on arrête tout — plutôt que de deviner une connexion Proxmox.
    """
    if args.cluster_url and args.user and args.token_id and args.token_secret:
        return args.cluster_url, args.user, args.token_id, args.token_secret

    clusters = InstallStore.list_clusters()
    if args.cluster:
        if args.cluster not in clusters:
            raise RuntimeError(
                f"Cluster '{args.cluster}' introuvable dans {DEFAULT_BASE_DIR} "
                f"(clusters connus : {', '.join(clusters) or 'aucun'}). "
                f"Lance `labomatics install --cluster {args.cluster}` d'abord."
            )
        cluster_name = args.cluster
    elif len(clusters) == 1:
        cluster_name = clusters[0]
    elif clusters:
        raise RuntimeError(
            f"Plusieurs clusters configurés ({', '.join(clusters)}) : précise "
            "--cluster <nom>, ou fournis --cluster-url/--user/--token-id/--token-secret."
        )
    else:
        raise RuntimeError(
            "Aucune connexion Proxmox disponible : ni --cluster-url/--user/--token-id/"
            f"--token-secret fournis, ni cluster configuré sur cette machine "
            f"({DEFAULT_BASE_DIR}). Lance `labomatics install` ici, ou fournis "
            "les 4 options manuellement."
        )

    proxmox_cfg = InstallStore.open(cluster_name).config.proxmox
    if proxmox_cfg is None:
        raise RuntimeError(
            f"Le cluster '{cluster_name}' n'a pas de connexion Proxmox enregistrée "
            f"(page « Proxmox » jamais validée par `labomatics install --cluster "
            f"{cluster_name}`)."
        )
    console.print(
        f"\nConnexion Proxmox : [bold]{proxmox_cfg.url}[/bold] ({proxmox_cfg.user}) "
        f"— cluster « {cluster_name} »"
    )
    return (
        proxmox_cfg.url,
        proxmox_cfg.user,
        proxmox_cfg.token_id,
        proxmox_cfg.token_secret,
    )


def _resolve_node(pve: ProxmoxClient, args) -> tuple[str, str]:
    """Choisit le nœud cible et son IP SSH. Retourne (node_name, ssh_host)."""
    nodes = pve.get_nodes()
    if not nodes:
        raise RuntimeError("Aucun nœud Proxmox trouvé sur ce cluster")

    if args.node:
        if args.node not in nodes:
            raise RuntimeError(
                f"Nœud '{args.node}' introuvable "
                f"(nœuds disponibles : {', '.join(nodes)})"
            )
        node = args.node
    elif len(nodes) == 1:
        node = nodes[0]
    else:
        console.print("\nNœuds Proxmox disponibles :")
        for i, n in enumerate(nodes, 1):
            console.print(f"  {i}. {n}")
        idx = int(prompt_with_retry("Sélectionner le nœud (numéro)", default="1")) - 1
        node = nodes[idx]

    ssh_host = (
        args.ssh_host
        or pve.get_nodes_with_ips().get(node)
        or pve.get_node_ip(node)
        or node
    )
    return node, ssh_host


def _check_ssh(ssh_host: str) -> None:
    key_path = CliKey().path
    if not key_path.exists():
        raise RuntimeError(
            f"Clé SSH du CLI introuvable ({key_path}). Lance `labomatics install` "
            "sur ce cluster au moins une fois pour la générer et la déployer sur "
            "les nœuds, avant d'utiliser `template build-openwrt`."
        )
    result = subprocess.run(
        ["ssh", *_SSH_OPTS, f"root@{ssh_host}", "true"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Connexion SSH root@{ssh_host} (clé {key_path}) impossible : "
            f"{result.stderr.strip()}\nVérifie que cette clé a bien été déployée "
            "sur le nœud par `labomatics install`."
        )


def _build_remote_script(
    *, version: str, vmid: int, password: str, storage: str
) -> str:
    """Génère le script shell exécuté en une session SSH root sur le nœud cible."""
    img_base = f"openwrt-{version}-x86-64-generic-ext4-combined"
    img_url = (
        f"https://downloads.openwrt.org/releases/{version}/targets/x86/64/"
        f"{img_base}.img.gz"
    )
    pkg_base = (
        f"https://downloads.openwrt.org/releases/{version}/targets/x86/64/packages"
    )
    built_date = date.today().isoformat()
    init_b64 = base64.b64encode(_OPENWRT_INIT.read_bytes()).decode()

    return f"""#!/bin/sh
set -u
for dep in losetup mount umount openssl qm wget gzip ar tar; do
  command -v "$dep" >/dev/null 2>&1 || {{ echo "Commande introuvable : $dep" >&2; exit 1; }}
done

TMP=$(mktemp -d)
cd "$TMP" || exit 1
IMG_GZ="{img_base}.img.gz"
IMG="{img_base}.img"
MNT="$TMP/mnt"
mkdir -p "$MNT"

echo "==> Téléchargement OpenWrt {version}..."
wget -O "$IMG_GZ" "{img_url}" || {{ echo "wget a échoué" >&2; exit 1; }}
[ -s "$IMG_GZ" ] || {{ echo "Fichier téléchargé vide" >&2; exit 1; }}

echo "==> Extraction..."
gzip -d "$IMG_GZ"
GZ_RC=$?
if [ "$GZ_RC" -ne 0 ] && [ "$GZ_RC" -ne 2 ]; then
  echo "gzip -d a échoué (exit $GZ_RC)" >&2
  exit 1
fi
[ -f "$IMG" ] || {{ echo "Fichier extrait introuvable: $IMG" >&2; exit 1; }}

echo "==> Montage partition root (p2)..."
LOOP=$(losetup -f) || exit 1
losetup -P "$LOOP" "$IMG" || exit 1
cleanup() {{ umount "$MNT" >/dev/null 2>&1; losetup -d "$LOOP" >/dev/null 2>&1; }}
trap cleanup EXIT
mount "${{LOOP}}p2" "$MNT" || exit 1

echo "==> Mot de passe root..."
PWD_HASH=$(openssl passwd -1 '{password}')
for f in "$MNT/etc/shadow" "$MNT/etc/passwd"; do
  [ -f "$f" ] && sed -i "s|^root:[^:]*:|root:${{PWD_HASH}}:|" "$f"
done

echo "==> Configuration SSH (Dropbear)..."
mkdir -p "$MNT/etc/dropbear" "$MNT/etc/rc.d"
echo 'DROPBEAR_EXTRA_ARGS="-p 22"' > "$MNT/etc/dropbear/dropbear.conf"
[ -e "$MNT/etc/rc.d/S50dropbear" ] || ln -s ../init.d/dropbear "$MNT/etc/rc.d/S50dropbear" 2>/dev/null || true

echo "==> Génération certificat HTTPS..."
openssl req -x509 -newkey rsa:2048 -keyout "$MNT/etc/uhttpd.key" -out "$MNT/etc/uhttpd.crt" \\
  -days 3650 -nodes -subj "/C=FR/O=OpenWrt/CN=openwrt" 2>/dev/null
chmod 600 "$MNT/etc/uhttpd.key" 2>/dev/null || true

echo "==> Installation qemu-guest-agent..."
if wget -q -O Packages.gz "{pkg_base}/Packages.gz"; then
  gunzip -f Packages.gz
  QEMU_FILE=$(grep '^Filename:.*qemu-ga' Packages 2>/dev/null | head -1 | awk '{{print $2}}')
  if [ -n "$QEMU_FILE" ] && wget -q -O qemu-ga.ipk "{pkg_base}/$QEMU_FILE"; then
    ar x qemu-ga.ipk
    if [ -f data.tar.gz ]; then
      tar -xzf data.tar.gz -C "$MNT"
      for svc in qemu-guest-agent qemu-ga; do
        if [ -f "$MNT/etc/init.d/$svc" ]; then
          [ -e "$MNT/etc/rc.d/S95$svc" ] || ln -s "../init.d/$svc" "$MNT/etc/rc.d/S95$svc"
          break
        fi
      done
      echo "  qemu-guest-agent installé"
    fi
  else
    echo "  qemu-ga introuvable dans les repos {version}"
  fi
else
  echo "  Packages.gz introuvable, qemu-ga ignoré"
fi

echo "==> Injection script uci-defaults (cloud-init NoCloud)..."
mkdir -p "$MNT/etc/uci-defaults"
echo '{init_b64}' | base64 -d > "$MNT/etc/uci-defaults/99-proxmox-init"
chmod 755 "$MNT/etc/uci-defaults/99-proxmox-init"

echo "==> Démontage..."
umount "$MNT" || exit 1
losetup -d "$LOOP" || true
trap - EXIT

echo "==> Création VM template (VMID {vmid})..."
qm create {vmid} --name "openwrt-{version}" --memory 256 --cores 1 \\
  --net0 virtio,bridge=vmbr0 --vga std --ostype l26 \\
  --description "OpenWrt {version} x86_64 - built {built_date}" || exit 1

echo "==> Import du disque..."
qm importdisk {vmid} "$IMG" {storage} || exit 1

DISK_ID=$(qm config {vmid} | grep '^unused' | head -1 | cut -d: -f2 | tr -d ' ')
[ -n "$DISK_ID" ] || DISK_ID="{storage}:vm-{vmid}-disk-0"
qm set {vmid} --virtio0 "${{DISK_ID}},discard=on,iothread=1" --boot order=virtio0 || exit 1

echo "==> Conversion en template..."
qm template {vmid} || exit 1

rm -rf "$TMP"
echo "BUILD_OK"
"""


def run_build(args) -> int:
    """Point d'entrée de `labomatics template build-openwrt`."""
    title("labomatics template build-openwrt")

    version = args.version
    if not version:
        info("Récupération de la dernière version OpenWrt...")
        try:
            version = _get_latest_openwrt_version()
            console.print(f"  Dernière version stable : [bold]{version}[/bold]")
        except Exception as e:
            console.print(
                f"[yellow]⚠  Impossible de récupérer la version : {e} "
                "— fallback 23.05.5[/yellow]"
            )
            version = "23.05.5"

    url, user, token_id, token_secret = _resolve_proxmox_connection(args)
    pve = ProxmoxClient(url, user, token_id, token_secret)

    node, ssh_host = _resolve_node(pve, args)
    storage = args.storage or prompt_with_retry(
        "Storage de destination", default="local"
    )
    vmid = args.vmid or DEFAULT_VMID
    password = args.password or DEFAULT_PASSWORD

    console.print(
        f"\nCluster : [bold]{pve.get_cluster_name()}[/bold] — "
        f"nœud cible : [bold]{node}[/bold] ({ssh_host})"
    )

    if pve.vm_exists(node, vmid) or pve.find_vm_node(vmid):
        console.print(
            f"[yellow]⚠  La template OpenWRT vmid={vmid} existe déjà.[/yellow]"
        )
        if not Confirm.ask("Recréer la template OpenWRT ?", default=False):
            console.print("[dim]Annulé — template existante conservée.[/dim]")
            return 0
        _delete_existing_template(pve, vmid)

    info(f"Connexion SSH root@{ssh_host}...")
    _check_ssh(ssh_host)
    success("SSH OK")

    script = _build_remote_script(
        version=version, vmid=vmid, password=password, storage=storage
    )

    step(1, 1, f"Build OpenWrt {version} sur {node} (session SSH root@{ssh_host})")
    result = subprocess.run(
        ["ssh", *_SSH_OPTS, f"root@{ssh_host}", "sh", "-s"],
        input=script,
        text=True,
    )
    if result.returncode != 0:
        console.print("[red]❌ Le build a échoué sur le nœud distant.[/red]")
        return 1

    pve.ensure_pool("templates")
    pve.moove_vm_to_pool("templates", vmid)
    success(f"Template OpenWrt {version} prête (vmid={vmid}) sur le nœud {node}")
    return 0

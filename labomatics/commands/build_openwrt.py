#!/usr/bin/env python3
"""
Commande ``build-openwrt`` — crée la template VM OpenWrt sur un nœud Proxmox.

Remplace le script shell ``scripts/build-openwrt-vm-template.sh``.
Doit être exécuté en root **directement sur un nœud Proxmox** ayant accès
au stockage partagé.

Étapes :
  1. Téléchargement de l'image OpenWrt x86_64
  2. Extraction gzip
  3. Montage via losetup (partition root = p2)
  4. Injection mot de passe root (MD5-crypt)
  5. Activation SSH (Dropbear)
  6. Génération certificat HTTPS auto-signé
  7. Installation qemu-guest-agent depuis les repos OpenWrt
  8. Injection du script uci-defaults (lecteur cloud-init NoCloud)
  9. Démontage
 10. Création VM Proxmox + import disque + conversion en template
"""

import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from rich.console import Console

from ._helpers import ask_confirm

console = Console()

_UCI_DEFAULTS_SCRIPT = """\
#!/bin/sh
# Lecteur cloud-init NoCloud pour OpenWrt (format Proxmox v1)
# Applique hostname + réseau depuis le drive injecté par Proxmox

CIDEV="/dev/sr0"

mkdir -p /tmp/cidata
mount -o ro "$CIDEV" /tmp/cidata 2>/dev/null || CIDEV=""

if [ -n "$CIDEV" ]; then
  if [ -f /tmp/cidata/user-data ]; then
    HN=$(grep '^hostname:' /tmp/cidata/user-data | awk '{print $2}')
    [ -n "$HN" ] && uci set system.@system[0].hostname="$HN"
  fi

  if [ -f /tmp/cidata/network-config ]; then
    uci delete network.lan  2>/dev/null
    uci delete network.wan  2>/dev/null
    uci delete network.wan6 2>/dev/null

    awk '
      /- type: physical/ {
        if (iface) print iface, addr, mask, gw
        iface=""; addr=""; mask=""; gw=""; skip=0
      }
      /- type: nameserver/ {
        if (iface) { print iface, addr, mask, gw; iface="" }
        skip=1
      }
      skip       { next }
      $1=="name:"    { iface=$2; gsub(/[\\047"]/, "", iface) }
      $1=="address:" { addr=$2;  gsub(/[\\047"]/, "", addr)  }
      $1=="netmask:" { mask=$2;  gsub(/[\\047"]/, "", mask)  }
      $1=="gateway:" { gw=$2;    gsub(/[\\047"]/, "", gw)    }
      END { if (iface) print iface, addr, mask, gw }
    ' /tmp/cidata/network-config | while read IFACE ADDR MASK GW; do
      if [ -n "$GW" ]; then NAME="wan"
      else NAME="lan"
      fi
      uci set network.$NAME=interface
      uci set network.$NAME.proto='static'
      uci set network.$NAME.ipaddr="$ADDR"
      uci set network.$NAME.netmask="$MASK"
      uci set network.$NAME.device="$IFACE"
      [ -n "$GW" ] && uci set network.$NAME.gateway="$GW"
    done

    uci commit network
    /etc/init.d/network restart
  fi

  uci commit system
  umount /tmp/cidata 2>/dev/null || true
fi

uci set uhttpd.main.listen_http='0.0.0.0:80'
uci set uhttpd.main.listen_https='0.0.0.0:443'
if [ -f /etc/uhttpd.crt ] && [ -f /etc/uhttpd.key ]; then
  uci set uhttpd.main.cert='/etc/uhttpd.crt'
  uci set uhttpd.main.key='/etc/uhttpd.key'
  uci set uhttpd.main.redirect_https=1
fi
uci commit uhttpd
/etc/init.d/uhttpd enable 2>/dev/null || true
/etc/init.d/uhttpd restart 2>/dev/null || true

uci add firewall rule
uci set firewall.@rule[-1].name='Allow-Web-WAN'
uci set firewall.@rule[-1].src='wan'
uci set firewall.@rule[-1].dest_port='80 443'
uci set firewall.@rule[-1].proto='tcp'
uci set firewall.@rule[-1].target='ACCEPT'
uci commit firewall
/etc/init.d/firewall reload 2>/dev/null || true

cp "$0" /etc/proxmox-init.sh 2>/dev/null || true
exit 0
"""


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def _check_root() -> None:
    import os

    if os.geteuid() != 0:
        console.print(
            "[red]❌ Cette commande doit être exécutée en root sur le nœud Proxmox.[/red]"
        )
        sys.exit(1)


def _check_deps() -> None:
    for dep in ("losetup", "mount", "umount", "openssl", "qm", "wget", "gunzip"):
        if not shutil.which(dep):
            console.print(f"[red]❌ Commande introuvable : {dep}[/red]")
            sys.exit(1)


def cmd_build_openwrt(args) -> None:
    """Crée la template VM OpenWrt sur le nœud Proxmox local (root requis)."""
    from ..config import load_config

    try:
        config = load_config()
        _storage_default = config.openwrt.storage
        _vmid_default = config.openwrt.template_vmid
    except Exception:
        _storage_default = "local-lvm"
        _vmid_default = 90200

    version: str = args.version
    vmid: int = args.vmid if args.vmid is not None else _vmid_default
    storage: str = args.storage if args.storage is not None else _storage_default
    password: str = args.password

    _check_root()
    _check_deps()

    img_base = f"openwrt-{version}-x86-64-generic-ext4-combined"
    img_url = f"https://downloads.openwrt.org/releases/{version}/targets/x86/64/{img_base}.img.gz"
    pkg_base = f"https://downloads.openwrt.org/releases/{version}/targets/x86/64/packages"

    # Vérification VM existante
    result = _run(["qm", "status", str(vmid)], check=False)
    if result.returncode == 0:
        console.print(f"[yellow]⚠  La VM {vmid} existe déjà.[/yellow]")
        if not getattr(args, "yes", False):
            if not ask_confirm(f"Remplacer la VM {vmid} ?"):
                console.print("[dim]Annulé.[/dim]")
                return
        _run(["qm", "destroy", str(vmid), "--purge"])
        console.print(f"  [red]✖ VM {vmid} supprimée[/red]")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        img_gz = tmp / f"{img_base}.img.gz"
        img = tmp / f"{img_base}.img"
        mnt = tmp / "mnt"
        mnt.mkdir()

        # Téléchargement via wget (sortie visible pour diagnostic)
        console.print(f"\n[bold]==> Téléchargement OpenWrt {version}...[/bold]")
        console.print(f"  [dim]{img_url}[/dim]")
        ret = subprocess.run(
            ["wget", "-O", str(img_gz), img_url],
            check=False,
        )
        if ret.returncode != 0:
            raise RuntimeError(f"wget a échoué (exit {ret.returncode})\nURL : {img_url}")
        if not img_gz.exists() or img_gz.stat().st_size < 1024:
            raise RuntimeError(f"Fichier téléchargé vide ou absent : {img_gz}")
        with open(img_gz, "rb") as f:
            magic = f.read(4)
        if magic[:2] != b"\x1f\x8b":
            raise RuntimeError(
                f"Fichier téléchargé invalide — premiers bytes : {magic!r}\n"
                f"Taille : {img_gz.stat().st_size} bytes\n"
                f"URL : {img_url}\n"
                f"Vérifiez la connectivité réseau du nœud (proxy ? firewall ?)."
            )
        console.print(
            f"  [green]✓ {img_gz.name} ({img_gz.stat().st_size // 1024 // 1024} MB)[/green]"
        )

        # Extraction gzip (exit 2 = trailing garbage sur image OpenWrt, non fatal)
        console.print("[bold]==> Extraction...[/bold]")
        r = _run(["gzip", "-d", str(img_gz)], check=False)
        if r.returncode not in (0, 2):
            raise RuntimeError(f"gzip -d a échoué (exit {r.returncode}) : {r.stderr.strip()}")
        if not img.exists():
            raise RuntimeError(f"Fichier extrait introuvable : {img}")

        # Montage (losetup -P pour partitions)
        console.print("[bold]==> Montage partition root (p2)...[/bold]")
        loop_result = _run(["losetup", "-f"])
        loop = loop_result.stdout.strip()
        _run(["losetup", "-P", loop, str(img)])

        try:
            _run(["mount", f"{loop}p2", str(mnt)])

            # Mot de passe root
            console.print("[bold]==> Mot de passe root...[/bold]")
            pwd_result = _run(["openssl", "passwd", "-1", password])
            pwd_hash = pwd_result.stdout.strip()
            shadow = mnt / "etc" / "shadow"
            passwd_f = mnt / "etc" / "passwd"
            import re

            for pfile in (shadow, passwd_f):
                if pfile.exists():
                    content = pfile.read_text()
                    content = re.sub(r"^(root):[^:]*:", f"root:{pwd_hash}:", content, flags=re.M)
                    pfile.write_text(content)
                    break

            # SSH Dropbear
            console.print("[bold]==> Configuration SSH (Dropbear)...[/bold]")
            dropbear_dir = mnt / "etc" / "dropbear"
            dropbear_dir.mkdir(parents=True, exist_ok=True)
            (dropbear_dir / "dropbear.conf").write_text('DROPBEAR_EXTRA_ARGS="-p 22"\n')
            symlink = mnt / "etc" / "rc.d" / "S50dropbear"
            if not symlink.exists():
                try:
                    symlink.symlink_to("../init.d/dropbear")
                except Exception:
                    pass

            # Certificat HTTPS
            console.print("[bold]==> Génération certificat HTTPS...[/bold]")
            _run(
                [
                    "openssl",
                    "req",
                    "-x509",
                    "-newkey",
                    "rsa:2048",
                    "-keyout",
                    str(mnt / "etc" / "uhttpd.key"),
                    "-out",
                    str(mnt / "etc" / "uhttpd.crt"),
                    "-days",
                    "3650",
                    "-nodes",
                    "-subj",
                    "/C=FR/O=OpenWrt/CN=openwrt",
                ]
            )
            (mnt / "etc" / "uhttpd.key").chmod(0o600)

            # qemu-guest-agent
            console.print("[bold]==> Installation qemu-guest-agent...[/bold]")
            try:
                with urllib.request.urlopen(f"{pkg_base}/Packages.gz", timeout=30) as resp:
                    import gzip
                    import io

                    with gzip.open(io.BytesIO(resp.read())) as gz:
                        pkg_list = gz.read().decode("utf-8", errors="replace")

                qemu_file = ""
                for line in pkg_list.splitlines():
                    if line.startswith("Filename:") and "qemu-ga" in line:
                        qemu_file = line.split(":", 1)[1].strip()
                        break

                if qemu_file:
                    ipk = tmp / "qemu-ga.ipk"
                    urllib.request.urlretrieve(f"{pkg_base}/{qemu_file}", ipk)
                    # .ipk = ar archive contenant data.tar.gz
                    _run(["ar", "x", str(ipk)], check=False)
                    data_tgz = Path("data.tar.gz")
                    if data_tgz.exists():
                        _run(["tar", "-xzf", str(data_tgz), "-C", str(mnt)])
                        data_tgz.unlink(missing_ok=True)
                    for svc in ("qemu-guest-agent", "qemu-ga"):
                        init = mnt / "etc" / "init.d" / svc
                        if init.exists():
                            rc_link = mnt / "etc" / "rc.d" / f"S95{svc}"
                            if not rc_link.exists():
                                rc_link.symlink_to(f"../init.d/{svc}")
                            break
                    console.print("  [green]✓ qemu-guest-agent installé[/green]")
                else:
                    console.print(
                        f"  [yellow]⚠  qemu-ga introuvable dans les repos {version}[/yellow]"
                    )
            except Exception as e:
                console.print(f"  [yellow]⚠  qemu-ga : {e}[/yellow]")

            # Script uci-defaults
            console.print("[bold]==> Injection script uci-defaults (cloud-init NoCloud)...[/bold]")
            uci_dir = mnt / "etc" / "uci-defaults"
            uci_dir.mkdir(parents=True, exist_ok=True)
            uci_script = uci_dir / "99-proxmox-init"
            uci_script.write_text(_UCI_DEFAULTS_SCRIPT)
            uci_script.chmod(0o755)

            console.print("[bold]==> Démontage...[/bold]")
        finally:
            _run(["umount", str(mnt)], check=False)
            _run(["losetup", "-d", loop], check=False)

        # Création VM Proxmox
        import datetime

        built_date = datetime.date.today().isoformat()
        console.print(f"\n[bold]==> Création VM template (VMID {vmid})...[/bold]")
        _run(
            [
                "qm",
                "create",
                str(vmid),
                "--name",
                f"openwrt-{version}",
                "--memory",
                "256",
                "--cores",
                "1",
                "--net0",
                "virtio,bridge=vmbr0",
                "--serial0",
                "socket",
                "--vga",
                "serial0",
                "--ostype",
                "l26",
                "--description",
                f"OpenWrt {version} x86_64 - built {built_date}",
            ]
        )

        console.print("[bold]==> Import du disque...[/bold]")
        _run(["qm", "importdisk", str(vmid), str(img), storage])
        # Lire le volume ID réel depuis qm config (ligne "unusedN: <volume>")
        cfg_out = _run(["qm", "config", str(vmid)]).stdout
        disk_id: str | None = None
        for line in cfg_out.splitlines():
            if line.startswith("unused"):
                disk_id = line.split(":", 1)[1].strip()
                break
        if not disk_id:
            disk_id = f"{storage}:vm-{vmid}-disk-0"
            console.print(f"  [yellow]⚠ volume ID non trouvé, fallback : {disk_id}[/yellow]")
        _run(
            [
                "qm",
                "set",
                str(vmid),
                "--virtio0",
                f"{disk_id},discard=on,iothread=1",
                "--boot",
                "order=virtio0",
            ]
        )

        console.print("[bold]==> Conversion en template...[/bold]")
        _run(["qm", "template", str(vmid)])

    console.print(f"\n[bold green]✓ Template prête : VM {vmid} (openwrt-{version})[/bold green]")

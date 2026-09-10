import subprocess
import time
import platform

from rich.console import Console

from ...utils.proxmox import ProxmoxClient
from ...utils.state import InstallState
from ...utils.theme import title, multi_select, prompt_with_retry
from .templates import images_list


console = Console()

_DISK_IMAGE_EXTENSIONS = {".img", ".qcow2", ".vmdk", ".raw", ".vhd", ".vhdx"}


def _iso_filename_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


def _is_disk_image(filename: str) -> bool:
    from pathlib import Path

    return Path(filename).suffix.lower() in _DISK_IMAGE_EXTENSIONS


def _image_content_type(filename: str) -> str:
    return "import" if _is_disk_image(filename) else "iso"


def _image_volid(storage: str, filename: str) -> str:
    if _is_disk_image(filename):
        return f"{storage}:import/{filename}"
    return f"{storage}:iso/{filename}"


def _get_storage_base_path(client: ProxmoxClient, storage: str) -> str:
    """Retourne le chemin de base du stockage (vide si non directory)."""
    try:
        for s in client.proxmox.storage.get():
            if s.get("storage") == storage:
                return str(s.get("path", ""))
    except Exception:
        pass
    return ""


def _find_image_path(node: str, storage_path: str, filename: str) -> str:
    """Localise le fichier image sur le nœud via SSH (find récursif)."""
    result = subprocess.run(
        [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            f"root@{node}",
            f"find '{storage_path}' -name '{filename}' 2>/dev/null | head -1",
        ],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _resize_image(node: str, image_path: str, size: str) -> None:
    """Redimensionne une image qcow2 via qemu-img."""
    console.print(f"  [cyan]Redimensionnement image : {size}[/cyan]")
    result = subprocess.run(
        [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            f"root@{node}",
            f"qemu-img resize '{image_path}' {size}",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        console.print(f"  [yellow]⚠  Resize image : {result.stderr.strip()}[/yellow]")
    else:
        console.print("  [green]✓ Image redimensionnée[/green]")


# ── Helpers pool ──────────────────────────────────────────────────────────────


def _virt_customize_image(node: str, image_path: str, packages: list[str]) -> None:
    """Pré-installe des packages dans l'image via virt-customize (SSH root@node).

    Prérequis : libguestfs-tools installé sur le nœud Proxmox.
    """
    pkg_str = ",".join(packages)
    console.print(f"  [cyan]virt-customize : {image_path}[/cyan]")
    console.print(f"    Packages à installer : {pkg_str}")

    # Vérifier l'espace disque de l'image
    result = subprocess.run(
        [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            f"root@{node}",
            f"qemu-img info '{image_path}' | grep 'virtual size'",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        console.print(f"    {result.stdout.strip()}")

    # Active le service qemu-guest-agent : systemd (Ubuntu/Debian/Fedora) ou OpenRC (Alpine)
    # rc-update ne fonctionne pas dans un chroot guestfs — on crée le symlink runlevel directement
    enable_ga = (
        "systemctl enable qemu-guest-agent.service 2>/dev/null"
        "; ln -sf /etc/init.d/qemu-guest-agent /etc/runlevels/default/qemu-guest-agent 2>/dev/null"
        "; true"
    )
    remote_cmd = (
        "command -v virt-customize >/dev/null 2>&1"
        " || apt-get install -y -q libguestfs-tools >&2"
        f" && virt-customize -a '{image_path}'"
        f" --install {pkg_str}"
        f" --run-command '{enable_ga}'"
        " --run-command 'sed -i \"s/^#PasswordAuthentication.*/PasswordAuthentication yes/\" /etc/ssh/sshd_config 2>/dev/null; true'"
        " --run-command 'sed -i \"/reset_rmc/d\" /etc/cloud/cloud.cfg 2>/dev/null; true'"
        " --run-command ': > /etc/machine-id'"
    )
    console.print(f"    Exécution SSH sur {node}...")
    result = subprocess.run(
        ["ssh", "-o", "StrictHostKeyChecking=no", f"root@{node}", remote_cmd],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        console.print("    [red]Erreur virt-customize :[/red]")
        console.print(f"    {result.stderr.strip()}")
        raise RuntimeError(f"virt-customize failed:\n{result.stderr.strip()}")
    console.print("  [green]✓ virt-customize terminé[/green]")


def _shutdown_vm(
    client: ProxmoxClient, node: str, vmid: int, timeout: int = 60
) -> None:
    """Arrête une VM et attend qu'elle soit complètement arrêtée."""
    console.print(f"  [yellow]Arrêt VM vmid={vmid}...[/yellow]")
    try:
        client.proxmox.nodes(node).qemu(vmid).status.stop.post()
    except Exception:
        pass

    start = time.time()
    while time.time() - start < timeout:
        try:
            status = client.proxmox.nodes(node).qemu(vmid).status.current.get()
            if status.get("status") == "stopped":
                console.print(f"  [green]✓ VM vmid={vmid} arrêtée[/green]")
                return
        except Exception:
            return
        time.sleep(1)
    console.print(f"  [yellow]⚠  VM vmid={vmid} timeout arrêt[/yellow]")


def _delete_existing_template(client: ProxmoxClient, vmid: int) -> None:
    node = client.find_vm_node(vmid)
    if node is None:
        return
    console.print(f"  [yellow]Template vmid={vmid} existante → suppression...[/yellow]")
    _shutdown_vm(client, node, vmid, timeout=30)
    try:
        task = client.proxmox.nodes(node).qemu(vmid).delete(purge=1)
        client.wait_for_task(node, task)
        console.print(f"  [red]✖ Template vmid={vmid} supprimée[/red]")
    except Exception as e:
        console.print(f"  [yellow]⚠  Suppression template vmid={vmid} : {e}[/yellow]")


def _delete_existing_iso(
    client: ProxmoxClient, node: str, storage: str, filename: str
) -> None:
    volid = _image_volid(storage, filename)
    try:
        contents = client.proxmox.nodes(node).storage(storage).content.get()
        if any(c.get("volid") == volid for c in contents):
            client.proxmox.nodes(node).storage(storage).content(volid).delete()
            console.print(f"  [yellow]↻ Image supprimée : {volid}[/yellow]")
    except Exception as e:
        console.print(f"  [yellow]⚠  Suppression image {volid} : {e}[/yellow]")


def _download_image(
    client: ProxmoxClient, node: str, storage: str, url: str, filename: str
) -> str:
    """Télécharge l'image sur le stockage Proxmox via l'API. Retourne le volid."""
    console.print(f"  [cyan]Téléchargement : {url}[/cyan]")
    task = (
        client.proxmox.nodes(node)
        .storage(storage)("download-url")
        .post(
            content=_image_content_type(filename),
            filename=filename,
            url=url,
        )
    )
    client.wait_for_task(node, task, timeout=600)
    volid = _image_volid(storage, filename)
    console.print(f"  [green]✓ Image téléchargée : {volid}[/green]")
    return volid


def _create_vm(
    client: ProxmoxClient,
    node: str,
    tmpl,
    iso_volid: str,
    dest_storage: str,
    bridge: str,
    eff_user: str = "",
    eff_pass: str = "",
) -> None:
    """Crée la VM avec import-from.

    Si tmpl.cloudinit=True  : drive cloud-init + agent + ciuser + ipconfig0 (défaut).
    Si tmpl.cloudinit=False : VM nue sans cloud-init ni agent (ex: OPNsense, pfSense).
    Si tmpl.uefi=True       : UEFI BIOS + efidisk0.
    """
    ostype = tmpl.ostype if tmpl.ostype != "other" else "l26"
    boot_order = "order=virtio0" if not tmpl.uefi else "order=virtio0"
    kwargs: dict = dict(
        name=tmpl.name.replace("_", "-"),
        memory=tmpl.memory,
        cores=tmpl.cores,
        sockets=1,
        cpu=tmpl.cpu_type,
        machine="q35" if tmpl.uefi else "pc",
        net0=f"virtio,bridge={bridge}",
        virtio0=f"{dest_storage}:0,import-from={iso_volid}",
        boot=boot_order,
        vga="std",
        ostype=ostype,
    )
    if tmpl.uefi:
        kwargs["bios"] = "ovmf"
        kwargs[
            "efidisk0"
        ] = f"{dest_storage}:1,efitype=4m,pre-enrolled-keys=1,format=qcow2"
        kwargs["boot"] = "order=virtio0;net0"
    if tmpl.cloudinit:
        kwargs["ide2"] = f"{dest_storage}:cloudinit"
        kwargs["agent"] = "enabled=1"
        kwargs["ciuser"] = eff_user
        kwargs["cipassword"] = eff_pass
        kwargs["ipconfig0"] = "ip=dhcp"

    task = client.create_vm_from_data(node, str(tmpl.vmid), kwargs)
    if task:
        client.wait_for_task(node, task, timeout=120)
    console.print(f"  [green]✓ VM vmid={tmpl.vmid} créée[/green]")


def _resize_disk(client: ProxmoxClient, node: str, vmid: int, size: str) -> None:
    try:
        client.proxmox.nodes(node).qemu(vmid).resize.put(disk="virtio0", size=size)
        console.print(f"  [green]✓ Disque → {size}[/green]")
    except Exception as e:
        console.print(f"  [yellow]⚠  Resize disque : {e}[/yellow]")


def _start_vm(client: ProxmoxClient, node: str, vmid: int) -> None:
    task = client.proxmox.nodes(node).qemu(vmid).status.start.post()
    if task:
        client.wait_for_task(node, task, timeout=60)
    console.print(f"  [green]✓ VM vmid={vmid} démarrée[/green]")


def _wait_for_guest_agent(
    client: ProxmoxClient, node: str, vmid: int, timeout: int = 300
) -> bool:
    """Attend que le guest agent soit disponible (VM bootée + cloud-init terminé)."""
    import sys

    console.print("  [cyan]Attente du guest agent...[/cyan]")
    start = time.time()
    deadline = start + timeout
    while time.time() < deadline:
        try:
            client.proxmox.nodes(node).qemu(vmid).agent("get-osinfo").get()
            sys.stderr.write("\r\033[K")
            sys.stderr.flush()
            return True
        except Exception:
            elapsed = int(time.time() - start)
            sys.stderr.write(f"\r  ⏳ guest agent [{elapsed}s / {timeout}s]")
            sys.stderr.flush()
            time.sleep(10)
    sys.stderr.write("\r\033[K")
    sys.stderr.flush()
    return False


def _wait_vm_stopped(
    client: ProxmoxClient, node: str, vmid: int, timeout: int = 60
) -> bool:
    """Attend que la VM soit à l'état 'stopped'."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            status = client.proxmox.nodes(node).qemu(vmid).status.current.get()
            if status.get("status") == "stopped":
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def _wait_vm_unlocked(
    client: ProxmoxClient, node: str, vmid: int, timeout: int = 30
) -> None:
    """Attend que le verrou Proxmox de la VM se libère (après un shutdown échoué)."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            status = client.proxmox.nodes(node).qemu(vmid).status.current.get()
            if not status.get("lock"):
                return
        except Exception:
            return
        time.sleep(2)


def _force_stop_vm(client: ProxmoxClient, node: str, vmid: int) -> None:
    """Force l'arrêt immédiat via l'API Proxmox.

    Attend d'abord que le verrou soit libéré (un shutdown échoué laisse la VM verrouillée).
    POST /status/stop est un arrêt brutal immédiat (équivalent SIGKILL sur QEMU).
    skiplock=1 permet de contourner un verrou résiduel du shutdown échoué.
    """
    _wait_vm_unlocked(client, node, vmid)
    try:
        task = client.proxmox.nodes(node).qemu(vmid).status.stop.post()
        if task:
            client.wait_for_task(node, task, timeout=30)
    except Exception as e:
        console.print(f"  [yellow]⚠  Force stop API : {e}[/yellow]")
    _wait_vm_stopped(client, node, vmid, timeout=10)


def _graceful_shutdown_vm(client: ProxmoxClient, node: str, vmid: int) -> None:
    console.print("  [cyan]Graceful shutdown...[/cyan]")
    try:
        task = client.proxmox.nodes(node).qemu(vmid).status.shutdown.post()
        client.wait_for_task(node, task, timeout=120)
    except Exception as e:
        console.print(f"  [yellow]⚠  Shutdown propre : {e} — forçage...[/yellow]")
        _force_stop_vm(client, node, vmid)
        return
    _wait_vm_stopped(client, node, vmid, timeout=10)


def _convert_to_template(
    proxmox,
    node: str,
    vmid: int,
    default_user: str = "",
    default_pass: str = "",
    cloudinit: bool = True,
) -> None:
    """Nettoie la config de build, pousse les defaults cloud-init, convertit en template.

    - Supprime les NICs et ipconfig0 (pas d'IP figée dans la template)
    - Conserve le drive cloud-init (ide2) avec ciuser/cipassword pré-remplis
      → visibles dans l'onglet Cloud-Init lors de la création d'un clone
    """
    try:
        cfg = proxmox.proxmox.nodes(node).qemu(vmid).config.get()
        to_delete = [k for k in cfg if k.startswith("net")]
        for field in ("ipconfig0", "nameserver", "searchdomain"):
            if field in cfg:
                to_delete.append(field)
        update: dict = {}
        if cloudinit:
            if default_user:
                update["ciuser"] = default_user
            if default_pass:
                update["cipassword"] = default_pass
        else:
            # Pas de cloud-init — supprimer tous les champs ci* s'ils existent
            for field in ("ciuser", "cipassword", "cicustom"):
                if field in cfg:
                    to_delete.append(field)
        if to_delete:
            proxmox.proxmox.nodes(node).qemu(vmid).config.put(
                delete=",".join(to_delete)
            )
        if update:
            proxmox.proxmox.nodes(node).qemu(vmid).config.put(**update)
    except Exception as e:
        console.print(f"  [yellow]⚠  Nettoyage config : {e}[/yellow]")
    proxmox.proxmox.nodes(node).qemu(vmid).template.post()
    console.print(
        f"  [green]✓ vmid={vmid} converti en template (cloud-init prêt)[/green]"
    )


def run_installation(state: InstallState) -> int:
    """Orchestrer l'installation."""
    title("labomatics install — gestion des templates")

    step_data = state.get_step(10)

    templates_pool = "templates"
    default_packages = ["qemu-guest-agent"]
    shared_pool = state.get_step(3).get("storage")
    bridge = state.get_step(1).get("network_iface")

    if step_data:
        ciuser = "labomatics"
        cipassword = "labomatics"
        iso_storage_pool = "local"
    else:
        ciuser = prompt_with_retry("Utilisateur cloud init", default="labomatics")
        cipassword = prompt_with_retry("Mot de passe cloud init", default="labomatics")
        iso_storage_pool = prompt_with_retry("Storage des iso", default="local")

        state.set_step(
            10,
            {
                "ciuser": ciuser,
                "cipassword": cipassword,
                "iso_storage_pool": iso_storage_pool,
            },
        )

    state_2 = state.get_step(2)

    pve = ProxmoxClient(
        state_2.get("proxmox_url"),
        state_2.get("proxmox_user"),
        state_2.get("proxmox_token_id"),
        state_2.get("proxmox_token_secret"),
    )

    templates = images_list

    templates_for_choice = {tmpl.name: tmpl for tmpl in templates}

    console.print("Choisir les templates à créer")
    selected = multi_select(templates_for_choice.keys())

    selected_templates = [
        tmpl for name, tmpl in templates_for_choice.items() if name in selected
    ]
    console.print(f"Construction de [yellow] {len(selected_templates)}[/yellow]")
    pve.ensure_pool(templates_pool)

    for tmpl in selected_templates:
        console.print(
            f"\n[bold cyan]═══ Template : {tmpl.name} (vmid={tmpl.vmid}) ═══[/bold cyan]"
        )
        if tmpl.cloudinit:
            console.print(f"  [dim]cloud-init user : {ciuser}[/dim]")
            console.print(f"  [dim]cloud-init password : {cipassword}[/dim]")

        node = platform.node()
        filename = _iso_filename_from_url(tmpl.iso_url)

        # 1. Supprimer template existante
        _delete_existing_template(pve, tmpl.vmid)

        # 2. Supprimer image existante
        _delete_existing_iso(pve, node, iso_storage_pool, filename)

        # 3. Télécharger l'image
        try:
            iso_volid = _download_image(
                pve, node, iso_storage_pool, tmpl.iso_url, filename
            )
        except Exception as e:
            console.print(f"[red]❌ Téléchargement échoué : {e}[/red]")
            continue

        # 3b. virt-customize (default_packages + extra_packages, sauf download_packages=False)
        effective_packages = default_packages + tmpl.extra_packages
        if tmpl.download_packages and effective_packages:
            storage_path = _get_storage_base_path(pve, iso_storage_pool)
            if not storage_path:
                console.print(
                    f"  [yellow]⚠  packages ignorés : chemin du stockage '{iso_storage_pool}' introuvable[/yellow]"
                )
            else:
                image_path = _find_image_path(node, storage_path, filename)
                if not image_path:
                    console.print(
                        f"  [yellow]⚠  packages ignorés : fichier '{filename}' introuvable dans {storage_path}[/yellow]"
                    )
                else:
                    if tmpl.qcow_size:
                        _resize_image(node, image_path, tmpl.qcow_size)
                    console.print(
                        f"  [cyan]virt-customize : {', '.join(effective_packages)}[/cyan]"
                    )
                    try:
                        _virt_customize_image(node, image_path, effective_packages)
                        console.print("  [green]✓ virt-customize terminé[/green]")
                    except Exception as e:
                        console.print(f"[red]❌ virt-customize échoué : {e}[/red]")
                        continue

        # 4. Créer la VM
        try:
            _create_vm(
                pve,
                node,
                tmpl,
                iso_volid,
                bridge=bridge,
                dest_storage=shared_pool,
                eff_user=ciuser,
                eff_pass=cipassword,
            )
        except Exception as e:
            console.print(f"[red]❌ Création VM échouée : {e}[/red]")
            continue

        # 5. Redimensionner le disque
        _resize_disk(pve, node, tmpl.vmid, tmpl.disk_size)

        if tmpl.cloudinit:
            # 6. Démarrer + attendre le guest agent (cloud-init inclus dans l'image)
            try:
                _start_vm(pve, node, tmpl.vmid)
            except Exception as e:
                console.print(f"[red]❌ Démarrage VM : {e}[/red]")
                continue

            if not _wait_for_guest_agent(
                pve, node, tmpl.vmid, timeout=tmpl.boot_timeout
            ):
                # Premier boot parfois bloqué (ex: Alpine/OpenRC) — reset et nouvel essai
                console.print(
                    "  [yellow]⚠  Timeout guest agent — reset VM et nouvel essai...[/yellow]"
                )
                try:
                    task = pve.proxmox.nodes(node).qemu(tmpl.vmid).status.reset.post()
                    if task:
                        pve.wait_for_task(node, task, timeout=30)
                except Exception as e:
                    console.print(f"  [yellow]⚠  Reset : {e}[/yellow]")
                if not _wait_for_guest_agent(
                    pve, node, tmpl.vmid, timeout=tmpl.boot_timeout // 2
                ):
                    console.print(
                        "[red]❌ Timeout guest agent — vérifier que l'image inclut qemu-guest-agent[/red]"
                    )
                    continue

            console.print("  [green]✓ Guest agent disponible[/green]")

            # 7. Shutdown
            _shutdown_vm(pve, node, tmpl.vmid)
        else:
            console.print("  [dim]cloud-init désactivé — pas de boot[/dim]")

        # 8. Nettoyage image
        _delete_existing_iso(pve, node, iso_storage_pool, filename)

        # 9. Conversion en template (retry 3x si VM encore en cours d'arrêt)
        converted = False
        for attempt in range(3):
            try:
                _convert_to_template(
                    pve,
                    node,
                    tmpl.vmid,
                    default_user=ciuser,
                    default_pass=cipassword,
                    cloudinit=tmpl.cloudinit,
                )
                converted = True
                break
            except Exception as e:
                if "running" in str(e).lower() and attempt < 2:
                    console.print(
                        f"  [yellow]⚠  VM encore active, force stop (essai {attempt + 1}/3)...[/yellow]"
                    )
                    _force_stop_vm(pve, node, tmpl.vmid)
                else:
                    console.print(f"[red]❌ Conversion en template : {e}[/red]")
                    break
        if not converted:
            continue

        # 10. Ajout au pool template
        try:
            pve.moove_vm_to_pool(templates_pool, tmpl.vmid)
            console.print(f"  [green]✓ Ajoutée au pool '{templates_pool}'[/green]")
        except Exception as e:
            console.print(f"  [yellow]⚠  Ajout au pool : {e}[/yellow]")

        console.print(
            f"\n[bold green]✓ Template '{tmpl.name}' construite avec succès (vmid={tmpl.vmid})[/bold green]"
        )

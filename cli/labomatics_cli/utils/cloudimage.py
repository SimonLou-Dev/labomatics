"""Gestion des images cloud-init pour Proxmox."""

import requests
from pathlib import Path


class CloudInitImageManager:
    """Télécharger les images cloud-init compatibles Proxmox."""

    # Images cloud-init avec Proxmox support
    IMAGES = {
        "ubuntu": {
            "url": "https://cloud-images.ubuntu.com/resolute/current/resolute-server-cloudimg-amd64.img",
            "filename": "ubuntu-resolute-cloudimg-amd64.qcow2",
            "format": "qcow2",
        },
        "rocky": {
            "url": "https://dl.rockylinux.org/pub/rocky/10/images/x86_64/Rocky-10-GenericCloud-Base.latest.x86_64.qcow2",
            "filename": "Rocky-10-GenericCloud-Base.qcow2",
            "format": "qcow2",
        },
        "alpine": {
            "url": "https://dl-cdn.alpinelinux.org/alpine/v3.24/releases/cloud/generic_alpine-3.24.1-x86_64-uefi-cloudinit-r0.qcow2",
            "filename": "alpine-3.24.1-uefi-cloudinit.qcow2",
            "format": "qcow2",
        },
        "fedora-server": {
            "url": "https://download.fedoraproject.org/pub/fedora/linux/releases/44/Cloud/x86_64/images/Fedora-Cloud-Base-Generic-44-1.7.x86_64.qcow2",
            "filename": "Fedora-Cloud-Base-44.qcow2",
            "format": "qcow2",
        },
    }

    @staticmethod
    def download_image(
        image_type: str = "fedora-server",
        cache_dir: Path = None,
        progress_callback=None,
    ) -> str:
        """
        Télécharger une image cloud-init compatible Proxmox.
        Retourne le chemin local du fichier.
        """
        if image_type not in CloudInitImageManager.IMAGES:
            raise ValueError(
                f"Type d'image inconnu: {image_type}. Options: {list(CloudInitImageManager.IMAGES.keys())}"
            )

        image_info = CloudInitImageManager.IMAGES[image_type]

        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "labomatics"

        cache_dir.mkdir(parents=True, exist_ok=True)
        image_path = cache_dir / image_info["filename"]

        # Si le fichier existe déjà, le retourner
        if image_path.exists():
            return str(image_path)

        # Télécharger
        url = image_info["url"]
        response = requests.get(url, stream=True, timeout=600)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        with open(image_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total_size)

        return str(image_path)

    @staticmethod
    def get_image_filename(image_type: str = "fedora-server") -> str:
        """Retourner le nom de fichier de l'image."""
        if image_type not in CloudInitImageManager.IMAGES:
            raise ValueError(f"Type d'image inconnu: {image_type}")
        return CloudInitImageManager.IMAGES[image_type]["filename"]

    @staticmethod
    def get_image_format(image_type: str = "fedora-server") -> str:
        """Retourner le format de l'image (qcow2, raw, etc)."""
        if image_type not in CloudInitImageManager.IMAGES:
            raise ValueError(f"Type d'image inconnu: {image_type}")
        return CloudInitImageManager.IMAGES[image_type]["format"]

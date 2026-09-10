

from ..models import TempalteConfig


fedora_44_server: TempalteConfig = TempalteConfig(
    name="fedora-44",
    vmid=90300,
    iso_url="https://fr2.rpmfind.net/linux/fedora/linux/releases/44/Cloud/x86_64/images/Fedora-Cloud-Base-Generic-44-1.7.x86_64.qcow2",
    iso_filename="Fedora-Cloud-Base-Generic-44-1.7.x86_64.qcow2",
    memory=2048,
    cores=2,
    disk_size="10G",
    uefi=False
)


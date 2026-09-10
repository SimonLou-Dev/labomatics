from ..models import TempalteConfig


trixie_server: TempalteConfig = TempalteConfig(
    name="debian-trixie",
    vmid=90500,
    iso_url="https://cloud.debian.org/images/cloud/trixie/20260831-2587/debian-13-genericcloud-amd64-20260831-2587.qcow2",
    iso_filename="debian-13-genericcloud-amd64-20260831-2587.qcow2",
    memory=2048,
    cores=2,
    disk_size="10G",
)

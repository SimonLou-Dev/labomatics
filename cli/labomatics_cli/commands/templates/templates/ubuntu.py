from ..models import TempalteConfig


resolute_server: TempalteConfig = TempalteConfig(
    name="ubuntu-resolute",
    vmid=90100,
    iso_url="https://cloud-images.ubuntu.com/resolute/20260823/resolute-server-cloudimg-amd64.img",
    iso_filename="resolute-server-cloudimg-amd64.qcow2",
    memory=2048,
    cores=2,
    disk_size="10G",
)

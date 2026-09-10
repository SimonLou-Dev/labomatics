

from ..models import TempalteConfig


alpine_3_24_server: TempalteConfig = TempalteConfig(
    name="alpine-3-24",
    vmid=90400,
    iso_url="https://dl-cdn.alpinelinux.org/alpine/v3.24/releases/cloud/generic_alpine-3.24.1-x86_64-bios-tiny-r0.qcow2",
    iso_filename="generic_alpine-3.24.1-x86_64-bios-tiny-r0.qcow2",
    memory=1024,
    cores=1,
    disk_size="10G",
    boot_timeout=100,
    cloudinit=False,
    uefi=False
)




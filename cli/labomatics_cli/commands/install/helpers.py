"""Helper functions for installation."""

from ipaddress import IPv4Network, IPv4Address
from ...utils.ssh import SSHClient


def allocate_first_wan_ip(wan_config: dict) -> str:
    """Allouer la première IP WAN pour la VM."""
    network = IPv4Network(wan_config["network"])
    gateway = IPv4Address(wan_config["gateway"])
    exclude = set()

    # Handle exclude: can be string or list
    exclude_raw = wan_config.get("exclude", [])
    if isinstance(exclude_raw, str):
        exclude_raw = [exclude_raw]

    for item in exclude_raw:
        if not item or not isinstance(item, str):
            continue
        item = item.strip()
        if "-" in item:
            try:
                start_ip_str, end_ip_str = item.split("-", 1)
                start_ip = IPv4Address(start_ip_str.strip())
                end_ip = IPv4Address(end_ip_str.strip())
                for ip_int in range(int(start_ip), int(end_ip) + 1):
                    addr = IPv4Address(ip_int)
                    if addr != gateway:
                        exclude.add(str(addr))
            except (ValueError, IndexError):
                pass
        else:
            exclude.add(item)

    for ip in network.hosts():
        if str(ip) != str(gateway) and str(ip) not in exclude:
            return str(ip)
    raise RuntimeError("Pas d'IP disponible dans le réseau WAN")


def connect_to_vm(host: str, user: str = "root", password: str = None) -> SSHClient:
    """Se connecter à la VM en SSH."""
    ssh = SSHClient(host, user=user, password=password)
    ssh.connect()
    return ssh


def check_step_completed(state, step_number: int) -> bool:
    """Vérifier si une étape est déjà complétée."""
    return state.get_step(step_number) is not None

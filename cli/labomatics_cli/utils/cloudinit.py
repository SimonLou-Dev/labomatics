"""Génération de cloud-init personnalisé pour Proxmox (NoCloud datasource)."""

import yaml


def generate_cloudinit_userdata(
    ssh_pubkeys: str = "",
    password: str = "",
    dns_servers: str = "8.8.8.8 8.8.4.4",
    username: str = "root",
) -> str:
    """Générer user-data cloud-init YAML pour NoCloud."""

    ssh_keys = [k.strip() for k in ssh_pubkeys.split("\n") if k.strip()]
    dns_list = [s.strip() for s in dns_servers.split() if s.strip()]

    config = {
        "package_update": True,
        "package_upgrade": True,
    }

    # Packages adaptés au système
    config["packages"] = [
        "openssh-server",
        "openssh-client",
        "qemu-guest-agent",
        "curl",
        "wget",
    ]

    # Configuration utilisateur
    users = [
        {
            "name": username,
            "sudo": ["ALL=(ALL) NOPASSWD:ALL"],
            "shell": "/bin/bash",
            "lock_passwd": False,
        }
    ]

    if ssh_keys:
        users[0]["ssh_authorized_keys"] = ssh_keys

    if password:
        users[0]["passwd"] = password

    config["users"] = users

    # Groupe par défaut
    config["groups"] = ["wheel", "sudo"]

    # DNS via resolv_conf
    if dns_list:
        config["resolv_conf"] = {
            "nameservers": dns_list,
            "search": ["local"],
        }

    # Services
    config["runcmd"] = [
        "systemctl daemon-reload",
        "systemctl enable sshd",
        "systemctl start sshd",
        "systemctl enable qemu-guest-agent || true",
        "systemctl start qemu-guest-agent || true",
    ]

    lines = ["#cloud-config"]
    yaml_content = yaml.dump(
        config,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    lines.append(yaml_content)
    return "\n".join(lines)


def generate_cloudinit_network(
    vm_ip: str,
    gateway: str,
    dns_servers: str = "8.8.8.8 8.8.4.4",
) -> str:
    """Générer network-config cloud-init YAML v2 pour NoCloud."""

    dns_list = [s.strip() for s in dns_servers.split() if s.strip()]

    config = {
        "version": 2,
        "ethernets": {
            "eth0": {
                "dhcp4": False,
                "addresses": [f"{vm_ip}/24"],
                "gateway4": gateway,
                "nameservers": {
                    "addresses": dns_list if dns_list else ["8.8.8.8", "8.8.4.4"],
                },
            }
        },
    }

    lines = ["#cloud-config"]
    yaml_content = yaml.dump(
        config,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    lines.append(yaml_content)
    return "\n".join(lines)


def generate_cloudinit_metadata(
    hostname: str = "labomatics", instance_id: str = None
) -> str:
    """Générer meta-data cloud-init YAML pour NoCloud."""
    if not instance_id:
        import uuid

        instance_id = str(uuid.uuid4())

    config = {
        "instance-id": instance_id,
        "local-hostname": hostname,
    }

    lines = ["#cloud-config"]
    yaml_content = yaml.dump(
        config,
        default_flow_style=False,
        sort_keys=False,
    )
    lines.append(yaml_content)
    return "\n".join(lines)

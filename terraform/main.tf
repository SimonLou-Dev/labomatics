terraform {
  required_version = ">= 1.0"
  required_providers {
    libvirt = {
      source  = "dmacvicar/libvirt"
      version = "~> 0.9"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

provider "libvirt" {
  uri = "qemu:///system"
}

# Réseau NAT interne pour communication entre VMs
resource "libvirt_network" "proxmox" {
  name      = "proxmox-lab-internal"
  autostart = true

  forward = {
    mode = "nat"
  }

  ips = [
    {
      address = "192.168.100.1"
      prefix  = 24
      dhcp = {
        start = "192.168.100.10"
        end   = "192.168.100.250"
      }
    }
  ]
}

# ISO Proxmox - On utilise le fichier directement sans le copier
locals {
  iso_file = var.iso_path
}

# Disques de démarrage pour pxmx1, pxmx2, pxmx3
resource "libvirt_volume" "boot_disks" {
  for_each = toset(["pxmx1", "pxmx2", "pxmx3"])

  name     = "${each.key}-boot.qcow2"
  pool     = var.pool_name
  capacity = var.boot_disk_size_gb * 1024 * 1024 * 1024

  target = {
    format = { type = "qcow2" }
  }

}

# Disque supplémentaire pour pxmx1
resource "libvirt_volume" "pxmx1_extra" {
  name     = "pxmx1-extra.qcow2"
  pool     = var.pool_name
  capacity = var.extra_disk_size_gb * 1024 * 1024 * 1024

  target = {
    format = { type = "qcow2" }
  }

}

# VM Proxmox 1 (avec 2 disques)
resource "libvirt_domain" "pxmx1" {
  name        = "pxmx1"
  type        = "kvm"
  memory      = var.vm_memory
  memory_unit = "MiB"
  vcpu        = var.vm_vcpu
  autostart   = true
  running     = true

  cpu = {
    mode = "host-passthrough"
  }

  os = {
    type         = "hvm"
    type_arch    = "x86_64"
    type_machine = "pc"
    boot_devices = [{ dev = "cdrom" }]
  }

  devices = {
    disks = [
      {
        driver = { name = "qemu", type = "qcow2" }
        source = {
          file = { file = libvirt_volume.boot_disks["pxmx1"].path }
        }
        target = {
          dev = "vda"
          bus = "virtio"
        }
      },
      {
        driver = { name = "qemu", type = "qcow2" }
        source = {
          file = { file = libvirt_volume.pxmx1_extra.path }
        }
        target = {
          dev = "vdb"
          bus = "virtio"
        }
      },
      {
        device = "cdrom"
        source = {
          file = { file = local.iso_file }
        }
        target = {
          dev = "hda"
          bus = "ide"
        }
        readonly = true
      }
    ]

    interfaces = [
      {
        model = { type = "virtio" }
        source = { network = { network = var.lan_network } }
        mac = { address = "52:54:00:12:34:01" }
      },
      {
        model = { type = "virtio" }
        source = { network = { network = "proxmox-lab-internal" } }
        mac = { address = "52:54:00:12:34:11" }
      }
    ]

    graphics = [
      {
        vnc = { autoport = "yes" }
      }
    ]
  }

  lifecycle {
    ignore_changes = [devices]
  }

  depends_on = [libvirt_volume.boot_disks, libvirt_volume.pxmx1_extra]
}

# VM Proxmox 2 (1 disque)
resource "libvirt_domain" "pxmx2" {
  name        = "pxmx2"
  type        = "kvm"
  memory      = var.vm_memory
  memory_unit = "MiB"
  vcpu        = var.vm_vcpu
  autostart   = true
  running     = true

  cpu = {
    mode = "host-passthrough"
  }

  os = {
    type         = "hvm"
    type_arch    = "x86_64"
    type_machine = "pc"
    boot_devices = [{ dev = "cdrom" }]
  }

  devices = {
    disks = [
      {
        driver = { name = "qemu", type = "qcow2" }
        source = {
          file = { file = libvirt_volume.boot_disks["pxmx2"].path }
        }
        target = {
          dev = "vda"
          bus = "virtio"
        }
      },
      {
        device = "cdrom"
        source = {
          file = { file = local.iso_file }
        }
        target = {
          dev = "hda"
          bus = "ide"
        }
        readonly = true
      }
    ]

    interfaces = [
      {
        model = { type = "virtio" }
        source = { network = { network = var.lan_network } }
        mac = { address = "52:54:00:12:34:02" }
      },
      {
        model = { type = "virtio" }
        source = { network = { network = "proxmox-lab-internal" } }
        mac = { address = "52:54:00:12:34:12" }
      }
    ]

    graphics = [
      {
        vnc = { autoport = "yes" }
      }
    ]
  }

  lifecycle {
    ignore_changes = [devices]
  }

  depends_on = [libvirt_volume.boot_disks]
}

# VM Proxmox 3 (1 disque)
resource "libvirt_domain" "pxmx3" {
  name        = "pxmx3"
  type        = "kvm"
  memory      = var.vm_memory
  memory_unit = "MiB"
  vcpu        = var.vm_vcpu
  autostart   = true
  running     = true

  cpu = {
    mode = "host-passthrough"
  }

  os = {
    type         = "hvm"
    type_arch    = "x86_64"
    type_machine = "pc"
    boot_devices = [{ dev = "cdrom" }]
  }

  devices = {
    disks = [
      {
        driver = { name = "qemu", type = "qcow2" }
        source = {
          file = { file = libvirt_volume.boot_disks["pxmx3"].path }
        }
        target = {
          dev = "vda"
          bus = "virtio"
        }
      },
      {
        device = "cdrom"
        source = {
          file = { file = local.iso_file }
        }
        target = {
          dev = "hda"
          bus = "ide"
        }
        readonly = true
      }
    ]

    interfaces = [
      {
        model = { type = "virtio" }
        source = { network = { network = var.lan_network } }
        mac = { address = "52:54:00:12:34:03" }
      },
      {
        model = { type = "virtio" }
        source = { network = { network = "proxmox-lab-internal" } }
        mac = { address = "52:54:00:12:34:13" }
      }
    ]

    graphics = [
      {
        vnc = { autoport = "yes" }
      }
    ]
  }

  lifecycle {
    ignore_changes = [devices]
  }

  depends_on = [libvirt_volume.boot_disks]
}

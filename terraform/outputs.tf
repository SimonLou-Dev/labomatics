output "proxmox_network" {
  description = "Réseau Proxmox LAB (Bridge)"
  value = {
    name      = libvirt_network.proxmox.name
    type      = "bridge"
    interface = var.bridge_interface
    note      = "VMs sur le même réseau que le PC hôte"
  }
}

output "vms" {
  description = "Configurations des VMs"
  value = {
    pxmx1 = {
      name   = "pxmx1"
      vcpu   = var.vm_vcpu
      memory = "${var.vm_memory} MiB"
      disks  = "${var.boot_disk_size_gb}GB + ${var.extra_disk_size_gb}GB"
      mac    = "52:54:00:12:34:01"
    }
    pxmx2 = {
      name   = "pxmx2"
      vcpu   = var.vm_vcpu
      memory = "${var.vm_memory} MiB"
      disks  = "${var.boot_disk_size_gb}GB"
      mac    = "52:54:00:12:34:02"
    }
    pxmx3 = {
      name   = "pxmx3"
      vcpu   = var.vm_vcpu
      memory = "${var.vm_memory} MiB"
      disks  = "${var.boot_disk_size_gb}GB"
      mac    = "52:54:00:12:34:03"
    }
  }
}

output "access_guide" {
  description = "Guide d'accès aux VMs"
  value       = <<-EOT
    === Commandes utiles ===

    Accéder à la console:
      virsh console pxmx1
      virsh console pxmx2
      virsh console pxmx3

    Obtenir les adresses IP (après DHCP):
      virsh net-dhcp-leases proxmox-lab-net

    Vérifier le statut:
      virsh list
      virsh dominfo pxmx1

    Accéder à Proxmox (après installation):
      https://192.168.122.XXX:8006

    Supprimer les VMs:
      virsh destroy pxmx1 pxmx2 pxmx3
      virsh undefine pxmx1 pxmx2 pxmx3
      virsh net-destroy proxmox-lab-net
  EOT
}

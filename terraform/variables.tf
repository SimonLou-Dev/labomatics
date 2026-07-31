variable "vm_memory" {
  description = "Mémoire RAM (MB) pour chaque VM"
  type        = number
  default     = 4096
}

variable "vm_vcpu" {
  description = "Nombre de vCPU pour chaque VM"
  type        = number
  default     = 4
}

variable "boot_disk_size_gb" {
  description = "Taille du disque de boot (GB) pour toutes les VMs"
  type        = number
  default     = 50
}

variable "extra_disk_size_gb" {
  description = "Taille du disque supplémentaire (GB) pour pxmx1"
  type        = number
  default     = 100
}

variable "network_subnet" {
  description = "Sous-réseau NAT pour les VMs"
  type        = string
  default     = "192.168.122.0/24"
}

variable "iso_path" {
  description = "Chemin vers l'ISO Proxmox"
  type        = string
  default     = "/home/virtu/iso/proxmox-ve_9.1-1.iso"
}

variable "pool_name" {
  description = "Nom du pool libvirt existant"
  type        = string
  default     = "pool"
}

variable "bridge_interface" {
  description = "Interface réseau à utiliser pour le bridge (ex: eth0, wlan0)"
  type        = string
  default     = "eth0"
}

variable "lan_network" {
  description = "Réseau libvirt existant pour le LAN (ex: lan-bridge, lanA, lanB)"
  type        = string
  default     = "lan-bridge"
}

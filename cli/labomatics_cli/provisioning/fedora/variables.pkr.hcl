# ── Connexion Proxmox ──────────────────────────────────────────────────────────
variable "proxmox_api_url" {
  type        = string
  description = "URL API Proxmox (ex: https://192.168.1.10:8006/api2/json)"
}

variable "proxmox_api_token_id" {
  type        = string
  description = "Token ID Proxmox (ex: root@pam!packer)"
}

variable "proxmox_api_token_secret" {
  type        = string
  sensitive   = true
  description = "Secret du token API Proxmox"
}

# ── Cible Proxmox ──────────────────────────────────────────────────────────────
variable "proxmox_node" {
  type        = string
  description = "Nœud Proxmox cible (ex: pve-a-1)"
}

variable "vm_id" {
  type        = string
  description = "VMID de la template à créer (ex: 9100)"
}

variable "vm_name" {
  type        = string
  default     = "pkr-ubuntu"
  description = "Nom de la VM template"
}

variable "storage_pool" {
  type        = string
  description = "Stockage partagé pour le disque VM (ex: zfs-store, ceph)"
}

variable "iso_storage_pool" {
  type        = string
  default     = "local"
  description = "Stockage contenant l'ISO Ubuntu"
}

variable "iso_file" {
  type        = string
  description = "Chemin de l'ISO Ubuntu dans Proxmox (ex: local:iso/ubuntu-24.04-live-server-amd64.iso)"
}

variable "bridge" {
  type        = string
  default     = "vmbr0"
  description = "Bridge réseau Proxmox"
}

# ── Identifiants VM ────────────────────────────────────────────────────────────
variable "custom_user" {
  type        = string
  default     = "ubuntu"
  description = "Utilisateur créé dans la VM"
}

variable "custom_password" {
  type        = string
  sensitive   = true
  default     = "ubuntu"
  description = "Mot de passe de l'utilisateur (et SSH pendant le build)"
}

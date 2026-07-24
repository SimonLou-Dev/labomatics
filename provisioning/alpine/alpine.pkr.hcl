source "proxmox-iso" "pkr-alpine-1" {
  proxmox_url              = var.proxmox_api_url
  username                 = var.proxmox_api_token_id
  token                    = var.proxmox_api_token_secret
  insecure_skip_tls_verify = true

  node                 = var.proxmox_node
  vm_id                = var.vm_id
  vm_name              = var.vm_name
  template_description = "Alpine Server - built by Packer / labomatics"

  iso_file         = var.iso_file
  iso_storage_pool = var.iso_storage_pool
  unmount_iso      = true
  qemu_agent       = true

  scsi_controller = "virtio-scsi-pci"
  cores           = "2"
  sockets         = "1"
  memory          = "2048"

  vga {
    type = "virtio"
  }

  disks {
    disk_size    = "5G"
    format       = "raw"
    storage_pool = var.storage_pool
    type         = "virtio"
  }

  network_adapters {
    model    = "virtio"
    bridge   = var.bridge
    firewall = "false"
  }

  boot_command = [
    "<wait10>",
    "root<enter><wait3>",
    "ifconfig eth0 up && udhcpc -i eth0<enter><wait10>",
    "wget http://{{ .HTTPIP }}:{{ .HTTPPort }}/alpine/answers -O /root/answers<enter><wait5>",
    "setup-alpine -f /root/answers<enter><wait15>",
    "${var.custom_password}<enter><wait5>",
    "${var.custom_password}<enter><wait10>",
    "${var.custom_user}<enter><wait2>",
    "<enter><wait2>",
    "${var.custom_password}<enter><wait2>",
    "${var.custom_password}<enter><wait2>",
    "<enter><wait2>",
    "y<enter><wait60>",
    "mount /dev/vda3 /mnt && mount --bind /proc /mnt/proc && mount --bind /dev /mnt/dev && cp /etc/resolv.conf /mnt/etc/<enter><wait2>",
    "chroot /mnt apk add --no-cache qemu-guest-agent<enter><wait20>",
    "chroot /mnt rc-update add qemu-guest-agent<enter><wait2>",
    "echo 'PermitRootLogin yes' >> /mnt/etc/ssh/sshd_config<enter><wait2>",
    "umount /mnt/proc /mnt/dev /mnt<enter><wait2>",
    "reboot<enter>",
    "<wait30>"
  ]

  boot                   = "c"
  boot_wait              = "6s"
  communicator           = "ssh"
  http_directory         = "./http"
  http_port_min          = 8098
  http_port_max          = 8108
  ssh_username           = "root"
  ssh_password           = var.custom_password
  ssh_timeout            = "15m"
  ssh_pty                = true
  ssh_handshake_attempts = 20
}

build {
  name    = "alpine"
  sources = ["source.proxmox-iso.pkr-alpine-1"]

  provisioner "shell" {
    inline = [
      "apk update",
      "apk add sudo kbd-bkeymaps",
      "setup-keymap fr fr",
      "rc-update add loadkmap",
      "adduser ${var.custom_user} wheel",
      "echo '%wheel ALL=(ALL) NOPASSWD: ALL' > /etc/sudoers.d/wheel",
      "sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config",
      "rc-service sshd restart"
    ]
  }
}

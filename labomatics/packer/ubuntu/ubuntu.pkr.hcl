source "proxmox-iso" "ubuntu" {
  proxmox_url              = var.proxmox_api_url
  username                 = var.proxmox_api_token_id
  token                    = var.proxmox_api_token_secret
  insecure_skip_tls_verify = true

  node                 = var.proxmox_node
  vm_id                = var.vm_id
  vm_name              = var.vm_name
  template_description = "Ubuntu Server - built by Packer / labomatics"

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
    disk_size    = "10G"
    format       = "raw"
    storage_pool = var.storage_pool
    type         = "virtio"
  }

  network_adapters {
    model    = "virtio"
    bridge   = var.bridge
    firewall = "false"
  }

  # Ubuntu live server : grub pour injecter autoinstall via HTTP
  boot_command = [
    "<wait5>",
    "c<wait3>",
    "linux /casper/vmlinuz quiet autoinstall ds=nocloud-net\\;s=http://{{ .HTTPIP }}:{{ .HTTPPort }}/ubuntu/ ---<enter><wait3>",
    "initrd /casper/initrd<enter><wait3>",
    "boot<enter>"
  ]

  boot      = "c"
  boot_wait = "5s"

  http_content = {
    "/ubuntu/user-data" = <<-EOF
      #cloud-config
      autoinstall:
        version: 1
        locale: fr_FR.UTF-8
        keyboard:
          layout: fr
        network:
          network:
            version: 2
            ethernets:
              ens18:
                dhcp4: true
        storage:
          layout:
            name: direct
        identity:
          hostname: ubuntu-server
          username: ${var.custom_user}
          # Mot de passe défini via late-commands/chpasswd — hash dummy ici
          password: "!"
        ssh:
          install-server: true
          allow-pw: true
        packages:
          - qemu-guest-agent
          - sudo
        late-commands:
          - echo '${var.custom_user}:${var.custom_password}' | chpasswd --root /target
          - echo '${var.custom_user} ALL=(ALL) NOPASSWD:ALL' > /target/etc/sudoers.d/${var.custom_user}
          - chmod 440 /target/etc/sudoers.d/${var.custom_user}
          - curtin in-target -- systemctl enable qemu-guest-agent
      EOF
    "/ubuntu/meta-data" = "instance-id: ubuntu-server\nlocal-hostname: ubuntu-server\n"
  }

  http_port_min = 8098
  http_port_max = 8108

  communicator           = "ssh"
  ssh_username           = var.custom_user
  ssh_password           = var.custom_password
  ssh_timeout            = "30m"
  ssh_pty                = true
  ssh_handshake_attempts = 30
}

build {
  name    = "ubuntu"
  sources = ["source.proxmox-iso.ubuntu"]

  provisioner "shell" {
    inline = [
      "sudo rm -f /etc/ssh/ssh_host_*",
      "sudo truncate -s 0 /etc/machine-id",
      "sudo apt-get -y autoremove --purge",
      "sudo apt-get -y clean",
      "sudo cloud-init clean",
      "sudo sync"
    ]
  }
}

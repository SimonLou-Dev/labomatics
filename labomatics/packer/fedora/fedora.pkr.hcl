source "proxmox-iso" "pkr-fedora-1" {
  proxmox_url              = var.proxmox_api_url
  username                 = var.proxmox_api_token_id
  token                    = var.proxmox_api_token_secret
  insecure_skip_tls_verify = true

  node                 = var.proxmox_node
  vm_id                = var.vm_id
  vm_name              = var.vm_name
  template_description = "Fedora Server - built by Packer / labomatics"

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

  # Fedora : édition du menu GRUB pour injecter le kickstart
  boot_command = [
    "<wait5>",
    "<up><enter",
    "e<wait>",
    "<down><down><end>",
    " inst.ks=http://{{ .HTTPIP }}:{{ .HTTPPort }}/fedora/ks.cfg inst.text<wait>",
    "<f10>"
  ]

  boot                   = "c"
  boot_wait              = "5s"
  communicator           = "ssh"
  http_content = {
    "/fedora/ks.cfg" = <<-EOF
      text
      cdrom

      lang fr_FR.UTF-8
      keyboard fr
      timezone UTC --utc

      rootpw --plaintext ${var.custom_password}
      user --name=${var.custom_user} --password=${var.custom_password} --groups=wheel --plaintext

      firewall --disabled
      selinux --permissive
      firstboot --disabled

      bootloader --location=mbr --driveorder=vda
      clearpart --all --drives=vda --initlabel
      autopart --type=plain

      %packages
      @^server-product-environment
      qemu-guest-agent
      sudo
      -firewalld
      %end

      %post
      systemctl enable qemu-guest-agent

      echo '${var.custom_user} ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/${var.custom_user}
      chmod 440 /etc/sudoers.d/${var.custom_user}

      sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
      sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
      %end

      reboot
      EOF
  }
  http_port_min          = 8098
  http_port_max          = 8108
  ssh_username           = var.custom_user
  ssh_password           = var.custom_password
  ssh_timeout            = "45m"
  ssh_pty                = true
  ssh_handshake_attempts = 30
}

build {
  name    = "fedora"
  sources = ["source.proxmox-iso.pkr-fedora-1"]

  provisioner "shell" {
    inline = [
      "sudo dnf clean all",
      "sudo rm -f /etc/ssh/ssh_host_*",
      "sudo truncate -s 0 /etc/machine-id",
      "sudo sync"
    ]
  }
}

#!/bin/bash
# À exécuter sur le nœud Proxmox en root
# Crée un template VM OpenWrt depuis l'image disk officielle x86_64
#
# Usage: ./build-openwrt-vm-template.sh [version] [vmid] [storage] [root_password]
# Ex:    ./build-openwrt-vm-template.sh 23.05.5 90200 zfs-store openwrt

set -euo pipefail

OPENWRT_VERSION="${1:-23.05.5}"
VMID="${2:-90200}"
STORAGE="${3:-local-lvm}"
ROOT_PASSWORD="${4:-openwrt}"

IMG_BASE="openwrt-${OPENWRT_VERSION}-x86-64-generic-ext4-combined"
IMG_URL="https://downloads.openwrt.org/releases/${OPENWRT_VERSION}/targets/x86/64/${IMG_BASE}.img.gz"
PKG_BASE="https://downloads.openwrt.org/releases/${OPENWRT_VERSION}/targets/x86/64/packages"

# --- Vérification template existant ---
if qm status "${VMID}" &>/dev/null; then
  read -rp "⚠ La VM ${VMID} existe déjà. La remplacer ? [y/N] " CONFIRM
  case "$CONFIRM" in
    [yY]) qm destroy "${VMID}" --purge ;;
    *)    echo "Annulé."; exit 0 ;;
  esac
fi

# --- Téléchargement image ---
echo "==> Téléchargement OpenWrt ${OPENWRT_VERSION}..."
rm -f "/tmp/${IMG_BASE}.img.gz" "/tmp/${IMG_BASE}.img"
wget -q --show-progress -O "/tmp/${IMG_BASE}.img.gz" "${IMG_URL}"

# Les images combined sont gzip + partitions concaténées.
# gzip retourne 2 ("trailing garbage") → normal, image valide.
gzip -d "/tmp/${IMG_BASE}.img.gz" || { RC=$?; [ $RC -eq 2 ] || exit $RC; }

# --- Montage ---
echo "==> Montage de l'image (partition root = p2)..."
LOOP=$(losetup -f)
losetup -P "${LOOP}" "/tmp/${IMG_BASE}.img"
mkdir -p /tmp/openwrt-mnt
mount "${LOOP}p2" /tmp/openwrt-mnt

cleanup() {
  umount /tmp/openwrt-mnt 2>/dev/null || true
  losetup -d "${LOOP}" 2>/dev/null || true
}
trap cleanup EXIT

# --- Mot de passe root ---
echo "==> Mot de passe root..."
PWD_HASH=$(openssl passwd -1 "${ROOT_PASSWORD}")
sed -i "s|^root:[^:]*:|root:${PWD_HASH}:|" /tmp/openwrt-mnt/etc/shadow 2>/dev/null || \
  sed -i "s|^root:[^:]*:|root:${PWD_HASH}:|" /tmp/openwrt-mnt/etc/passwd

# --- SSH (dropbear) ---
echo "==> Configuration SSH..."
mkdir -p /tmp/openwrt-mnt/etc/dropbear
printf 'DROPBEAR_EXTRA_ARGS="-p 22"\n' > /tmp/openwrt-mnt/etc/dropbear/dropbear.conf
ln -sf ../init.d/dropbear /tmp/openwrt-mnt/etc/rc.d/S50dropbear 2>/dev/null || true

# --- HTTPS : certificat auto-signé ---
echo "==> Génération du certificat HTTPS..."
openssl req -x509 -newkey rsa:2048 \
  -keyout /tmp/openwrt-mnt/etc/uhttpd.key \
  -out    /tmp/openwrt-mnt/etc/uhttpd.crt \
  -days 3650 -nodes -subj "/C=FR/O=OpenWrt/CN=openwrt" 2>/dev/null
chmod 600 /tmp/openwrt-mnt/etc/uhttpd.key

# --- qemu-guest-agent ---
echo "==> Installation de qemu-guest-agent..."
QEMU_GA_FILE=$(wget -q "${PKG_BASE}/Packages.gz" -O - | zcat 2>/dev/null \
  | awk '/^Package: qemu-ga$/{p=1} p && /^Filename:/{print $2; exit}') || QEMU_GA_FILE=""

if [ -n "${QEMU_GA_FILE}" ]; then
  wget -q "${PKG_BASE}/${QEMU_GA_FILE}" -O /tmp/qemu-ga.ipk
  # Un .ipk est une archive ar contenant data.tar.gz
  cd /tmp && ar x qemu-ga.ipk data.tar.gz
  tar -xzf /tmp/data.tar.gz -C /tmp/openwrt-mnt/
  rm -f /tmp/data.tar.gz /tmp/control.tar.gz /tmp/debian-binary /tmp/qemu-ga.ipk
  cd - >/dev/null
  # Activer au boot (nom du service variable selon version)
  ln -sf /etc/init.d/qemu-guest-agent /tmp/openwrt-mnt/etc/rc.d/S95qemu-guest-agent 2>/dev/null || \
    ln -sf /etc/init.d/qemu-ga        /tmp/openwrt-mnt/etc/rc.d/S95qemu-ga        2>/dev/null || true
  echo "    OK"
else
  echo "    WARN: paquet qemu-ga introuvable dans les repos ${OPENWRT_VERSION}"
fi

# --- Script uci-defaults : lecteur NoCloud + réseau + HTTPS ---
echo "==> Injection du script uci-defaults..."
mkdir -p /tmp/openwrt-mnt/etc/uci-defaults
cat > /tmp/openwrt-mnt/etc/uci-defaults/99-proxmox-init <<'UCIEOF'
#!/bin/sh
# Lecteur cloud-init NoCloud pour OpenWrt (format Proxmox v1)
# Applique hostname + réseau depuis le drive injecté par Proxmox

CIDEV="/dev/sr0"

mkdir -p /tmp/cidata
mount -o ro "$CIDEV" /tmp/cidata 2>/dev/null || CIDEV=""

if [ -n "$CIDEV" ]; then
  # Hostname depuis user-data
  if [ -f /tmp/cidata/user-data ]; then
    HN=$(grep '^hostname:' /tmp/cidata/user-data | awk '{print $2}')
    [ -n "$HN" ] && uci set system.@system[0].hostname="$HN"
  fi

  # Réseau depuis network-config
  # Format Proxmox v1 : address/netmask séparés, valeurs single-quotées
  if [ -f /tmp/cidata/network-config ]; then
    uci delete network.lan  2>/dev/null
    uci delete network.wan  2>/dev/null
    uci delete network.wan6 2>/dev/null

    awk '
      /- type: physical/ {
        if (iface) print iface, addr, mask, gw
        iface=""; addr=""; mask=""; gw=""; skip=0
      }
      /- type: nameserver/ {
        if (iface) { print iface, addr, mask, gw; iface="" }
        skip=1
      }
      skip       { next }
      $1=="name:"    { iface=$2; gsub(/[\047"]/, "", iface) }
      $1=="address:" { addr=$2;  gsub(/[\047"]/, "", addr)  }
      $1=="netmask:" { mask=$2;  gsub(/[\047"]/, "", mask)  }
      $1=="gateway:" { gw=$2;    gsub(/[\047"]/, "", gw)    }
      END { if (iface) print iface, addr, mask, gw }
    ' /tmp/cidata/network-config | while read IFACE ADDR MASK GW; do

      if [ -n "$GW" ]; then NAME="wan"
      else NAME="lan"
      fi

      uci set network.$NAME=interface
      uci set network.$NAME.proto='static'
      uci set network.$NAME.ipaddr="$ADDR"
      uci set network.$NAME.netmask="$MASK"
      uci set network.$NAME.device="$IFACE"
      [ -n "$GW" ] && uci set network.$NAME.gateway="$GW"

    done

    uci commit network
    /etc/init.d/network restart
  fi

  uci commit system
  umount /tmp/cidata 2>/dev/null || true
fi

# uhttpd : écoute sur toutes les interfaces + HTTPS avec le cert du template
uci set uhttpd.main.listen_http='0.0.0.0:80'
uci set uhttpd.main.listen_https='0.0.0.0:443'
if [ -f /etc/uhttpd.crt ] && [ -f /etc/uhttpd.key ]; then
  uci set uhttpd.main.cert='/etc/uhttpd.crt'
  uci set uhttpd.main.key='/etc/uhttpd.key'
  uci set uhttpd.main.redirect_https=1
fi
uci commit uhttpd
/etc/init.d/uhttpd enable 2>/dev/null || true
/etc/init.d/uhttpd restart 2>/dev/null || true

# Firewall : autoriser HTTP/HTTPS depuis WAN (INPUT bloqué par défaut)
uci add firewall rule
uci set firewall.@rule[-1].name='Allow-Web-WAN'
uci set firewall.@rule[-1].src='wan'
uci set firewall.@rule[-1].dest_port='80 443'
uci set firewall.@rule[-1].proto='tcp'
uci set firewall.@rule[-1].target='ACCEPT'
uci commit firewall
/etc/init.d/firewall reload 2>/dev/null || true

# Copie permanente pour re-exécution sans rebuild template
cp "$0" /etc/proxmox-init.sh 2>/dev/null || true

exit 0
UCIEOF
chmod +x /tmp/openwrt-mnt/etc/uci-defaults/99-proxmox-init

# --- Démontage (aussi via trap EXIT) ---
echo "==> Démontage..."
umount /tmp/openwrt-mnt
losetup -d "${LOOP}"
trap - EXIT

# --- Création VM Proxmox ---
echo "==> Création de la VM template (VMID ${VMID})..."
qm create "${VMID}" \
  --name "openwrt-${OPENWRT_VERSION}" \
  --memory 256 \
  --cores 1 \
  --net0 virtio,bridge=vmbr0 \
  --serial0 socket \
  --vga serial0 \
  --ostype l26 \
  --description "OpenWrt ${OPENWRT_VERSION} x86_64 - built $(date +%Y-%m-%d)"

echo "==> Import du disque..."
qm importdisk "${VMID}" "/tmp/${IMG_BASE}.img" "${STORAGE}"
qm set "${VMID}" \
  --virtio0 "${STORAGE}:vm-${VMID}-disk-0,discard=on,iothread=1" \
  --boot order=virtio0

echo "==> Conversion en template..."
qm template "${VMID}"

rm -f "/tmp/${IMG_BASE}.img"

echo ""
echo "Template prêt : VM ${VMID} (openwrt-${OPENWRT_VERSION})"
echo "Dans infra.yaml : template_vmid: ${VMID}"

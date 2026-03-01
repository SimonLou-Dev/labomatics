## Activer le NAT (masquerading LAN → WAN)

Le NAT permet aux machines sur le réseau LAN/VXLAN d'accéder à Internet via le WAN.

**Via UCI (SSH) :**

```bash
# Vérifier que le masquerading est activé sur la zone WAN (actif par défaut)
uci show firewall | grep masq

# Si désactivé, l'activer :
uci set firewall.@zone[1].masq='1'
uci commit firewall
/etc/init.d/firewall reload
```

**Vérifier que le forwarding LAN → WAN est autorisé :**

```bash
uci show firewall | grep -A5 'forwarding'
# La règle lan → wan doit exister avec target ACCEPT
```

**Via LuCI :**
`Network` → `Firewall` → zone `wan` → cocher `Masquerading`
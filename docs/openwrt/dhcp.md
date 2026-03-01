## Activer le serveur DHCP dans votre LAB


### Via UCI (SSH)

```bash
uci set dhcp.lan.interface='lan'
uci set dhcp.lan.start='100'
uci set dhcp.lan.limit='50'
uci set dhcp.lan.leasetime='12h'
uci commit dhcp
/etc/init.d/dnsmasq restart
```

Cela distribue les IPs `10.200.0.100` → `10.200.0.149` sur l'interface LAN.

### Via interface web
`Network` → `Interfaces` → `lan` → `Edit` → onglet `DHCP Server` → `Set up DHCP server`

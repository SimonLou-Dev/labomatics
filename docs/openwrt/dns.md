## Configurer le DNS

Le résolveur DNS par défaut est `dnsmasq`. Vous pouvez changer les serveurs upstream :

**Via UCI :**

```bash
# Utiliser Cloudflare + Google
uci set network.wan.dns='1.1.1.1 8.8.8.8'
uci commit network
/etc/init.d/network reload
```

**Ajouter un domaine local résolu par dnsmasq :**

```bash
uci add dhcp domain
uci set dhcp.@domain[-1].name='mon-service.lab'
uci set dhcp.@domain[-1].ip='10.200.0.10'
uci commit dhcp
/etc/init.d/dnsmasq reload
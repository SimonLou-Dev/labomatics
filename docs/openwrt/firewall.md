## Règles firewall courantes

### Autoriser un port entrant depuis le WAN

```bash
uci add firewall rule
uci set firewall.@rule[-1].name='Allow-MonService'
uci set firewall.@rule[-1].src='wan'
uci set firewall.@rule[-1].dest_port='8080'
uci set firewall.@rule[-1].proto='tcp'
uci set firewall.@rule[-1].target='ACCEPT'
uci commit firewall
/etc/init.d/firewall reload
```

### Redirection de port
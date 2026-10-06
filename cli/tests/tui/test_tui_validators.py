from labomatics_cli.tui import validators as v

V: dict = {}


def test_ip():
    """Ip accepte v4/v6 et refuse le reste."""
    assert v.Ip()("10.0.0.1", V) is None and v.Ip()("::1", V) is None
    assert v.Ip()("10.0.0.300", V) and v.Ip()("abc", V)


def test_cidr():
    """Cidr est strict et propose le vrai réseau."""
    assert v.Cidr()("10.10.0.0/16", V) is None
    assert "utilise 10.96.0.0/12" in v.Cidr()("10.96.0.1/12", V)
    assert v.Cidr()("10.10.0.0", V) and v.Cidr()("nope/16", V)


def test_cidr_max_prefix():
    """max_prefix borne la longueur du préfixe."""
    assert v.Cidr(max_prefix=23)("10.0.0.0/23", V) is None
    assert v.Cidr(max_prefix=23)("10.0.0.0/24", V)


def test_ip_range():
    """IpRange impose a-b, même version, début <= fin."""
    r = v.IpRange()
    assert r("10.0.0.10-10.0.0.50", V) is None and r("10.0.0.5-10.0.0.5", V) is None
    assert "inférieur" in r("10.0.0.50-10.0.0.10", V)
    assert r("10.0.0.10", V) and r("10.0.0.1-::1", V) and r("a-b", V)


def test_ip_or_range_and_cidr():
    """Les unions IP/plage et IP/CIDR choisissent la bonne branche."""
    assert (
        v.IpOrRange()("10.0.0.1", V) is None
        and v.IpOrRange()("10.0.0.1-10.0.0.9", V) is None
    )
    assert v.IpOrRange()("10.0.0.9-10.0.0.1", V)
    assert (
        v.IpOrCidr()("10.0.0.0/24", V) is None and v.IpOrCidr()("10.0.0.1", V) is None
    )
    assert v.IpOrCidr()("10.0.0.1/24", V)


def test_ip_in():
    """IpIn vérifie l'appartenance, les bords et ignore un champ source vide."""
    values = {"net": "10.0.0.0/24"}
    check = v.IpIn("net")
    assert check("10.0.0.10", values) is None
    assert check("10.1.0.10", values)
    assert check("10.0.0.0", values) and check("10.0.0.255", values)
    assert v.IpIn("net", exclude_edges=False)("10.0.0.0", values) is None
    assert check("10.0.0.10-10.0.0.300", values) and check("10.0.0.10-10.0.1.5", values)
    assert check("10.0.0.10-10.0.0.50", values) is None
    assert check("10.9.9.9", {}) is None and check("10.9.9.9", {"net": "oops"}) is None


def test_no_overlap():
    """NoOverlap refuse un CIDR qui chevauche les champs cités."""
    values = {"a": "10.0.0.0/16", "b": ["192.168.0.0/24"]}
    check = v.NoOverlap("a", "b")
    assert check("172.16.0.0/12", values) is None
    assert "10.0.0.0/16" in check("10.0.5.0/24", values)
    assert check("192.168.0.0/16", values)
    assert check("garbage", values) is None


def test_hosts():
    """Hostname, Host et Domain."""
    assert (
        v.Hostname()("pve.local", V) is None
        and v.Hostname()("10.0.0.999", V)
        and v.Hostname()("bad host", V)
    )
    assert (
        v.Host()("pve-01.lab", V) is None
        and v.Host()("192.168.1.1", V) is None
        and v.Host()("pve local", V)
    )
    assert (
        v.Domain()("lab.example.com", V) is None and v.Domain()("pve.local", V) is None
    )
    assert v.Domain()("localhost", V) and v.Domain()("10.0.0.1", V)


def test_url_email():
    """Url (schémas) et Email."""
    assert v.Url()("https://pve.lab:8006", V) is None
    assert (
        v.Url()("http://pve.lab", V)
        and v.Url()("https://", V)
        and v.Url()("https://h:99999", V)
    )
    assert v.Url(("http", "https"))("http://pve.lab", V) is None
    assert v.Email()("a@b.fr", V) is None and v.Email()("a@b", V) and v.Email()("x", V)


def test_numbers():
    """Port, IntRange et GreaterThan."""
    assert (
        v.Port()("8006", V) is None
        and v.Port()("0", V)
        and v.Port()("70000", V)
        and v.Port()("abc", V)
    )
    assert (
        v.IntRange(1, 5)("3", V) is None
        and v.IntRange(1, 5)("0", V)
        and v.IntRange(max=5)("6", V)
    )
    assert v.IntRange()("x", V)
    gt = v.GreaterThan("low")
    assert (
        gt("10", {"low": "5"}) is None
        and gt("5", {"low": "5"})
        and gt("x", {"low": "5"})
    )
    assert gt("1", {}) is None


def test_text():
    """Length, Regex et AllOf."""
    assert (
        v.Length(3)("ab", V)
        and v.Length(0, 2)("abc", V)
        and v.Length(1, 3)("ab", V) is None
    )
    assert v.Regex(r"[a-z]+", "minuscules")("ABC", V) == "minuscules"
    assert v.AllOf(v.Length(1), v.Ip())("x", V) == v.Ip()("x", V)
    assert v.AllOf(v.Length(1))("x", V) is None


def test_formats():
    """SshPublicKey, LdapDn, LdapUrl et Uuid."""
    key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGq3 user@host"
    assert v.SshPublicKey()(key, V) is None and v.SshPublicKey()("ssh-dss AAAA", V)
    assert v.SshPublicKey()("ssh-rsa !!!", V)
    assert v.SshPublicKey()("ecdsa-sha2-nistp256 AAAAE2VjZHNh", V) is None
    assert v.LdapDn()("dc=example,dc=com", V) is None and v.LdapDn()("example.com", V)
    assert (
        v.LdapUrl()("ldaps://ldap.lab:636", V) is None
        and v.LdapUrl()("ldap://10.0.0.1", V) is None
    )
    assert v.LdapUrl()("http://x", V) and v.LdapUrl()("ldaps://x:99999", V)
    assert v.Uuid()("123e4567-e89b-12d3-a456-426614174000", V) is None and v.Uuid()(
        "nope", V
    )

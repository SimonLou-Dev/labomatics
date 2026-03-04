"""Tests unitaires pour labomatics.ip_pool (sans Proxmox)."""

from ipaddress import IPv4Address

import pytest

from labomatics.ip_pool import _parse_excluded_ips, _parse_excluded_networks


def test_parse_excluded_ips_simple():
    result = _parse_excluded_ips(["172.16.0.1", "172.16.0.2"])
    assert IPv4Address("172.16.0.1") in result
    assert IPv4Address("172.16.0.2") in result
    assert len(result) == 2


def test_parse_excluded_ips_range():
    result = _parse_excluded_ips(["172.16.0.1-172.16.0.5"])
    assert len(result) == 5
    assert IPv4Address("172.16.0.3") in result
    assert IPv4Address("172.16.0.6") not in result


def test_parse_excluded_ips_mixed():
    result = _parse_excluded_ips(["172.16.0.1-172.16.0.3", "172.16.0.10"])
    assert len(result) == 4
    assert IPv4Address("172.16.0.2") in result
    assert IPv4Address("172.16.0.10") in result


def test_parse_excluded_networks():
    result = _parse_excluded_networks(["10.100.0.0/24", "10.100.1.0/24"])
    from ipaddress import ip_network
    assert ip_network("10.100.0.0/24") in result
    assert ip_network("10.100.2.0/24") not in result


def test_parse_excluded_networks_invalid_ignored():
    result = _parse_excluded_networks(["not-a-network", "10.100.0.0/24"])
    assert len(result) == 1

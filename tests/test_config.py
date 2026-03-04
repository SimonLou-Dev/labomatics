"""Tests unitaires pour labomatics.config."""

import pytest
import yaml

from labomatics.config import FlavorConfig, InfraConfig


MINIMAL_CONFIG = {
    "openwrt": {
        "vmid_start": 10000,
        "template_vmid": 90200,
        "storage": "zfs-store",
        "network": {
            "zone_name": "esgilab",
            "wan_pool": {"network": "172.16.0.0/24", "gateway": "172.16.0.254"},
            "vxlan_pool": {"network": "10.100.0.0/12"},
        },
    }
}


def test_minimal_config():
    cfg = InfraConfig(**MINIMAL_CONFIG)
    assert cfg.openwrt.vmid_start == 10000
    assert cfg.openwrt.wan_bridge == "vmbr0"  # défaut


def test_get_flavor_found():
    cfg = InfraConfig(
        **MINIMAL_CONFIG,
        flavors={"CO1": FlavorConfig(cpu=4, ram=8192, disk=40)},
    )
    f = cfg.get_flavor("CO1")
    assert f.cpu == 4
    assert f.ram == 8192


def test_get_flavor_not_found_returns_first():
    cfg = InfraConfig(
        **MINIMAL_CONFIG,
        flavors={
            "CO1": FlavorConfig(cpu=4, ram=8192, disk=40),
            "CO2": FlavorConfig(cpu=8, ram=16384, disk=80),
        },
    )
    f = cfg.get_flavor("UNKNOWN")
    assert f.cpu == 4  # premier flavor


def test_get_flavor_empty_returns_unlimited():
    cfg = InfraConfig(**MINIMAL_CONFIG, flavors={})
    f = cfg.get_flavor("CO1")
    assert f.cpu == 0
    assert f.ram == 0
    assert f.disk == 0


def test_wan_pool_exclude_default():
    cfg = InfraConfig(**MINIMAL_CONFIG)
    assert cfg.openwrt.network.wan_pool.exclude == []


def test_quotad_defaults():
    cfg = InfraConfig(**MINIMAL_CONFIG)
    assert cfg.quotad.interval == 30
    assert cfg.quotad.action == "stop"

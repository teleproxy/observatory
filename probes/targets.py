"""Telegram datacenter IP addresses.

Extracted from teleproxy's mtproto-dc-table.c.  Used by probes to test
direct reachability of Telegram infrastructure.
"""

PRODUCTION_DCS = {
    1: {"ipv4": "149.154.175.50", "ipv6": "2001:0b28:f23d:f001::a"},
    2: {"ipv4": "149.154.167.51", "ipv6": "2001:067c:04e8:f002::a"},
    3: {"ipv4": "149.154.175.100", "ipv6": "2001:0b28:f23d:f003::a"},
    4: {"ipv4": "149.154.167.91", "ipv6": "2001:067c:04e8:f004::a"},
    5: {"ipv4": "91.108.56.100", "ipv6": "2001:0b28:f23f:f005::a"},
}

DC_PORT = 443

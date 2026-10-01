"""Network safety hooks for the validation venvs (installed via .pth).

1. IPv4-first getaddrinfo: this network has a black-holed IPv6 route to many
   CDNs; python tries IPv6 first and burns ~30s per connection (or hangs),
   while curl's happy-eyeballs is fast.
2. Global default socket timeout (75s): many upstream notebooks call
   requests.get()/urlopen without an explicit timeout; on this network a
   blocked CDN turns that into an infinite hang that stalls the whole
   marathon cell. With a default timeout the cell fails fast and is
   classified NETWORK instead of burning the wall clock.

Installed as ov_amd_ipv4_first.py + ov_amd_net_fix.pth by
ov_amd.environment.ensure_ipv4_first (a plain sitecustomize.py gets shadowed
by /usr/lib/python3.12/sitecustomize.py).
"""

import socket

_orig_getaddrinfo = socket.getaddrinfo

_DEFAULT_SOCKET_TIMEOUT = 75


def _ipv4_first_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    res = _orig_getaddrinfo(host, port, family, type, proto, flags)
    return sorted(res, key=lambda a: (0 if a[0] == socket.AF_INET else 1,))


if getattr(socket.getaddrinfo, "__module__", "") != __name__:
    socket.getaddrinfo = _ipv4_first_getaddrinfo
    socket.setdefaulttimeout(_DEFAULT_SOCKET_TIMEOUT)

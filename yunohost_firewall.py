# -*- coding: utf-8 -*-

""" License

    Copyright (C) 2013 YunoHost

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program; if not, see http://www.gnu.org/licenses

"""

""" yunohost_firewall.py

    Manage firewall rules
"""
import os
import sys
try:
    import miniupnpc
except ImportError:
    sys.stderr.write('Error: Yunohost CLI Require miniupnpc lib\n')
    sys.exit(1)
try:
    import yaml
except ImportError:
    sys.stderr.write('Error: Yunohost CLI Require yaml lib\n')
    sys.stderr.write('apt-get install python-yaml\n')
    sys.exit(1)
from yunohost import YunoHostError, win_msg


def firewall_allow(protocol=None, port=None, ipv6=None, upnp=False):
    """
    Allow connection port/protocol

    Keyword argument:
        port -- Port to open
        protocol -- Protocol associated with port
        upnp -- upnp
        ipv6 -- ipv6

    """
    port = int(port)
    if upnp:
        add_portmapping(protocol, upnp, ipv6, 'a')

    if 0 < port < 65536:
        if protocol == "Both":
            update_yml(port, 'TCP', 'a', ipv6, upnp)
            update_yml(port, 'UDP', 'a', ipv6, upnp)

        else:
            update_yml(port, protocol, 'a', ipv6, upnp)

        win_msg(_("Port successfully openned"))

    else:
        raise YunoHostError(22, _("Port not between 1 and 65535:") + str(port))

    return firewall_reload(upnp)


def firewall_disallow(protocol=None, port=None, ipv6=None, upnp=False):
    """
    Disallow connection

    Keyword argument:
        port -- Port to open
        protocol -- Protocol associated with port
        upnp -- upnp
        ipv6 -- ipv6

    """

    port = int(port)
    if protocol == "Both":
        update_yml(port, 'TCP', 'r', ipv6, upnp)
        update_yml(port, 'UDP', 'r', ipv6, upnp)
    else:
        update_yml(port, protocol, 'r', ipv6, upnp)
    win_msg(_("Port successfully closed"))

    return firewall_reload(upnp)


def firewall_list():
    """
    List all firewall rules


    """
    with open('/etc/yunohost/firewall.yml') as f:
        firewall = yaml.load(f)
    return firewall


def firewall_reload(upnp=False):
    """
    Reload all firewall rules

    Keyword argument:
        upnp -- upnp

    """
    with open('/etc/yunohost/firewall.yml', 'r') as f:
        firewall = yaml.load(f)

    os.system("iptables -P INPUT ACCEPT")
    os.system("iptables -F")
    os.system("iptables -X")
    os.system("iptables -A INPUT -m state --state ESTABLISHED -j ACCEPT")

    if 22 not in firewall['ipv4']['TCP']:
        update_yml(22, 'TCP', 'a', False)

    if os.path.exists("/proc/net/if_inet6"):
        os.system("ip6tables -P INPUT ACCEPT")
        os.system("ip6tables -F")
        os.system("ip6tables -X")
        os.system("ip6tables -A INPUT -m state --state ESTABLISHED -j ACCEPT")

    if 22 not in firewall['ipv6']['TCP']:
        update_yml(22, 'TCP', 'a', False)

    if upnp:
        remove_portmapping()

    add_portmapping('TCP', upnp, False, 'r')
    add_portmapping('UDP', upnp, False, 'r')

    if os.path.exists("/proc/net/if_inet6"):
        add_portmapping('TCP', upnp, True, 'r')
        add_portmapping('UDP', upnp, True, 'r')

    os.system("iptables -A INPUT -i lo -j ACCEPT")
    os.system("iptables -A INPUT -p icmp -j ACCEPT")
    os.system("iptables -P INPUT DROP")

    if os.path.exists("/proc/net/if_inet6"):
        os.system("ip6tables -A INPUT -i lo -j ACCEPT")
        os.system("ip6tables -A INPUT -p icmp -j ACCEPT")
        os.system("ip6tables -P INPUT DROP")

    os.system("service fail2ban restart")
    win_msg(_("Firewall successfully reloaded"))

    return firewall_list()


def update_yml(port=None, protocol=None, mode=None, ipv6=None, upnp=False):
    """
    Update firewall.yml
    Keyword arguments:
        protocol -- Protocol used
        port -- Port to open
        mode -- a=append r=remove
        ipv6 -- Boolean ipv6
        upnp -- Boolean upnp

    Return
        None
    """
    if ipv6:
        ip = 'ipv6'
    else:
        ip = 'ipv4'

    with open('/etc/yunohost/firewall.yml', 'r') as f:
        firewall = yaml.load(f)

    if mode == 'a':
        if port not in firewall[ip][protocol]:
            firewall[ip][protocol].append(port)
            if not ipv6 and upnp:
                firewall['UPNP']['ports'][protocol].append(port)
        elif not ipv6 and upnp:
            if port not in firewall['UPNP']['ports'][protocol]:
                firewall['UPNP']['ports'][protocol].append(port)
            else:
                raise YunoHostError(22, _("Port already openned :") + str(port))

        else:
            raise YunoHostError(22, _("Port already openned :") + str(port))

    else:
        if not ipv6 and upnp:
            if port in firewall['UPNP']['ports'][protocol]:
                firewall['UPNP']['ports'][protocol].remove(port)

            else:
                raise YunoHostError(22, _("Upnp redirection already deleted :") + str(port))
        elif not ipv6:
            if port in firewall['UPNP']['ports'][protocol]:
                firewall['UPNP']['ports'][protocol].remove(port)

            if port in firewall[ip][protocol]:
                firewall[ip][protocol].remove(port)

            else:
                raise YunoHostError(22, _("Port already closed :") + str(port))
        else:
            if port in firewall[ip][protocol]:
                firewall[ip][protocol].remove(port)

            else:
                raise YunoHostError(22, _("Port already closed :") + str(port))

    firewall[ip][protocol].sort()
    firewall['UPNP']['ports'][protocol].sort()

    os.system("mv /etc/yunohost/firewall.yml /etc/yunohost/firewall.yml.old")

    with open('/etc/yunohost/firewall.yml', 'w') as f:
        yaml.dump(firewall, f)


def add_portmapping(protocol=None, upnp=False, ipv6=None, mode=None,):
    """
    Send a port mapping rules to igd device
    Keyword arguments:
        protocol -- Protocol used
        upnp -- Boolean upnp
        ipv6 -- Boolean ipv6
        mode -- Add a rule (a) or reload all rules (r)

    Return
        None
    """
    if ipv6:
        os.system("ip6tables -P INPUT ACCEPT")
    else:
        os.system("iptables -P INPUT ACCEPT")

    if upnp and not ipv6  and mode == 'a':
        remove_portmapping()

    if ipv6:
        ip = 'ipv6'
    else:
        ip = 'ipv4'
    with open('/etc/yunohost/firewall.yml', 'r') as f:
        firewall = yaml.load(f)

    for i, port in enumerate(firewall[ip][protocol]):
        if ipv6:
            os.system("ip6tables -A INPUT -p " + protocol + " --dport " + str(port) + " -j ACCEPT")
        else:
            os.system("iptables -A INPUT -p " + protocol + " --dport " + str(port) + " -j ACCEPT")
        if upnp and not ipv6:
            if port in firewall['UPNP']['ports'][protocol]:
                upnpc = miniupnpc.UPnP()
                upnpc.discoverdelay = 200
                nbigd = upnpc.discover()
                if nbigd:
                    upnpc.selectigd()
                    upnpc.addportmapping(port, protocol, upnpc.lanaddr, port, 'yunohost firewall : port %u' % port, '')

    os.system("iptables -P INPUT DROP")


def remove_portmapping():
    """
    Remove all portmapping rules in the igd device
    Keyword arguments:
        None
    Return
        None
    """
    upnp = miniupnpc.UPnP()
    upnp.discoverdelay = 200
    nbigd = upnp.discover()
    if nbigd:
        try:
            upnp.selectigd()
        except:
            firewall_reload(False)
            raise YunoHostError(167, _("No upnp devices found"))
    else:
        firewall_reload(False)
        raise YunoHostError(22, _("Can't connect to the igd device"))

    # list the redirections :
    for i in xrange(100):
        p = upnp.getgenericportmapping(i)
        if p is None:
            break
        upnp.deleteportmapping(p[0], p[1])


def firewall_installupnp():
    """
    Add upnp cron


    """

    with open('/etc/yunohost/firewall.yml', 'r') as f:
        firewall = yaml.load(f)

    firewall['UPNP']['cron'] = True

    os.system("touch /etc/cron.d/yunohost-firewall")
    os.system("echo '*/50 * * * * root yunohost firewall reload -u --no-ldap >>/dev/null'>/etc/cron.d/yunohost-firewall")
    win_msg(_("UPNP cron installed"))

    os.system("mv /etc/yunohost/firewall.yml /etc/yunohost/firewall.yml.old")

    with open('/etc/yunohost/firewall.yml', 'w') as f:
        yaml.dump(firewall, f)


def firewall_removeupnp():
    """
    Remove upnp cron


    """
    with open('/etc/yunohost/firewall.yml', 'r') as f:
        firewall = yaml.load(f)

    firewall['UPNP']['cron'] = False

    try:
        os.remove("/etc/cron.d/yunohost-firewall")
    except:
        raise YunoHostError(167, _("UPNP cron was not installed!"))

    win_msg(_("UPNP cron removed"))

    os.system("mv /etc/yunohost/firewall.yml /etc/yunohost/firewall.yml.old")

    with open('/etc/yunohost/firewall.yml', 'w') as f:
        yaml.dump(firewall, f)


def firewall_checkupnp():
    """
    check if UPNP is install or not (0 yes 1 no)


    """
    with open('/etc/yunohost/firewall.yml', 'r') as f:
        firewall = yaml.load(f)

        if firewall['UPNP']['cron']:
            win_msg(_("UPNP is activated"))
        else:
            raise YunoHostError(167, _("UPNP not activated!"))


def firewall_stop():
    """
    Stop iptables and ip6tables


    """

    os.system("iptables -P INPUT ACCEPT")
    os.system("iptables -F")
    os.system("iptables -X")

    os.system("ip6tables -P INPUT ACCEPT")
    os.system("ip6tables -F")
    os.system("ip6tables -X")
    if(os.path.exists("/etc/cron.d/yunohost-firewall")):
        firewall_removeupnp()

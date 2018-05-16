#!/usr/bin/env python3
#
# Copyright (C) 2018 VyOS maintainers and contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 or later as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

import sys
import os

import jinja2

from vyos.config import Config
from vyos import ConfigError

config_file = r'/etc/ssh/sshd_config'

# Please be careful if you edit the template.
config_tmpl = """

### Autogenerated by vyos-config-ssh.py ###

# Non-configurable defaults
Protocol 2
HostKey /etc/ssh/ssh_host_rsa_key
HostKey /etc/ssh/ssh_host_dsa_key
HostKey /etc/ssh/ssh_host_ecdsa_key
HostKey /etc/ssh/ssh_host_ed25519_key
UsePrivilegeSeparation yes
KeyRegenerationInterval 3600
ServerKeyBits 1024
SyslogFacility AUTH
LoginGraceTime 120
StrictModes yes
RSAAuthentication yes
PubkeyAuthentication yes
IgnoreRhosts yes
RhostsRSAAuthentication no
HostbasedAuthentication no
PermitEmptyPasswords no
ChallengeResponseAuthentication no
X11Forwarding yes
X11DisplayOffset 10
PrintMotd no
PrintLastLog yes
TCPKeepAlive yes
Banner /etc/issue.net
Subsystem sftp /usr/lib/openssh/sftp-server
UsePAM yes
HostKey /etc/ssh/ssh_host_key

# Specifies whether sshd should look up the remote host name,
# and to check that the resolved host name for the remote IP
# address maps back to the very same IP address.
UseDNS {{ host_validation }}

# Specifies the port number that sshd listens on.  The default is 22.
# Multiple options of this type are permitted.
Port {{ port }}

# Gives the verbosity level that is used when logging messages from sshd
LogLevel {{ log_level }}

# Specifies whether root can log in using ssh
PermitRootLogin {{ allow_root }}

# Specifies whether password authentication is allowed
PasswordAuthentication {{ password_authentication }}

{% if listen_on -%}
# Specifies the local addresses sshd should listen on
{% for a in listen_on -%}
ListenAddress {{ a }}
{% endfor -%}
{% endif %}

{% if ciphers -%}
# Specifies the ciphers allowed. Multiple ciphers must be comma-separated.
#
# NOTE: As of now, there is no 'multi' node for 'ciphers', thus we have only one :/
Ciphers {{ ciphers | join(",") }}
{% endif %}

{% if mac -%}
# Specifies the available MAC (message authentication code) algorithms. The MAC
# algorithm is used for data integrity protection. Multiple algorithms must be
# comma-separated.
#
# NOTE: As of now, there is no 'multi' node for 'mac', thus we have only one :/
MACs {{ mac | join(",") }}
{% endif %}

{% if key_exchange -%}
# Specifies the available KEX (Key Exchange) algorithms. Multiple algorithms must
# be comma-separated.
#
# NOTE: As of now, there is no 'multi' node for 'key-exchange', thus we have only one :/
KexAlgorithms {{ key_exchange | join(",") }}
{% endif %}

{% if allow_users -%}
# This keyword can be followed by a list of user name patterns, separated by spaces.
# If specified, login is allowed only for user names that match one of the patterns. 
# Only user names are valid, a numerical user ID is not recognized.
AllowUsers {{ allow_users | join(" ") }}
{% endif %}

{% if allow_groups -%}
# This keyword can be followed by a list of group name patterns, separated by spaces.
# If specified, login is allowed only for users whose primary group or supplementary
# group list matches one of the patterns. Only group names are valid, a numerical group
# ID is not recognized.
AllowGroups {{ allow_groups | join(" ") }}
{% endif %}

{% if deny_users -%}
# This keyword can be followed by a list of user name patterns, separated by spaces.
# Login is disallowed for user names that match one of the patterns. Only user names
# are valid, a numerical user ID is not	recognized.
DenyUsers {{ deny_users | join(" ") }}
{% endif %}

{% if deny_groups -%}
# This keyword can be followed by a list of group name patterns, separated by spaces.
# Login is disallowed for users whose primary group or supplementary group list matches
# one of the patterns. Only group names are valid, a numerical group ID is not recognized.
DenyGroups {{ deny_groups | join(" ") }}
{% endif %}
"""

default_config_data = {
    'port' : '22',
    'log_level': 'INFO',
    'allow_root': 'no',
    'password_authentication': 'yes',
    'host_validation': 'yes'
}

def get_config():
    ssh = default_config_data
    conf = Config()
    if not conf.exists('service ssh'):
        return None
    else:
        conf.set_level('service ssh')

    if conf.exists('access-control allow user'):
        allow_users = conf.return_values('access-control allow user')
        ssh.setdefault('allow_users', allow_users)

    if conf.exists('access-control allow group'):
        allow_groups = conf.return_values('access-control allow group')
        ssh.setdefault('allow_groups', allow_groups)

    if conf.exists('access-control deny user'):
        deny_users = conf.return_values('access-control deny user')
        ssh.setdefault('deny_users', deny_users)

    if conf.exists('access-control deny group'):
        deny_groups = conf.return_values('access-control deny group')
        ssh.setdefault('deny_groups', deny_groups)

    if conf.exists('allow-root'):
        ssh['allow-root'] = 'yes'

    if conf.exists('ciphers'):
        ciphers = conf.return_values('ciphers')
        ssh.setdefault('ciphers', ciphers)

    if conf.exists('disable-host-validation'):
        ssh['host_validation'] = 'no'

    if conf.exists('disable-password-authentication'):
        ssh['password_authentication'] = 'no'

    if conf.exists('key-exchange'):
        kex = conf.return_values('key-exchange')
        ssh.setdefault('key_exchange', kex)

    if conf.exists('listen-address'):
        # We can listen on both IPv4 and IPv6 addresses
        # Maybe there could be a check in the future if the configured IP address
        # is configured on this system at all?
        addresses = conf.return_values('listen-address')
        listen = []

        for addr in addresses:
            listen.append(addr)

        ssh.setdefault('listen_on', listen)

    if conf.exists('loglevel'):
        ssh['log_level'] = conf.return_value('loglevel')

    if conf.exists('mac'):
        mac = conf.return_values('mac')
        ssh.setdefault('mac', mac)

    if conf.exists('port'):
        port = conf.return_value('port')
        ssh.setdefault('port', port)

    return ssh

def verify(ssh):
    if ssh is None:
        return None

    if 'loglevel' in ssh.keys():
        allowed_loglevel = 'QUIET, FATAL, ERROR, INFO, VERBOSE'
        if not ssh['loglevel'] in allowed_loglevel:
            raise ConfigError('loglevel must be one of "{0}"\n'.format(allowed_loglevel))

    return None

def generate(ssh):
    if ssh is None:
        return None

    tmpl = jinja2.Template(config_tmpl)
    config_text = tmpl.render(ssh)
    with open(config_file, 'w') as f:
        f.write(config_text)
    return None

def apply(ssh):
    if ssh is not None and 'port' in ssh.keys():
        os.system("sudo systemctl restart ssh")
    else:
        # SSH access is removed in the commit
        os.system("sudo systemctl stop ssh")
        os.unlink(config_file)

    return None

if __name__ == '__main__':
    try:
        c = get_config()
        verify(c)
        generate(c)
        apply(c)
    except ConfigError as e:
        print(e)
        sys.exit(1)
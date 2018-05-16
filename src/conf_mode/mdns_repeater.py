#!/usr/bin/env python3
#
# Copyright (C) 2017 VyOS maintainers and contributors
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
import netifaces
import time

from vyos.config import Config
from vyos import ConfigError

config_file = r'/etc/default/mdns-repeater'

def get_config():
    interface_list = []

    conf = Config()
    conf.set_level('service mdns repeater')
    if not conf.exists(''):
        return interface_list

    if conf.exists('interface'):
        intfs_names = []
        intfs_names = conf.return_values('interface')

        for name in intfs_names:
            interface_list.append(name)

    return interface_list

def verify(mdns):
    # '0' interfaces are possible, think of service deletion. Only '1' is not supported!
    if len(mdns) == 1:
        raise ConfigError('At least 2 interfaces must be specified but %d given!' % len(mdns))

    # For mdns-repeater to work it is essential that the interfaces
    # have an IP address assigned
    for intf in mdns:
        try:
            netifaces.ifaddresses(intf)[netifaces.AF_INET]
        except KeyError as e:
            raise ConfigError('No IP address configured for interface "%s"!' % intf)

    return None

def generate(mdns):
    config_header = '### Autogenerated by vyos-update-mdns-repeater.py on {tm} ###\n'.format(tm=time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime()))
    if len(mdns) > 0:
        config_args = 'DAEMON_ARGS="' + ' '.join(str(e) for e in mdns) + '"\n'
    else:
        config_args = 'DAEMON_ARGS=""\n'

    # write new configuration file
    f = open(config_file, 'w')
    f.write(config_header)
    f.write(config_args)
    f.close()

    return None

def apply(mdns):
    if len(mdns) == 0:
        cmd = "sudo systemctl stop mdns-repeater"
    else:
        cmd = "sudo systemctl restart mdns-repeater"

    os.system(cmd)
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
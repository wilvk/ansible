# (c) 2016 Red Hat Inc.
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os

from ansible.compat.tests.mock import patch
from ansible.modules.network.nxos import nxos_vrf
from .nxos_module import TestNxosModule, load_fixture, set_module_args


class TestNxosVrfModule(TestNxosModule):

    module = nxos_vrf

    def setUp(self):
        self.mock_load_config = patch('ansible.modules.network.nxos.nxos_vrf.load_config')
        self.load_config = self.mock_load_config.start()

        self.mock_run_commands = patch('ansible.modules.network.nxos.nxos_vrf.run_commands')
        self.run_commands = self.mock_run_commands.start()

    def tearDown(self):
        self.mock_load_config.stop()
        self.mock_run_commands.stop()

    def load_fixtures(self, commands=None):
        def load_from_file(*args, **kwargs):
            module, commands = args
            output = list()

            for command in commands:
                filename = str(command).split(' | ')[0].replace(' ', '_')
                filename = os.path.join('nxos_vrf', filename)
                output.append(load_fixture(filename))
            return output

        self.load_config.return_value = None
        self.run_commands.side_effect = load_from_file

    def test_nxos_vrf_present(self):
        set_module_args(dict(vrf='ntc', state='present', admin_state='up'))
        self.execute_module(changed=True, commands=['vrf context ntc', 'no shutdown'])

    def test_nxos_vrf_present_no_change(self):
        set_module_args(dict(vrf='management', state='present', admin_state='up'))
        self.execute_module(changed=False, commands=[])

    def test_nxos_vrf_absent(self):
        set_module_args(dict(vrf='management', state='absent'))
        self.execute_module(changed=True, commands=['no vrf context management'])

    def test_nxos_vrf_absent_no_change(self):
        set_module_args(dict(vrf='ntc', state='absent'))
        self.execute_module(changed=False, commands=[])

    def test_nxos_vrf_default(self):
        set_module_args(dict(vrf='default'))
        result = self.execute_module(failed=True)
        self.assertEqual(result['msg'], 'cannot use default as name of a VRF')

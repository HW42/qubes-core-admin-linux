#!/usr/bin/python2
#
# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2010  Joanna Rutkowska <joanna@invisiblethingslab.com>
# Copyright (C) 2013  Marek Marczykowski <marmarek@invisiblethingslab.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#

import subprocess
import sys
import os.path
import shutil

from qubes.qubes import QubesVm,QubesHVm
from qubes.qubes import QubesException,QubesHost,QubesVmLabels
from qubes.qubes import vm_files,system_path,dry_run

vm_files['appmenus_templates_subdir'] = 'apps.templates'
vm_files['appmenus_template_templates_subdir'] = 'apps-template.templates'
vm_files['appmenus_whitelist'] = 'whitelisted-appmenus.list'

system_path['appmenu_start_hvm_template'] = '/usr/share/qubes-appmenus/qubes-start.desktop'
system_path['appmenu_create_cmd'] = '/usr/libexec/qubes-appmenus/create-apps-for-appvm.sh'
system_path['appmenu_remove_cmd'] = '/usr/libexec/qubes-appmenus/remove-appvm-appmenus.sh'


def QubesVm_get_attrs_config(self, attrs):
    attrs["appmenus_templates_dir"] = { "eval": \
        'os.path.join(self.dir_path, vm_files["appmenus_templates_subdir"]) if self.updateable else ' + \
            'self.template.appmenus_templates_dir if self.template is not None else None' }
    return attrs

def QubesVm_appmenus_create(self, verbose=False, source_template = None):
    if source_template is None:
        source_template = self.template

    if self.internal:
        return

    vmtype = None
    if self.is_netvm():
        vmtype = 'servicevms'
    elif self.is_template():
        vmtype = 'vm-templates'
    else:
        vmtype = 'appvms'

    try:
        if source_template is not None:
            subprocess.check_call ([system_path["appmenu_create_cmd"], source_template.appmenus_templates_dir, self.name, vmtype])
        elif self.appmenus_templates_dir is not None:
            subprocess.check_call ([system_path["appmenu_create_cmd"], self.appmenus_templates_dir, self.name, vmtype])
        else:
            # Only add apps to menu
            subprocess.check_call ([system_path["appmenu_create_cmd"], "none", self.name, vmtype])
    except subprocess.CalledProcessError:
        print >> sys.stderr, "Ooops, there was a problem creating appmenus for {0} VM!".format (self.name)

def QubesVm_appmenus_remove(self):
    vmtype = None
    if self.is_netvm():
        vmtype = 'servicevms'
    elif self.is_template():
        vmtype = 'vm-templates'
    else:
        vmtype = 'appvms'
    subprocess.check_call ([system_path["appmenu_remove_cmd"], self.name, vmtype])

def QubesVm_pre_rename(self, new_name):
    self.appmenus_remove()

def QubesVm_post_rename(self, old_name):
    old_dirpath = os.path.join(os.path.dirname(self.dir_path), old_name)
    if self.appmenus_templates_dir is not None:
        self.appmenus_templates_dir = self.appmenus_templates_dir.replace(old_dirpath, self.dir_path)

    self.appmenus_create()

def QubesVm_create_on_disk(self, verbose, source_template):

    if isinstance(self, QubesHVm) and source_template is None:
        if verbose:
            print >> sys.stderr, "--> Creating appmenus directory: {0}".format(self.appmenus_templates_dir)
        os.mkdir (self.appmenus_templates_dir)
        shutil.copy (system_path["appmenu_start_hvm_template"], self.appmenus_templates_dir)

    source_whitelist_filename = 'vm-' + vm_files["appmenus_whitelist"]
    if self.is_netvm():
        source_whitelist_filename = 'netvm-' + vm_files["appmenus_whitelist"]
    if source_template and os.path.exists(os.path.join(source_template.dir_path, source_whitelist_filename)):
        if verbose:
            print >> sys.stderr, "--> Creating default whitelisted apps list: {0}".\
                format(self.dir_path + '/' + vm_files["whitelisted_appmenus"])
        shutil.copy(os.path.join(source_template.dir_path, source_whitelist_filename),
                os.path.join(self.dir_path, vm_files["whitelisted_appmenus"]))

    if source_template and self.updateable:
        if verbose:
            print >> sys.stderr, "--> Copying the template's appmenus templates dir:\n{0} ==>\n{1}".\
                    format(source_template.appmenus_templates_dir, self.appmenus_templates_dir)
        shutil.copytree (source_template.appmenus_templates_dir, self.appmenus_templates_dir)

    # Create appmenus
    self.appmenus_create(verbose=verbose)

def QubesVm_clone_disk_files(self, src_vm, verbose):
    if src_vm.updateable and src_vm.appmenus_templates_dir is not None and self.appmenus_templates_dir is not None:
        if verbose:
            print >> sys.stderr, "--> Copying the template's appmenus templates dir:\n{0} ==>\n{1}".\
                    format(src_vm.appmenus_templates_dir, self.appmenus_templates_dir)
        shutil.copytree (src_vm.appmenus_templates_dir, self.appmenus_templates_dir)

    for whitelist in (
            vm_files["appmenus_whitelist"],
            'vm-' + vm_files["appmenus_whitelist"],
            'netvm-' + vm_files["appmenus_whitelist"]):
        if os.path.exists(os.path.join(src_vm.dir_path, whitelist)):
            if verbose:
                print >> sys.stderr, "--> Copying whitelisted apps list: {0}".\
                    format(whitelist)
            shutil.copy(os.path.join(src_vm.dir_path, whitelist),
                    os.path.join(self.dir_path, whitelist))

    # Create appmenus
    self.appmenus_create(verbose=verbose)

def QubesVm_remove_from_disk(self):
    self.appmenus_remove()

def QubesVm_appmenus_recreate(self):
    self.appmenus_remove()
    self.appmenus_create()

# new methods
QubesVm.appmenus_create = QubesVm_appmenus_create
QubesVm.appmenus_remove = QubesVm_appmenus_remove
QubesVm.appmenus_recreate = QubesVm_appmenus_recreate

# hooks for existing methods
QubesVm.hooks_get_attrs_config.append(QubesVm_get_attrs_config)
QubesVm.hooks_pre_rename.append(QubesVm_pre_rename)
QubesVm.hooks_post_rename.append(QubesVm_post_rename)
QubesVm.hooks_create_on_disk.append(QubesVm_create_on_disk)
QubesVm.hooks_clone_disk_files.append(QubesVm_clone_disk_files)
QubesVm.hooks_remove_from_disk.append(QubesVm_remove_from_disk)

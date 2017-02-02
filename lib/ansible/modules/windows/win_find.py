#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2016, Ansible, inc
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
#

ANSIBLE_METADATA = {'metadata_version': '1.0',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = r'''
---
module: win_find
version_added: "2.3"
short_description: return a list of files based on specific criteria
description:
    - Return a list of files based on specified criteria.
    - Multiple criteria are AND'd together.
    - For non-Windows targets, use the M(find) module instead.
options:
    age:
        description:
            - Select files or folders whose age is equal to or greater than
              the specified time. Use a negative age to find files equal to or
              less than the specified time. You can choose seconds, minutes,
              hours, days or weeks by specifying the first letter of an of
              those words (e.g., "2s", "10d", 1w").
        required: false
    age_stamp:
        description:
            - Choose the file property against which we compare C(age). The
              default attribute we compare with is the last modification time.
        required: false
        default: mtime
        choices: ['atime', 'mtime', 'ctime']
    checksum_algorithm:
        description:
            - Algorithm to determine the checksum of a file. Will throw an error
              if the host is unable to use specified algorithm.
        required: false
        default: sha1
        choices: ['md5', 'sha1', 'sha256', 'sha384', 'sha512']
    file_type:
        description: Type of file to search for
        required: false
        default: file
        choices: ['file', 'directory']
    follow:
        description:
            - Set this to true to follow symlinks in the path. This needs to
              be used in conjunction with C(recurse).
        required: false
        default: false
        choices: ['true', 'false']
    get_checksum:
        description:
            - Whether to return a checksum of the file in the return info (default sha1),
              use C(checksum_algorithm) to change from the default.
        required: false
        default: true
        choices: ['true', 'false']
    hidden:
        description: Set this to include hidden files or folders
        required: false
        default: false
        choices: ['true', 'false']
    paths:
        description:
            - List of paths of directories to search for files or folders in.
              This can be supplied as a single path or a list of paths.
        required: true
    patterns:
        description:
            - One or more (powershell or regex) patterns to compare filenames
              with. The type of pattern matching is controlled by C(use_regex)
              option. The patterns retrict the list of files or folders to be
              returned based on the filenames. For a file to be matched it
              only has to match with one pattern in a list provided.
        required: false
    recurse:
        description:
            - Will recursively descend into the directory looking for files
              or folders
        required: false
        default: false
        choices: ['true', 'false']
    size:
        description:
            - Select files or folders whose size is equal to or greater than
              the specified size. Use a negative value to find files equal to
              or less than the specified size. You can specify the size with
              a suffix of the byte type i.e. kilo = k, mega = m... Size is not
              evaluated for symbolic links.
        required: false
        default: false
    use_regex:
        description:
            - Will set patterns to run as a regex check if true
        required: false
        default: false
        choices: ['true', 'false']
notes:
    - For non-Windows targets, use the M(find) module instead.
author: "Jordan Borean (@jborean93)"
'''

EXAMPLES = r'''
# Find files in path
- win_find:
    paths: D:\temp

# Find hidden files in path
- win_find:
    paths: D:\temp
    hidden: True

# Find files in multiple paths
- win_find:
    paths: ['C:\temp', 'D:\temp']

# Find files in directory while searching recursively
- win_find:
    paths: D:\temp
    recurse: True

# Find files in directory while following symlinks
- win_find:
    paths: D:\temp
    recurse: True
    follow: True

# Find files with .log and .out extension using powershell wildcards
- win_find:
    paths: D:\temp
    patterns: ['*.log', '*.out']

# Find files in path based on regex pattern
- win_find:
    paths: D:\temp
    patterns: 'out_\d{8}-\d{6}.log'

# Find files older than 1 day
- win_find:
    paths: D:\temp
    age: 86400

# Find files older than 1 day based on create time
- win_find:
    paths: D:\temp
    age: 86400
    age_stamp: ctime

# Find files older than 1 day with unit syntax
- win_find:
    paths: D:\temp
    age: 1d

# Find files newer than 1 hour
- win_find:
    paths: D:\temp
    age: -3600

# Find files newer than 1 hour with unit syntax
- win_find:
    paths: D:\temp
    age: -1h

# Find files larger than 1MB
- win_find:
    paths: D:\temp
    size: 1048576

# Find files larger than 1GB with unit syntax
- win_find:
    paths: D:\temp
    size: 1g

# Find files smaller than 1MB
- win_find:
    paths: D:\temp
    size: -1048576

# Find files smaller than 1GB with unit syntax
- win_find:
    paths: D:\temp
    size: -1g

# Find folders/symlinks in multiple paths
- win_find:
    paths: ['C:\temp', 'D:\temp']
    file_type: directory

# Find files and return SHA256 checksum of files found
- win_find:
    paths: C:\temp
    get_checksum: True
    checksum_algorithm: sha256

# Find files and do not return the checksum
- win_find:
    path: C:\temp
    get_checksum: False
'''

RETURN = r'''
changed:
    description: Whether anything was chagned
    returned: always
    type: boolean
    sample: True
examined:
    description: The number of files/folders that was checked
    returned: always
    type: int
    sample: 10
matched:
    description: The number of files/folders that match the criteria
    returned: always
    type: int
    sample: 2
files:
    description: Information on the files/folders that match the criteria returned as a list of dictionary elements for each file matched
    returned: success
    type: complex
    contains:
        attributes:
            description: attributes of the file at path in raw form
            returned: success, path exists
            type: string
            sample: "Archive, Hidden"
        checksum:
            description: The checksum of a file based on checksum_algorithm specified
            returned: success, path exists, path is a file, get_checksum == True
            type: string
            sample: 09cb79e8fc7453c84a07f644e441fd81623b7f98
        creationtime:
            description: the create time of the file represented in seconds since epoch
            returned: success, path exists
            type: float
            sample: 1477984205.15
        extension:
            description: the extension of the file at path
            returned: success, path exists, path is a file
            type: string
            sample: ".ps1"
        isarchive:
            description: if the path is ready for archiving or not
            returned: success, path exists
            type: boolean
            sample: True
        isdir:
            description: if the path is a directory or not
            returned: success, path exists
            type: boolean
            sample: True
        ishidden:
            description: if the path is hidden or not
            returned: success, path exists
            type: boolean
            sample: True
        islnk:
            description: if the path is a symbolic link or junction or not
            returned: success, path exists
            type: boolean
            sample: True
        isreadonly:
            description: if the path is read only or not
            returned: success, path exists
            type: boolean
            sample: True
        isshared:
            description: if the path is shared or not
            returned: success, path exists
            type: boolean
            sample: True
        lastaccesstime:
            description: the last access time of the file represented in seconds since epoch
            returned: success, path exists
            type: float
            sample: 1477984205.15
        lastwritetime:
            description: the last modification time of the file represented in seconds since epoch
            returned: success, path exists
            type: float
            sample: 1477984205.15
        lnk_source:
            description: the target of the symbolic link, will return null if not a link or the link is broken
            return: success, path exists, path is a symbolic link
            type: string
            sample: C:\temp
        owner:
            description: the owner of the file
            returned: success, path exists
            type: string
            sample: BUILTIN\Administrators
        path:
            description: the full absolute path to the file
            returned: success, path exists
            type: string
            sample: BUILTIN\Administrators
        sharename:
            description: the name of share if folder is shared
            returned: success, path exists, path is a directory and isshared == True
            type: string
            sample: file-share
        size:
            description: the size in bytes of a file or folder
            returned: success, path exists, path is not a link
            type: int
            sample: 1024
'''

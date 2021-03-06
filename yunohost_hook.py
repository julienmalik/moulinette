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

""" yunohost_hook.py

    Manage hooks
"""
import os
import sys
import re
import json
from yunohost import YunoHostError, YunoHostLDAP, win_msg, colorize

hook_folder = '/user/share/yunohost/hooks/'

def hook_add(action, file):
    """
    Store hook script to filsystem

    Keyword argument:
        file -- Script to check
        action -- Action folder to store into

    """
    try: os.listdir(hook_folder + action)
    except OSError: os.makedirs(hook_folder + action)

    os.system('cp '+ file +' '+ hook_folder + action)


def hook_callback(action):
    """
    Execute all scripts binded to an action

    Keyword argument:
        action -- Action name

    """
    with YunoHostLDAP() as yldap:
        try: os.listdir(hook_folder + action)
        except OSError: os.makedirs(hook_folder + action)

        for hook in os.listdir(hook_folder + action):
            hook_exec(file=hook_folder + action +'/'+ hook)


def hook_check(file):
    """
    Parse the script file and get arguments

    Keyword argument:
        file -- File to check

    """
    try:
        with open(file[:file.index('scripts/')] + 'manifest.json') as f:
            manifest = json.loads(str(f.read()))
    except:
        raise YunoHostError(22, _("Invalid app package"))

    action = file[file.index('scripts/') + 8:]
    if action in manifest["arguments"]:
        return manifest["arguments"][action]
    else:
        return {}


def hook_exec(file, args=None):
    """
    Execute hook from a file with arguments

    Keyword argument:
        file -- Script to execute
        args -- Arguments to pass to the script

    """
    with YunoHostLDAP() as yldap:
        required_args = hook_check(file)
        if args is None:
            args = {}

        arg_list = []
        for arg in required_args:
            if arg['name'] in args:
                if 'choices' in arg and args[arg['name']] not in arg['choices']:
                    raise YunoHostError(22, _("Invalid choice") + ': ' + args[arg['name']])
                arg_list.append(args[arg['name']])
            else:
                if os.isatty(1) and 'ask' in arg:
                    ask_string = arg['ask']['en'] #TODO: I18n
                    if 'choices' in arg:
                        ask_string = ask_string +' ('+ '|'.join(arg['choices']) +')'
                    if 'default' in arg:
                        ask_string = ask_string +' (default: '+ arg['default'] +')'

                    input_string = raw_input(colorize(ask_string + ': ', 'cyan'))

                    if input_string == '' and 'default' in arg:
                        input_string = arg['default']

                    arg_list.append(input_string)
                elif 'default' in arg:
                    arg_list.append(arg['default'])
                else:
                    raise YunoHostError(22, _("Missing arguments") + ': ' + arg['name'])

        file_path = "./"
        if "/" in file and file[0:2] != file_path:
            file_path = os.path.dirname(file)
            file = file.replace(file_path +"/", "")
        return os.system('su - admin -c "cd \\"'+ file_path +'\\" && bash \\"'+ file +'\\" '+ ' '.join(arg_list) +'"') #TODO: Allow python script

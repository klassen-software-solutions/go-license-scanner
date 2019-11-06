
"""Scan a GO project for third-party dependancies.

This module will examine a given directory containing a GO project to determine all
the modules or packages that it relies upon.
"""

import logging
import os
import pathlib
import re
import subprocess

from typing import List


_MODULE_LIST_FILENAME = "go.mod"
_DEPENDANCY_COLUMN = 0
_IS_MAIN_PACKAGE_COLUMN = 1
_IS_INDIRECT_COLUMN = 2
_NUMBER_OF_COLUMNS_IN_DEPENDANCY_LIST_REPORT = 3
_HIDDEN_FILE_REGEX = r'\..+\/.+'

_SYSTEM_MODULES = {'path', 'mime', 'internal', 'os', 'encoding', 'crypto', 'runtime',
                   'compress', 'net', 'io', 'unicode', 'container', 'hash', 'math',
                   'sync', 'regexp'
                  }

_IGNORED_DEPENDANCIES = {'vendor/golang_org', 'golang_org',
                         'scm01.frauscher.intern',
                         'sintela', 'sensonic'
                        }


def scan(directory: str) -> List[str]:
    """List the dependances required by the GO project found in directory."""

    ret = []
    cwd = os.getcwd()
    os.chdir(directory)
    logging.info("scanning for dependancies in %s", directory)

    if pathlib.Path(_MODULE_LIST_FILENAME).exists():
        ret = _dependancy_list_from_modules()
    else:
        ret = _dependancy_list_from_packages()

    os.chdir(cwd)
    return ret


def _dependancy_list_from_modules() -> List[str]:
    logging.debug("  using GO modules to determine dependancies")
    ret = []
    cmd = subprocess.Popen('go list -m -f "{{.Path}} {{.Main}} {{.Indirect}}" all',
                           shell=True, stdout=subprocess.PIPE)
    for line in cmd.stdout:
        entry = _line_as_tuple(line)
        if entry is None:
            logging.warning("    ignoring line %s", (line.strip()))
            continue

        if entry[_IS_MAIN_PACKAGE_COLUMN]:
            continue

        dep = entry[_DEPENDANCY_COLUMN]
        if dep.startswith("golang.org/"):
            continue

        logging.debug("    found dependancy %s", dep)
        ret.append(dep)
    return ret


def _dependancy_list_from_packages() -> List[str]:
    logging.debug("  searching packages to determine dependancies")
    deps = set()
    ret = []
    dirs = _directories_containing_go_code()
    for directory in dirs:
        deps.update(_dependancies_in_directory(directory))
    logging.debug("    removing local and standard library dependancies. Leaves...")
    for dep in deps:
        if _should_be_ignored(dep):
            continue
        path = dep.split("/")
        if len(path) == 1:
            continue
        if path[0] in _SYSTEM_MODULES:
            continue
        logging.debug("      %s", dep)
        ret.append(dep)
    return ret

def _should_be_ignored(dep: str) -> bool:
    for igdep in _IGNORED_DEPENDANCIES:
        if dep.startswith(igdep + "/"):
            return True
    return False

def _directories_containing_go_code() -> List[str]:
    dirs = set()
    logging.debug("    finding the go code...")
    cmd = subprocess.Popen('find . -name "*.go" | grep -v ".*_test.go"',
                           shell=True, stdout=subprocess.PIPE)
    for line in cmd.stdout:
        directory = _remove_prefix(os.path.dirname(line.decode("utf-8").strip()), "./")
        if re.match(_HIDDEN_FILE_REGEX, directory):
            logging.debug("      ignoring %s", directory)
            continue
        dirs.add(directory)

    for directory in dirs:
        logging.debug("      found %s", directory)
    return dirs

def _dependancies_in_directory(directory) -> List[str]:
    logging.debug("    searching for dependancies in %s", directory)
    deps = set()
    cwd = os.getcwd()
    os.chdir(directory)
    cmd = subprocess.Popen('go list -f "{{.Deps}}"', shell=True, stdout=subprocess.PIPE)
    for line in cmd.stdout:
        newdeps = line.decode("utf-8").strip().strip("[]").split()
        if len(newdeps) > 0:
            logging.debug("      found %s", newdeps)
            deps.update(newdeps)
    os.chdir(cwd)
    return deps


def _remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def _line_as_tuple(line: str) -> (str, bool, bool):
    entry = line.split()
    if len(entry) != _NUMBER_OF_COLUMNS_IN_DEPENDANCY_LIST_REPORT:
        return None

    return (entry[_DEPENDANCY_COLUMN].decode("utf-8"),
            entry[_IS_MAIN_PACKAGE_COLUMN].decode("utf-8") == "true",
            entry[_IS_INDIRECT_COLUMN].decode("utf-8") == "true")

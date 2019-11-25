
"""Dependancy scanning

This module defines the API required for dependancy scanning and provides two scanners,
one for scanning using GO modules and one for scanning GO packages.
"""

import abc
import logging
import os
import pathlib
import subprocess

from operator import attrgetter
from typing import Dict, List

from .cache import LicenseReportEntry


class DependancyScanner(abc.ABC):
    """API for implementing a scan for dependancies."""

    @abc.abstractmethod
    def can_handle(self, directory: str) -> bool:
        """Subclasses must override this to return True if this scanner
           can handle the code in the given directory.
        """

    @abc.abstractmethod
    def scan(self, directory: str) -> List[LicenseReportEntry]:
        """Subclasses must override this to scan the given directory and
           return a list of the dependancies. For each entry added, the
           'package' and 'dependancy_scanner_name' should be filled.
        """


class GoModuleDependancyScanner(DependancyScanner):
    """Scanner implementation that will handle GO module based projects.
    """

    _MODULE_LIST_FILENAME = "go.mod"
    _DEPENDANCY_COLUMN = 0
    _IS_MAIN_PACKAGE_COLUMN = 1
    _IS_INDIRECT_COLUMN = 2
    _NUMBER_OF_COLUMNS_IN_DEPENDANCY_LIST_REPORT = 3

    def can_handle(self, directory: str) -> bool:
        filename = directory + "/" + self._MODULE_LIST_FILENAME
        return pathlib.Path(filename).exists()

    def scan(self, directory: str) -> List[LicenseReportEntry]:
        ret = []
        cwd = os.getcwd()
        os.chdir(directory)
        cmd = subprocess.Popen('go list -m -f "{{.Path}} {{.Main}} {{.Indirect}}" all',
                               shell=True, stdout=subprocess.PIPE)
        for line in cmd.stdout:
            line = line.decode('utf-8')
            entry = self._line_as_tuple(line)
            if entry is None:
                logging.warning("  ignoring unrecognized line %s", line.strip())
                continue

            if entry[self._IS_MAIN_PACKAGE_COLUMN]:
                logging.debug("  ignoring main package entry %s", line.strip())
                continue

            dep = entry[self._DEPENDANCY_COLUMN]
            logging.debug("  found dependancy %s", dep)
            ret.append(LicenseReportEntry(package=dep, dependancy_scanner_name=type(self).__name__))
        os.chdir(cwd)
        return ret

    @classmethod
    def _line_as_tuple(cls, line: str) -> (str, bool, bool):
        entry = line.split()
        if len(entry) != cls._NUMBER_OF_COLUMNS_IN_DEPENDANCY_LIST_REPORT:
            return None
        return (entry[cls._DEPENDANCY_COLUMN],
                entry[cls._IS_MAIN_PACKAGE_COLUMN] == "true",
                entry[cls._IS_INDIRECT_COLUMN] == "true")


def scan_all(directory: str, scanners: List[DependancyScanner]) -> List[LicenseReportEntry]:
    """Scan a directory using all applicable scanners in the list and return a list
       of the merged results.
    """
    found_a_scanner = False
    combined_entries = {}
    logging.info("Scanning for dependancies in %s", directory)
    for scanner in scanners:
        logging.debug("Trying scanner: %s", type(scanner).__name__)
        if scanner.can_handle(directory):
            logging.info("Using scanner: %s", type(scanner).__name__)
            found_a_scanner = True
            _add_new_entries(combined_entries, scanner.scan(directory))
    if not found_a_scanner:
        raise RuntimeError("Could not find a scanner that will handle this directory")
    return sorted(combined_entries.values(), key=attrgetter('package'))


def _add_new_entries(entries: Dict, new_entries: List[LicenseReportEntry]):
    for item in new_entries:
        if item.package in entries:
            continue
        entries[item.package] = item

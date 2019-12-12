
"""Results caching

This module defines the API used for caching the license results as well as provides
a simple file based cache implementation.
"""

import abc
import json
import logging
import pathlib

from dataclasses import asdict
from dataclasses import dataclass

@dataclass
class LicenseReportEntry:
    """Encapsulation of the information we need to include in a report.
    """
    package: str = None
    license_name: str = None
    license_url: str = None
    license_encoded: str = None
    license_recognized_at: str = None
    dependancy_scanner_name: str = None
    license_recognizer_name: str = None

    def __eq__(self, other):
        if isinstance(other, LicenseReportEntry):
            return (self.package == other.package and
                    self.license_name == other.license_name and
                    self.license_url == other.license_url and
                    self.license_encoded == other.license_encoded and
                    self.license_recognized_at == other.license_recognized_at and
                    self.dependancy_scanner_name == other.dependancy_scanner_name and
                    self.license_recognizer_name == other.license_recognizer_name)
        return False


class LicenseCache(abc.ABC):
    """API for caching license results."""

    @abc.abstractmethod
    def read(self, package: str) -> LicenseReportEntry:
        """Subclasses must override this to return the current LicenseReportEntry
           for the given package name. They should return None if no entry has yet
           been cached.
        """

    @abc.abstractmethod
    def write(self, entry: LicenseReportEntry):
        """Subclasses must override this to add or update the given entry. Note
           that entry.package must have been set or an exception will be thrown.
        """


class JsonFileLicenseCache(LicenseCache):
    """Cache implementation using a simple JSON file."""

    def __init__(self, filename: str):
        self.filename = filename
        if not pathlib.Path(filename).exists():
            logging.info("Could not read %s, assuming an initially empty cache", filename)
        self._resolved = self._read_cache_from_file()
        self._has_changed = False

    def read(self, package: str) -> LicenseReportEntry:
        jsn = self._resolved.get(package, None)
        return None if jsn is None else LicenseReportEntry(**jsn)

    def write(self, entry: LicenseReportEntry):
        jsn = asdict(entry)
        self._resolved[entry.package] = jsn
        self._has_changed = True

    def update_cache_file(self) -> bool:
        """Creates or updates the cache file if there have been any changes. Returns
           True if a change was made and False otherwise."""
        if self._has_changed:
            resolved = list(self._resolved.values())
            resolved.sort(key=lambda lic: lic['package'])
            jsn = {'resolved-licenses': resolved}
            with open(self.filename, 'w') as json_file:
                json.dump(jsn, json_file, indent=4)
            return True
        return False

    def _read_cache_from_file(self):
        resolved = {}
        if pathlib.Path(self.filename).exists():
            with open(self.filename) as json_file:
                data = json.load(json_file)
                lics = data['resolved-licenses']
                if lics is not None:
                    for lic in data['resolved-licenses']:
                        key = lic['package']
                        resolved[key] = lic
        return resolved

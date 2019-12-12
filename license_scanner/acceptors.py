
"""License acceptance

This module defines the API used to automatically accept or reject a license based
on its name.
"""

import abc
import re

from typing import Dict, List

from .cache import LicenseReportEntry


class LicenseAcceptor(abc.ABC):
    """API for implementing the auto-accept/reject of a license."""

    @abc.abstractmethod
    def accept_or_reject(self, entry: LicenseReportEntry) -> bool:
        """Subclasses must override this to examine the entry and decide if it
           should be automatically accepted or rejected. It should return True
           if the license is accepted, False if it is rejected and None if it
           cannot decide.
        """


class JsonFileLicenseAcceptor(LicenseAcceptor):
    """An acceptor that is initialized with a JSON object that lists the acceptable
       licenses. The file follows the format described in the Gradle-License-Report
       GitHub project for the allowed licenses file, except that this only supports
       the moduleLicense and moduleName items. It does not support moduleVersion
       filtering since at present we are not tracking module versions.

       Note that this acceptor never returns False if the license name has been set.
       Any license that does not pass its acceptance is assumed to be rejected and
       not left as unknown. Hence if you support a series of acceptors, you probably
       need this one to be the last one in the list.
    """

    def __init__(self, json_data):
        self._allowed_licenses = self._get_allowed_licenses_from_json(json_data)

    def accept_or_reject(self, entry: LicenseReportEntry) -> bool:
        if entry.license_name:
            allowed = self._allowed_licenses.get(entry.license_name, None)
            if allowed:
                for lic in allowed:
                    if self._entry_matches(entry, lic):
                        return True
            return False
        return None

    @classmethod
    def _get_allowed_licenses_from_json(cls, json_data) -> Dict:
        allowed = {}
        for lic in json_data['allowedLicenses']:
            cls._get_list_by_license(allowed, lic).append(lic)
        return allowed

    @classmethod
    def _get_list_by_license(cls, allowed: Dict, lic: Dict) -> List:
        lst = allowed.get(lic['moduleLicense'], None)
        if lst is None:
            lst = []
            allowed[lic['moduleLicense']] = lst
        return lst

    @classmethod
    def _entry_matches(cls, entry: LicenseReportEntry, allowed_license: Dict) -> bool:
        if entry.license_name != allowed_license['moduleLicense']:
            return False
        if not cls._pattern_matches(entry.package, allowed_license.get('moduleName', None)):
            return False
        return True

    @classmethod
    def _pattern_matches(cls, package: str, pattern: str) -> bool:
        if not pattern:
            return True
        if package == pattern:
            return True
        regex = pattern.replace('.', '\\.').replace('*', '.*')
        if re.fullmatch(regex, package) is not None:
            return True
        return False


def accept_all(entries: List[LicenseReportEntry],
               acceptors: List[LicenseAcceptor]) -> List[LicenseReportEntry]:
    """Compare any entries against all the the acceptors to auto accept/reject them.
       Returns a list of all entries that do not have acceptable licenses.
    """
    unaccepted = []
    for entry in entries:
        if not _try_all_acceptors(entry, acceptors):
            unaccepted.append(entry)
    return unaccepted


def _try_all_acceptors(entry: LicenseReportEntry, acceptors: List[LicenseAcceptor]):
    if acceptors is not None:
        for acceptor in acceptors:
            result = acceptor.accept_or_reject(entry)
            if result is not None:
                return result
    return False

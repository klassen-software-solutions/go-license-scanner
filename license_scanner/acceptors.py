
"""License acceptance

This module defines the API used to automatically accept or reject a license based
on its name.
"""

import abc

from typing import List

from .cache import LicenseCache, LicenseReportEntry


class LicenseAcceptor(abc.ABC):
    """API for implementing the auto-accept/reject of a license."""

    def __init__(self, cache: LicenseCache):
        self.cache = cache

    @abc.abstractmethod
    def do_accept_or_reject(self, entry: LicenseReportEntry) -> bool:
        """Subclasses must override this to examine the entry and decide if it
           should be automatically accepted or rejected. If so it should set
           the following fields and should return True to indicate there has
           been a change.
            acceptable
            acceptor_name

           You should not call this method manually. Instead it should only be
           called from the public accept_or_reject method.
        """

    def accept_or_reject(self, entry: LicenseReportEntry) -> bool:
        """Accept or reject the entry, then update the cache if necessary."""
        if entry.acceptable is None:
            if self.do_accept_or_reject(entry):
                self._update_cache(entry)

    def _update_cache(self, entry: LicenseReportEntry):
        if self.cache is not None:
            self.cache.write(entry)


class JsonFileLicenseAcceptor(LicenseAcceptor):
    """An acceptor that is initialized with a JSON object that lists the acceptable
       and non-acceptable licenses.
    """

    def __init__(self, json_data, cache: LicenseCache):
        LicenseAcceptor.__init__(self, cache)
        self._acceptable = set(json_data['acceptable-license-types'])
        self._unacceptable = set(json_data['unacceptable-license-types'])

    def do_accept_or_reject(self, entry: LicenseReportEntry) -> bool:
        if entry.license_name is not None:
            if entry.license_name in self._acceptable:
                entry.acceptable = True
                entry.acceptor_name = type(self).__name__
                return True
            if entry.license_name in self._unacceptable:
                entry.acceptable = False
                entry.acceptor_name = type(self).__name__
                return True
        return False


def accept_all(entries: List[LicenseReportEntry], acceptors: List[LicenseAcceptor]):
    """Compare any entries against all the the acceptors to auto accept/reject them.
    """
    for entry in entries:
        _try_all_acceptors(entry, acceptors)


def _try_all_acceptors(entry: LicenseReportEntry, acceptors: List[LicenseAcceptor]):
    for acceptor in acceptors:
        if acceptor.accept_or_reject(entry):
            return


"""License recognition

This module defines the API required for license scanning and provides two license
recognizers, one that will check the predefined list and one that will check GitHub.
"""

import abc
import copy
import json
import logging
import time

from operator import attrgetter
from typing import Dict, List

import requests

from .cache import LicenseCache, LicenseReportEntry


class Recognizer(abc.ABC):
    """API for implementing a license recognizer."""

    def __init__(self, cache: LicenseCache):
        self.cache = cache

    @abc.abstractmethod
    def do_recognize(self, entry: LicenseReportEntry) -> bool:
        """Subclasses must override this to attempt to recognize the license for
           entry.package. On call you can assume that entry will have at least the
           'package' item set. If recognized, this should return True and have set
           the following in entry:
            license_name
            license_recognized_at
            license_recognizer_name
            license_url (optional)
            license_encoded (optional)

           If this recognizer is not capable of recognizing entry.package, then
           it should return False.

           Note that this should not be called manually, it should only be called
           via the recognize method.
        """

    def recognize(self, entry: LicenseReportEntry) -> bool:
        """Recognize an entry by first checking the cache and, if not available,
           by calling the do_recognize method.
        """
        if self._set_from_cache(entry):
            logging.debug("  recognized %s as %s using %s (cached)",
                          entry.package,
                          entry.license_name,
                          entry.license_recognizer_name)
            return True
        if self.do_recognize(entry):
            logging.debug("  recognized %s as %s using %s",
                          entry.package,
                          entry.license_name,
                          entry.license_recognizer_name)
            self._save_to_cache(entry)
            return True
        return False

    def _set_from_cache(self, entry: LicenseReportEntry) -> bool:
        if self.cache is not None:
            cached_entry = self.cache.read(entry.package)
            if cached_entry is not None:
                if cached_entry.license_name is not None:
                    entry.__dict__ = cached_entry.__dict__.copy()
                    return True
        return False

    def _save_to_cache(self, entry: LicenseReportEntry):
        if self.cache is not None:
            self.cache.write(entry)


class CommonPrefixRecognizer(Recognizer):
    """License recognizer that assigns a single license to all dependancies with
       a given prefix. Obviously this is relying on the programmer having researched
       the code at that prefix and determining the license type properly.

       In addition to recognizing them, this will also compress all the matching
       dependancies down to a single one, by renaming them to all be the prefix.
       (This will cause the redundant ones to be removed before the reports are
       generated.)
    """

    def __init__(self, prefix: str, license_name: str, license_url: str, cache: LicenseCache):
        Recognizer.__init__(self, cache)
        self.prefix = prefix
        self.license_name = license_name
        self.license_url = license_url

    def do_recognize(self, entry: LicenseReportEntry) -> bool:
        if entry.package.startswith(self.prefix):
            entry.license_name = self.license_name
            entry.license_url = self.license_url
            entry.license_encoded = None
            entry.license_recognized_at = _secs_to_time_string(time.time())
            entry.license_recognizer_name = "%s(%s)" % (type(self).__name__, self.prefix)
            return True
        return False


class GitHubRecognizer(Recognizer):
    """License recognizer that uses the github api. This recognizer will accept any
       package that has the syntax: github.com/<organization>/<package>
    """

    _NUMBER_OF_URL_PATH_SEGMENTS_FOR_GITHUB_API = 3

    def __init__(self, cache: LicenseCache):
        Recognizer.__init__(self, cache)

    def do_recognize(self, entry: LicenseReportEntry) -> bool:
        path = entry.package.split("/")
        if len(path) != self._NUMBER_OF_URL_PATH_SEGMENTS_FOR_GITHUB_API or path[0] != 'github.com':
            return False
        owner = path[1]
        project = path[2]
        if not self._can_call_github():
            return False
        self._fill_license_for_github(owner, project, entry)
        return True

    @classmethod
    def _fill_license_for_github(cls, owner: str, project: str, entry: LicenseReportEntry):
        cls._init_entry(entry)
        url = "https://api.github.com/repos/%s/%s/license" % (owner, project)
        try:
            resp = requests.get(url)
            if not cls._is_ok_response(resp):
                logging.error("  bad response from %s, response=%d", url, resp.status_code)
                return
            j = json.loads(resp.text)
            entry.license_name = j['license']['name']
            entry.license_url = j['download_url']
            entry.license_encoded = j['content']
        except requests.exceptions.ConnectionError as err:
            logging.error("  could not read from %s, error=%s", url, err)

    @classmethod
    def _can_call_github(cls) -> bool:
        url = "https://api.github.com/rate_limit"
        resp = requests.get(url)
        if cls._is_ok_response(resp):
            j = json.loads(resp.text)
            if j['resources']['core']['remaining'] == 0:
                logging.critical("  Do not have any remaining github API calls, retry after %s",
                                 _secs_to_time_string(j['resources']['core']['reset']))
                return False
        return True

    @classmethod
    def _init_entry(cls, entry: LicenseReportEntry):
        entry.license_name = None
        entry.license_url = None
        entry.license_encoded = None
        entry.license_recognized_at = _secs_to_time_string(time.time())
        entry.license_recognizer_name = cls.__name__

    @classmethod
    def _is_ok_response(cls, resp):
        return resp.status_code >= 200 and resp.status_code < 300


class MappedToGitHubRecognizer(Recognizer):
    """License recognizer that uses the GitHub protocol, but requires that the package
       be mapped to the proper GitHub package. The mapping dictionary will take a set of
       keys which are the original package names, mapped to a github package.
    """

    def __init__(self, mapping: Dict[str, str], cache: LicenseCache):
        Recognizer.__init__(self, cache)
        self.mapping = mapping
        self._github = GitHubRecognizer(cache)

    def do_recognize(self, entry: LicenseReportEntry) -> bool:
        git_package = self.mapping.get(entry.package, None)
        if git_package is not None:
            git_entry = copy.copy(entry)
            git_entry.package = git_package
            result = self._github.do_recognize(git_entry)
            if result:
                entry.license_name = git_entry.license_name
                entry.license_url = git_entry.license_url
                entry.license_encoded = git_entry.license_encoded
                entry.license_recognized_at = git_entry.license_recognized_at
                entry.license_recognizer_name = type(self).__name__
            return result
        return False


def recognize_all(entries: List[LicenseReportEntry], recognizers: List[Recognizer]):
    """Use the list of recognizers to attempt to recognize the license for the
       list of entries.
    """
    logging.info("Attempting to recognize %d entries", len(entries))
    for entry in entries:
        _recognize_entry(entry, recognizers)

def _recognize_entry(entry: LicenseReportEntry, recognizers: List[Recognizer]):
    for recognizer in recognizers:
        if entry.package is not None:
            if recognizer.recognize(entry):
                return
    logging.warning("  could not recognize a license for %s", entry.package)

def _secs_to_time_string(secs):
    local_time = time.localtime(secs)
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", local_time)

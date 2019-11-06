
"""Scan a list of dependancies to determine their license requirements."""

import json
import logging
import pathlib
import sys
import time
from typing import List

import requests


DEPENDANCY_COLUMN = 0
LICENSE_ABBREVIATION_COLUMN = 1
URL_COLUMN = 2
_KNOWN_LICENSES_FILENAME = "/opt/Frauscher/etc/known_licenses.json"
_NUMBER_OF_URL_PATH_SEGMENTS_FOR_GITHUB_API = 3

_GOPKG_LICENSE = ("GoPkg License",
                  "https://github.com/niemeyer/gopkg/blob/master/LICENSE",
                  "found")

class Scanner:
    """Class to scan dependancies in a list to determine their licenses."""

    def __init__(self, dependancies: List[str]):
        self.dependancies = dependancies
        self.licenses = []
        self._load_known_licenses()


    def scan(self):
        """Scan each dependancy in the list to determine its license.

        Fills the licenses member with the license details for each dependancy.
        """
        logging.info("scanning for licenses")
        self.licenses = []
        for dep in self.dependancies:
            lic = self._license_for_dependancy(dep)
            self.licenses.append((dep, lic[0], lic[1]))

            if lic[2] is None:
                entry = {
                    "key": dep,
                    "license-abbreviation": lic[0],
                    "license-url": lic[1],
                    "time": Scanner._secs_to_time_string(time.time())
                }
                print("  New entry:", file=sys.stderr)
                print(json.dumps(entry, indent=4), file=sys.stderr)
            else:
                logging.debug("  (%s) %s: %s", lic[2], dep, lic[0])


    def count_invalid_licenses(self) -> int:
        """Returns a count of the number of licenses in the list which either could not be
           determined, or are not considered acceptable.
        """
        count = 0
        for lic in self.licenses:
            dep = lic[DEPENDANCY_COLUMN]
            abbr = lic[LICENSE_ABBREVIATION_COLUMN]
            if abbr == "<unknown>":
                logging.error("  unknown license for %s", dep)
                count += 1
            elif not abbr in self.acceptable_licenses:
                logging.error("  unacceptable license for %s: %s", dep, abbr)
                count += 1
        return count


    def _load_known_licenses(self):
        self.known_licenses = {}
        self.acceptable_licenses = set()
        if pathlib.Path(_KNOWN_LICENSES_FILENAME).exists():
            with open(_KNOWN_LICENSES_FILENAME) as json_file:
                data = json.load(json_file)
                for lic in data["resolved-licenses"]:
                    key = lic["key"]
                    abbrev = lic["license-abbreviation"]
                    lic_url = lic["license-url"]
                    self.known_licenses[key] = (abbrev, lic_url, "cached")

                for lic in data["acceptable-license-types"]:
                    self.acceptable_licenses.add(lic)

    def _license_for_dependancy(self, dep) -> (str, str, str):
        if dep in self.known_licenses:
            return self.known_licenses[dep]

        host = dep.split("/")[0]
        if host == "github.com":
            return Scanner._license_for_github(dep)
        if host == "gopkg.in":
            return _GOPKG_LICENSE

        return ("<unknown>", "", "invalid")

    @staticmethod
    def _license_for_github(dep):
        path = dep.split("/")
        if len(path) < _NUMBER_OF_URL_PATH_SEGMENTS_FOR_GITHUB_API:
            logging.warning("  cannot extract owner and project from the url %s", dep)
            return ("<unknown>", "", None)

        Scanner._ensure_can_call_github()

        owner = path[1]
        project = path[2]
        url = "https://api.github.com/repos/%s/%s/license" % (owner, project)

        try:
            resp = requests.get(url)
            if not Scanner._is_ok_response(resp):
                logging.error("  bad response from %s, response=%d", url, resp.status_code)
                return ("<unknown>", "", None)
        except requests.exceptions.ConnectionError as err:
            logging.error("  could not read from %s, error=%s", url, err)
            return ("<unknown>", "", None)

        j = json.loads(resp.text)
        return (j['license']['name'], j['license']['url'], None)

    @staticmethod
    def _license_for_gopkg():
        return ("GoPkg License",
                "https://github.com/niemeyer/gopkg/blob/master/LICENSE",
                "found")

    @staticmethod
    def _ensure_can_call_github():
        url = "https://api.github.com/rate_limit"
        resp = requests.get(url)
        if Scanner._is_ok_response(resp):
            j = json.loads(resp.text)
            if j['resources']['core']['remaining'] == 0:
                logging.critical("  Do not have any remaining github API calls, retry after %s",
                                 Scanner._secs_to_time_string(j['resources']['core']['reset']))
                sys.exit(-1)

    @staticmethod
    def _is_ok_response(resp):
        return resp.status_code >= 200 and resp.status_code < 300

    @staticmethod
    def _secs_to_time_string(secs):
        local_time = time.localtime(secs)
        return time.strftime("%Y-%m-%dT%H:%M:%S%z", local_time)

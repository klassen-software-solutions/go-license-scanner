#!/usr/bin/env python3

"""Script to scan Go modules for license requirements."""

import json
import os
import pathlib
import subprocess
import sys
import time
import requests

MODULE_LIST_FILENAME = "go.mod"
KNOWN_LICENSES_FILENAME = "/opt/Frauscher/etc/known_licenses.json"

def _line_as_tuple(line):
    entry = line.split()
    if len(entry) != 3:
        return None

    return (entry[0].decode("utf-8"),
            entry[1].decode("utf-8") == "true",
            entry[2].decode("utf-8") == "true")

def _ensure_can_call_github():
    url = "https://api.github.com/rate_limit"
    resp = requests.get(url)
    if _is_ok_response(resp):
        j = json.loads(resp.text)
        if j['resources']['core']['remaining'] == 0:
            print("  FATAL: Do not have any remaining github API calls, retry after %s"
                  % _secs_to_time_string(j['resources']['core']['reset']))
            sys.exit(-1)

def _is_ok_response(resp):
    return resp.status_code >= 200 and resp.status_code < 300

def _secs_to_time_string(secs):
    local_time = time.localtime(secs)
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", local_time)

def _dependancy_list():
    if not pathlib.Path(MODULE_LIST_FILENAME).exists():
        raise Exception('does not use go modules')

    ret = []
    cmd = subprocess.Popen('go list -m -f "{{.Path}} {{.Main}} {{.Indirect}}" all',
                           shell=True, stdout=subprocess.PIPE)
    for line in cmd.stdout:
        entry = _line_as_tuple(line)
        if entry is None:
            print("  WARN: ignoring line %s" % (line.strip()))
            continue

        if entry[1]:
            continue

        ret.append(entry[0])
    return ret

def _license_for_github(dep):
    path = dep.split("/")
    if len(path) != 3:
        print("  WARN: cannot extract owner and project from the url %s" % dep)
        return ("<unknown>", "", None)

    _ensure_can_call_github()

    owner = path[1]
    project = path[2]
    url = "https://api.github.com/repos/%s/%s/license" % (owner, project)

    try:
        resp = requests.get(url)
        if not _is_ok_response(resp):
            print("  ERROR: bad response from %s, response=%d" % (url, resp.status_code))
            return ("<unknown>", "", None)
    except requests.exceptions.ConnectionError as err:
        print("  ERROR: could not read from %s, error=%s" % (url, err))
        return ("<unknown>", "", None)

    j = json.loads(resp.text)
    return (j['license']['name'], j['license']['url'], None)

def _license_for_golang():
    return ("Go License", "https://golang.org/LICENSE", "found")

def _license_for_gopkg():
    return ("GoPkg License", "https://github.com/niemeyer/gopkg/blob/master/LICENSE", "found")



class _Scanner:
    def __init__(self, directory):
        self.dir = directory
        self._load_known_licenses()

    def scan(self):
        """Perform the scan."""

        print("Scanning {}".format(self.dir))
        dependancies = _dependancy_list()
        bad_count = 0
        for dep in dependancies:
            lic = self._license_for_dependancy(dep)
            if lic[0] == "<unknown>":
                print("  FAIL unknown license for %s" % dep)
                bad_count += 1
            elif not lic[0] in self.acceptable_licenses:
                print("  FAIL unacceptable license for %s: %s" % (dep, lic[0]))
                bad_count += 1
            else:
                if lic[2] is None:
                    entry = {
                        "key": dep,
                        "license-abbreviation": lic[0],
                        "license-url": lic[1],
                        "time": _secs_to_time_string(time.time())
                    }
                    print("  New entry:")
                    print(json.dumps(entry, indent=4))
                else:
                    print("  (%s) %s: %s" % (lic[2], dep, lic[0]))

        return bad_count

    def _load_known_licenses(self):
        self.known_licenses = {}
        self.acceptable_licenses = set()
        if pathlib.Path(KNOWN_LICENSES_FILENAME).exists():
            with open(KNOWN_LICENSES_FILENAME) as json_file:
                data = json.load(json_file)
                for lic in data["resolved-licenses"]:
                    key = lic["key"]
                    abbrev = lic["license-abbreviation"]
                    lic_url = lic["license-url"]
                    self.known_licenses[key] = (abbrev, lic_url, "cached")

                for lic in data["acceptable-license-types"]:
                    self.acceptable_licenses.add(lic)

    def _license_for_dependancy(self, dep):
        if dep in self.known_licenses:
            return self.known_licenses[dep]

        host = dep.split("/")[0]
        if host == "github.com":
            return _license_for_github(dep)
        if host == "golang.org":
            return _license_for_golang()
        if host == "gopkg.in":
            return _license_for_gopkg()

        return ("<unknown>", "", "invalid")


def main():
    """Main entry point."""

    scanner = _Scanner(os.getcwd())
    unknown_count = scanner.scan()
    if unknown_count > 0:
        sys.exit(unknown_count)

if __name__ == '__main__':
    main()

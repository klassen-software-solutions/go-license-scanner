# license-check

## Generating a report on the command line

To generate a JSON report of the licenses you simply run the docker container, mounting the
directory of the project to scan as the `/work` directory. For example:

```
docker run -v`pwd`:/work docker-fts.rep01.frauscher.intern/license-check:999999
```

Or, if you wish to see the debugging information while separating the JSON results, something
like the following will work:

```
docker run -v`pwd`:/work docker-fts.rep01.frauscher.intern/license-check:999999 \
    license_scanner.py --verbose --report \
    > t.json
```

(Of course you need to replace the 999999 with the most recent version of the docker image.)

## Turning on license scanning in a Go project

To turn on the scanning you need to add an appropriate section to your git lab configuration. First,
add an appropriate stage, called "licensecheck" to the stages. Next, add the following to turn it on.
Note that <currentversion> should be replaced with the value of the latest version shown in Nexus.

```
run license check:
stage: licensecheck
image: docker-fts-snapshots.rep01.frauscher.intern/license-check:<currentversion>
tags:
  - linux
  - docker
except:
  - master
script:
  - license_scanner.py --verbose
```

## Understanding the license scanner results

The license scanner script will return 0 if there are no problems, -1 (which is reported as 255 in most
Linux systems), or the number of failed licenses.

If the scanning fails, the log file will tell you what licenses have failed. The log file itself will list the
dependancies that it needs to check, the licenses that have been resolved and the licenses that
have not been resolved. You can use this to see what licenses need closer examination.

## The known licenses file

This file is used for the following purposes:

1. To act as a cache so we don't run out of github API calls (we are only allowed 60/hour),
2. To handle the licenses cases that we cannot automatically determine, and
3. To describe which licenses we consider acceptable.

The first and second are dealt with by adding new entries into the "resolved-licenses" section. Each
entry here consists of a key, which is the dependancy being checked, a license abbreviation, which
is used to describe the license for that entry, a license-url which is used to give the full details of that
license, and an optional timestamp which is the time that we established the license information.
The url and the timestamp are not used by the script, but are simply reported. The url is useful if
we need to review licenses in detail or compile a document listing them all. This script will not do
that, but if and when it becomes necessary, the url is a nice way of finding them. The timestamp is 
added in case we want to add a timeout on our license check. For example, perhaps we want to 
recheck all licenses once per year so see if they have changed. If so the scanning script could be
modified to make use of that.

Determining which licenses we consider acceptable is handled by the first section "acceptable-license-types"
of the file. It is simply a list of the "license-abbreviation" values that we consider acceptable. For example,
if we start using a GPL library, the github check will list it as such and report it, but since it is not in
our list of acceptable licenses, our script will report that appropriately. Most of the values here are 
exactly what is returned by the github API calls, but a few (like "GoPkg License" and "Manually Accepted")
are custom values we have created to identify licenses that we have determine as acceptable but are
not automatically handled by the github API.

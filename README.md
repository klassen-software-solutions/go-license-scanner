# license-check

## NOTICE

This project is a fork of a project created by Frauscher Sensonic GmbH. It has been forked and
its license changed to an MIT license with their permission. The intended purpose is to move the
functionality of this project into the more general `LicenseScanner` project and to continue
maintaining it from that point.

## Generating a license report for a Go project

Presently this license checker only handles Go projects that conform to the relatively new 
go module structure. Specifically it is relying on the go module reporting facility in order to
obtain the list of dependancies to examine.

To run the report, all you need is the latest version of the license-check docker image.

```
docker run -v`pwd`:/work docker-fts.rep01.frauscher.intern/license-check:999999
```

This will run the license check using a cache to be found in `resources/license_cache.json` and
writing its output to a file `resources/licenses.json`. The cache file is needed since we use the
GitHub API in order to obtain the license information for any GitHub based dependancies (which is most
of them for Go projects) and we are limited to a maximum of 60 API hits/hour. The cache file will be
automatically created if it does not already exist, but should be checked into git whenever running this
changes it in order to ensure that we do not need to rebuild the cache each time.

## Generating a PDF report

If you wish to obtain a PDF report, the following will write myreport.pdf into the directory mapped
to /work.

```
docker run -v`pwd`:/work docker-fts.rep01.frauscher.intern/license-check:999999 \
    --pdf=myreport.pdf
```

## Turning on license scanning in a Go project

To turn on the scanning you need to add an appropriate section to your git lab configuration. First,
add an appropriate stage, called `licensecheck` to the stages. Next, add the following to turn it on.
Note the use of the `entrypoint` item. This is needed to ensure the CI can run the docker with a
shell rather than running the script automatically. However at present we have removed this from
our current projects as it has been decided not to make the license check a go/no-go decision in
the CI.

```
run license check:
  stage: licensecheck
  image: 
    name: docker-fts-snapshots.rep01.frauscher.intern/license-check:999999
    entrypoint: [""]
  tags:
    - linux
    - docker
  except:
    - master
  script:
    - run_scanner.py
          --verbose 
          --error-on-invalid 
          --cache=resources/license-cache.json 
          --auto-accept=resources/allowed-licenses.json
```

## Understanding the license scanner results

The license scanner script will return 0 if there are no problems, -1 (which is reported as 255 in most
Linux systems) if there is some form of system error. Additionally, if the `--error-on-invalid` command
line option has been given, then the number of unrecognized or unaccepted licenses will be
returned. (This is used by the CI configurations to ensure that invalid licenses cause the CI to
report an error.)

If the scanning fails, the log file will tell you what licenses have failed. If you include the `--verbose`
flag, the logfile will list the dependancies that it needs to check, the licenses that have been resolved 
and the licenses that have not been resolved. You can use this to see what licenses need closer 
examination.

## The known licenses cache file

This file is used as a cache so we don't run out of GitHub API calls (we are only allowed 60/hour).
It can also be used to handle license cases that we cannot automatically determine, by manually
creating/editing an entry in this file, however that is not recommended. For the most part you should
leave this file alone, but checkin any changes that running the license scan makes.

The filename is specified using the `--cache=<filename>` command line option.

We don't describe this file in any more detail as we really don't want it to be manually tweaked. It
should really only be used for caching and perhaps for debugging purposes.

## The acceptable licenses file

Determining which licenses we automatically consider acceptable is handled by the acceptable licenses file.
Any license requests that do not match this file are considered not acceptable. 

The format of the file is described in more detail in https://github.com/jk1/Gradle-License-Report. Note,
however, that we do not support the `moduleVersion` item mentioned in that project since we are
not presently tracking the module versions in our license scanner.

The file itself is specified using the `--auto-accept=<filename>` command line parameter.

Here is a short example. In this example the Apache license would be acceptable by any of our
packages while the MIT license would be acceptable only for projects from `github.com/myorg/` or
from projects `project1` and `project2` of `github.com/anotherorg/`.

```
{
  "allowedLicenses": [
    {
      "moduleLicense": "Apache License 2.0",
    },
    {
      "moduleLicense": "MIT License",
      "moduleName": "github.com/myorg/*",
    },
    {
      "moduleLicense": "MIT License",
      "moduleName": "github.com/anotherorg/project1"
    },
    {
      "moduleLicense": "MIT License",
      "moduleName": "github.com/anotherorg/project2"
    }
  ]
}
```

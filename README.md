# license-check

## Updating the license cache for a project

When the CI fails telling you that there are unknown or unacceptable licenses, you will need to
either change the code to use acceptable license, or assuming that the licenses are acceptable
and just need the correct record kept, you can update the local `license_cache.json` file
for the project.

Assuming the latter, the easiest way is to run the license check locally on your development environment.
This will add any new dependancies to the cache file which you can then checkin and push. (Of course 
you need to replace 999999 with the latest version of the license checker docker.)

```
docker run -v`pwd`:/work docker-fts.rep01.frauscher.intern/license-check:999999
```

### Side note: running the script in the docker

The docker has been created with an `ENTRYPOINT` setting allowing for you to add additional
command line arguments without having to respecify everything. Hence you can, for example,
simply add `--verbose` to the above command without having to specify the entire command.
The docker is configured to run the following command:

```
run_scanner.py \
    --cache=./license_cache.json \
    --auto-accept=/opt/Frauscher/etc/auto_accepted_licenses.json
```

so if you wish to change the cache or auto-accept files you will need to set the entrypoint to be
empty and then run the full command manually. You can obtain the full command line options
by adding the `--help` option.

## Generating a report

The license checker will also allow you to generate a report of all the licenses for your project
either in a JSON or PDF format.

To generate the JSON to a file, the following will write myreport.json into the directory mapped to /work.

```
docker run -v`pwd`:/work docker-fts.rep01.frauscher.intern/license-check:999999 \
    --json=myreport.json
```

Or, if you wish to obtain a PDF report, the following will write myreport.pdf into the directory mapped
to /work.

```
docker run -v`pwd`:/work docker-fts.rep01.frauscher.intern/license-check:999999 \
    --pdf=myreport.pdf
```

## Turning on license scanning in a Go project

To turn on the scanning you need to add an appropriate section to your git lab configuration. First,
add an appropriate stage, called `licensecheck` to the stages. Next, add the following to turn it on.
Note the use of the `entrypoint` item. This is needed to ensure the CI can run the docker with a
shell rather than running the script automatically.

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
          --cache=./license_cache.json 
          --auto-accept=/opt/Frauscher/etc/auto_accepted_licenses.json
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

This file is used for the following purposes:

1. To act as a cache so we don't run out of github API calls (we are only allowed 60/hour), and
2. to handle the licenses cases that we cannot automatically determine.

The filename is specified using the `--cache=<filename>` command line option.

Each entry consists of the following:

* package: This is the dependancy being checked,
* license_name: A short form of the license (e.g. 'MIT License'),
* license_url: The URL describing the full license,
* license_encoded: The full license text, encoded in base64 encoding. Note that you can leave this out and
it will be automatically added, the next time the license_url is read.
* license_recognized_at: The time we last read the license.
* acceptable: If true, the license is accepted, if false the license is rejected, if null then it is not yet
accepted or rejected (i.e. it's state is unknown). For a manually accepted or rejected license you
can set this. If null the script will attempt to set it automatically.
* ..._name: These fields contain the  name of the component that was used when determining
the license details. It is primarily for debugging purposes and is currently never read. For manually
accepting or rejecting a license you may want to set 'acceptor_name' to 'Manual' or perhaps to
the name of the person who accepted/rejected it, just to make it clear.

The timestamp is not currently used by the script, but is added in case we want to add a 
timeout on our license check. For example, perhaps we want to  recheck all licenses once 
per year so see if they have changed. If so the scanning script could be modified to make
use of that information.

Here is a short example:

```
{
    "resolved-licenses": [
        {
            "package": "github.com/Azure/go-ansiterm",
            "license_name": "MIT License",
            "license_url": "https://raw.githubusercontent.com/Azure/go-ansiterm/master/LICENSE",
            "license_encoded": ...,
            "license_recognized_at": "2019-11-29T08:20:36-0700",
            "acceptable": true,
            "dependancy_scanner_name": "GoModuleDependancyScanner",
            "license_recognizer_name": "GitHubRecognizer",
            "acceptor_name": "JsonFileLicenseAcceptor"
        },
        {
            "package": "github.com/Flaque/filet",
            "license_name": "Apache License 2.0",
            "license_url": "https://raw.githubusercontent.com/Flaque/filet/master/LICENSE.txt",
            "license_encoded": ...,
            "license_recognized_at": "2019-11-29T08:20:36-0700",
            "acceptable": true,
            "dependancy_scanner_name": "GoModuleDependancyScanner",
            "license_recognizer_name": "GitHubRecognizer",
            "acceptor_name": "JsonFileLicenseAcceptor"
        }
    ]
}
```


## The acceptable licenses file

Determining which licenses we automatically consider acceptable is handled by the acceptable licenses file.
It is simply a list of the "license_name" values that we consider acceptable or non-acceptable. For example,
if we start using a GPL library, the github check will list it as such and report it, but since it is not in
our list of acceptable licenses, our script will report that appropriately. Most of the values here are 
exactly what is returned by the github API calls, but a few (like "GoPkg License") are custom values we 
have created to identify licenses that are not automatically handled by the github API.

The file itself is specified using the `--auto-accept=<filename>` command line parameter.

Here is a short example showing both acceptable and non-acceptable licenses.

```
{
    "acceptable-license-types": [
        "Apache License 2.0",
        "BSD 2-Clause \"Simplified\" License",
        "BSD 3-Clause \"New\" or \"Revised\" License",
        "Go Standard Library License",
        "ISC License",
        "MIT License",
        "Mozilla Public License 2.0"
    ],
    "unacceptable-license-types": [
        "GNU General Public License family",
        "GNU General Public License v2.0",
        "GNU General Public License v3.0"
    ]
}
```

Note that this only accepts/rejects licenses that have not already been accepted or rejected (i.e.
where "acceptable" is set to null). Once a license has been accepted or rejected, either automatically
or manually, it will not be changed by the auto acceptance code.

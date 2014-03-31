# REST-API-server for statistical data

Statcubeserver serves statistical data over a REST-API. The API
is a fairly thin REST-wrapper for [pydatacube](https://github.com/jampekka/pydatacube/)
functionality.

## Install and startup

Statcubeserver requires [pydatacube](https://github.com/jampekka/pydatacube/)
(usually latest git, developed in sync), CherryPy 3 and Python 2
(most likely 2.7).

There's no separate installer, just run scripts in the project root. Currently
supports loading PC-Axis datasets of the [Helsinki Region Infoshare service](http://www.hri.fi/)
using the [`load_hri.py`](load_hri.py) script, by running eg:

    mkdir hri_data_files
    python2 load_hri.py hri_data_files > hri_data_index.json

which downloads and stores the PC-Axis files to `hri_data_files`-directory and
writes metadata/index of them to `hri_data_index.json`.

The [`px_json_server.py`](px_json_server.py) can be used to serve this data:

    python2 px_json_server.py hri_data_index.json

And if everything goes fine, the API can be accessed (by default) at
http://localhost:8080/resources/ and a (quite spartan) web-UI at
http://localhost:8080/browser/ .

## API Usage

**WARNING!** The API is still subject to change. Please inform the developers
if you are using the server, so we can ensure backwards compatibility.

**NOTE!** The links here point to a server instance serving Helsinki Region's
statistics.  To work with a local version, change the host, port and path
accordingly (eg. http://dev.hel.fi/stats/ -> http://localhost:8080/).

The API implements the
[HAL-specification](http://stateless.co/hal_specification.html), so the API can
be "navigated" using the `_links` and `_embedded` properties of the response
objects, eg the ["entry point"](http://dev.hel.fi/stats/resources/) listing
lists all the available datasets as "embedded resources", where the self-link
points to the table.

A [data table entrypoint](http://dev.hel.fi/stats/resources/aluesarjat_a03s_hki_vakiluku_aidinkieli/)
lists the available dimensions/columns/categories and other metadata and also
the supported methods as `_links`.

The API is also (partially) wrapped in as Statproxy-class in the Coffeescript
file `browser/statproxy.coffee`, which is the recommended way for accessing
the API for most common tasks when using Javascript/Coffeescript. Usage
examples can be found at [Helsinki Region Infoshare github demos](http://helsinkiregioninfoshare.github.io/hri-demos/).

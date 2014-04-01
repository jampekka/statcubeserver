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

## Examples

Click the links to see example results.

Browse datasets with a browser: [`/browser/`](http://dev.hel.fi/stats/browser/)

Preview a dataset and see available methods:  [`/browser/?resource=<resource uri>`](http://dev.hel.fi/stats/browser/?resource=http://dev.hel.fi/stats/resources/aluesarjat_a01hki_asuntokuntien_tulot)

Get available datasets: [`/resources/`](http://dev.hel.fi/stats/resources/)

Get dataset metadata and methods: [`/resources/<resource id>/`](http://dev.hel.fi/stats/resources/aluesarjat_a01hki_asuntokuntien_tulot/)

Get a filtered dataset: [`/resources/<resource_id>/filter<&col1=cat1,cat2&col2=cat3 ...>`](http://dev.hel.fi/stats/resources/aluesarjat_a01hki_asuntokuntien_tulot/http://dev.hel.fi/stats/resources/aluesarjat_a01hki_asuntokuntien_tulot/filter&alue=0910000000&tulotyyppi=5&vuosi=2010,2011/)

Get dataset's data (can be filtered) as "entries": [`/resources/<dataset path>/entries`](http://dev.hel.fi/stats/resources/aluesarjat_a01hki_asuntokuntien_tulot/http://dev.hel.fi/stats/resources/aluesarjat_a01hki_asuntokuntien_tulot/filter&alue=0910000000&tulotyyppi=5&vuosi=2010,2011/entries)

Get data as "table": [`/resources/<dataset path>/table[?start=firstrow&end=lastrow`](http://dev.hel.fi/stats/resources/aluesarjat_a01hki_asuntokuntien_tulot/http://dev.hel.fi/stats/resources/aluesarjat_a01hki_asuntokuntien_tulot/filter&alue=0910000000&tulotyyppi=5&vuosi=2010,2011/table)

Get data as "columns": [`/resources/<dataset path>/columns`](http://dev.hel.fi/stats/resources/aluesarjat_a01hki_asuntokuntien_tulot/http://dev.hel.fi/stats/resources/aluesarjat_a01hki_asuntokuntien_tulot/filter&alue=0910000000&tulotyyppi=5&vuosi=2010,2011/columns)

Get grouped data ("pivot") as columns: [`/resources/<dataset path>/group_for_columns?as_values=<col1,col2...>`](http://dev.hel.fi/stats/resources/aluesarjat_a01hki_asuntokuntien_tulot/http://dev.hel.fi/stats/resources/aluesarjat_a01hki_asuntokuntien_tulot/filter&alue=0910000000/group_for_columns?as_values=vuosi,value)

Get data as JSON-stat: [`/resources/<dataset path>/jsonstat`](http://dev.hel.fi/stats/resources/aluesarjat_a01hki_asuntokuntien_tulot/http://dev.hel.fi/stats/resources/aluesarjat_a01hki_asuntokuntien_tulot/filter&alue=0910000000&tulotyyppi=5&vuosi=2010,2011/jsonstat)

## Demos and advanced examples

http://helsinkiregioninfoshare.github.io/hri-demos/

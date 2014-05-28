# encoding: utf-8
import os
import sys
from urllib2 import urlopen
import urllib2
import urlparse
import json
import pydatacube
import pydatacube.pcaxis
import pydatacube.sql
import psycopg2

METADATA_URL="http://www.hri.fi/wp-content/uploads/ckan/hri-ckan-active-metadata-daily-output.json"

# From the werkzeug-project: https://github.com/mitsuhiko/werkzeug/blob/master/werkzeug/urls.py
import urllib
def url_fix(s, charset='utf-8'):
    """Sometimes you get an URL by a user that just isn't a real
    URL because it contains unsafe characters like ' ' and so on.  This
    function can fix some of the problems in a similar way browsers
    handle data entered by the user:

    >>> url_fix(u'http://de.wikipedia.org/wiki/Elf (Begriffsklärung)')
    'http://de.wikipedia.org/wiki/Elf%20%28Begriffskl%C3%A4rung%29'

    :param charset: The target charset for the URL if the url was
                    given as unicode string.
    """
    if isinstance(s, unicode):
        s = s.encode(charset, 'ignore')
    scheme, netloc, path, qs, anchor = urlparse.urlsplit(s)
    path = urllib.quote(path, '/%')
    qs = urllib.quote_plus(qs, ':&=')
    return urlparse.urlunsplit((scheme, netloc, path, qs, anchor))

def iterate_resources(packages):
	for package in packages:
		for resource in package['resources']:
			if resource['format'] != 'pc-axis':
				continue
			url = url_fix(resource['url'])
			yield dict(package=package, url=url, format='pc-axis')

def load_metadata(url):
	metadata = json.load(urlopen(url))
	packages = metadata['packages']
	return list(iterate_resources(packages))

if __name__ == '__main__':
	resources = load_metadata(METADATA_URL)
	con = psycopg2.connect(sys.argv[1])
	pydatacube.sql.initialize_schema(con)
	con.commit()
	for resource in resources:
		try:
			id = resource['package']['name']
			print >>sys.stderr, id

			con = psycopg2.connect(sys.argv[1])
			if pydatacube.sql.SqlDataCube.Exists(con, id):
				continue
			data = urlopen(resource['url'])
			try:
				cube = pydatacube.pcaxis.to_cube(data)
			except pydatacube.pcaxis.PxSyntaxError, e:
				print >>sys.stderr, "Px parsing failed:", e
				continue
			try:
				pydatacube.sql.SqlDataCube.FromCube(con, id, cube)
				con.commit()
			finally:
				con.close()
		except urllib2.HTTPError, e:
			print >>sys.stderr, e
	


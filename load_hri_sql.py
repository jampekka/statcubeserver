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

def load_resources(db_connection, replace=False):
	resources = load_metadata(METADATA_URL)
	def connect():
		return psycopg2.connect(db_connection)
	
	con = connect()
	pydatacube.sql.initialize_schema(con)
	con.commit()
	for resource in resources:
		try:
			id = resource['package']['name']
			#print >>sys.stderr, "Loading %s from %s"%(id, resource['url'])

			con = connect()
			if not replace:
				if pydatacube.sql.SqlDataCube.Exists(con, id):
					continue
			data = urlopen(resource['url'])
			try:
				cube = pydatacube.pcaxis.to_cube(data,
					origin_url=resource['url'])
			except pydatacube.pcaxis.PxSyntaxError, e:
				print >>sys.stderr, "Px parsing failed:", e
				continue
			try:
				pydatacube.sql.SqlDataCube.FromCube(con, id, cube, replace=True)
				con.commit()
			finally:
				con.close()
		except urllib2.HTTPError, e:
			print >>sys.stderr, "Download error", e, resource['package']['ckan_url']
			try:
				from urlparse import urlparse, parse_qs, urlunparse
				alternate = (r for r in resource['package']['resources'] if r['format'] == 'tietokanta').next()
				urlparts = urlparse(alternate['url'])
				url = parse_qs(urlparts.query)['bmark'][0].lower() + ".px"
				url = '/'.join(url.split('/')[1:])
				# WTF Guido, why is the URL API so damn horrible?
				url = urlunparse(list(urlparts[:2]) + [url] + ['']*3)
				print >>sys.stderr, "The right URL is probably %s"%(url,)
			except StopIteration:
				print >>sys.stderr, "'Tietokanta' link missing, can't guess the right url"
			print >>sys.stderr, ""
	

if __name__ == '__main__':
	import argh
	argh.dispatch_command(load_resources)

# encoding: utf-8
import os
import sys
from urllib2 import urlopen
import urllib2
import urlparse
import json

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
	from px_json_server import serve_px_resources
	resources = load_metadata(METADATA_URL)
	resource_list = []
	output_dir = sys.argv[1]
	for resource in resources:
		try:
			id = resource['package']['name']
			print >>sys.stderr, id
			format = 'pc-axis'
			outfilename = os.path.join(output_dir, "%s.%s"%(id, format))

			data = urlopen(resource['url'])
			with open(outfilename, 'w') as f:
				f.write(data.read())

			resource_list.append(dict(
				id=id,
				format=format,
				file=outfilename,
				origin_url=resource['url'],
			))
		except urllib2.HTTPError, e:
			print >>sys.stderr, e
	
	json.dump(resource_list, sys.stdout)


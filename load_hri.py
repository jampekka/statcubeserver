import os
import sys
from urllib2 import urlopen
import urllib2
import urlparse
import json

METADATA_URL="http://www.hri.fi/wp-content/uploads/ckan/hri-ckan-active-metadata-daily-output.json"


def iterate_resources(packages):
	for package in packages:
		for resource in package['resources']:
			if resource['format'] != 'pc-axis':
				continue
			yield dict(package=package, url=resource['url'], format='pc-axis')

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


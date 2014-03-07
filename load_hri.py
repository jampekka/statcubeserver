from urllib2 import urlopen
import json

METADATA_URL="http://www.hri.fi/wp-content/uploads/ckan/hri-ckan-active-metadata-daily-output.json"


def iterate_resources(packages):
	for package in packages:
		for resource in package['resources']:
			if resource['format'] != 'pc-axis':
				continue
			yield dict(url=resource['url'], format='pc-axis')

def load_metadata(url):
	metadata = json.load(urlopen(url))
	packages = metadata['packages']
	return list(iterate_resources(packages))


if __name__ == '__main__':
	from px_json_server import serve_px_resources
	resources = load_metadata(METADATA_URL)
	serve_px_resources(resources)



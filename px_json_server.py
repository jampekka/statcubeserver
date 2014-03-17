import sys
import itertools
from collections import OrderedDict
import urllib2
from urllib2 import urlopen
import urlparse
import os
from cStringIO import StringIO
import shelve

import cherrypy as cp
import pydatacube
import pydatacube.pcaxis
import pydatacube.jsonstat

def json_expose(func):
	func = cp.tools.json_out()(func)
	func.exposed = True
	return func

def is_exposed(obj):
	if getattr(obj, 'func_name', False) == 'index':
		return False
	
	if callable(obj) and getattr(obj, 'exposed', False):
		return True
	if hasattr(obj, 'index'):
		idx = getattr(obj, 'index')
		if callable(idx) and getattr(idx, 'exposed', False):
			return True
	
	return False

HAL_BLACKLIST = {'favicon_ico': True}
def default_hal_dir(obj):
	for name in dir(obj):
		if name.startswith('__'):
			continue
		if name in HAL_BLACKLIST:
			continue

		yield (name, getattr(obj, name))

def object_hal_links(obj, dirrer=default_hal_dir):
	links = {}
	if is_exposed(obj):
		links['self'] = {'href': cp.url(relative=False)}
	
	for name, value in dirrer(obj):
		if not is_exposed(value):
			continue
		link = {'href': cp.url(name, relative=False)}
		links[name] = link
	
	return links
		
class DictExposer(object):
	def __init__(self, mydict):
		self._dict = mydict
	
	@json_expose
	def index(self):
		objects = dict()
		for key, value in self._dict.iteritems():
			if hasattr(value, '_preview'):
				entry = OrderedDict(value._preview().iteritems())
			else:
				entry = OrderedDict()

			entry['_links'] = OrderedDict()
			entry['_links']['self'] = {
				'href': cp.url(key, relative=False)
				}
			objects[key] = entry

		ret = OrderedDict()
		ret['_embedded'] = objects
		ret['_links'] = object_hal_links(self)
		return ret

	def __getattr__(self, attr):
		try:
			return self._dict[attr]
		except KeyError:
			raise AttributeError("No item '%s'"%(attr))
			

class ResourceServer(object):
	def __init__(self, resources=None):
		if resources is None:
			resources = {}
		self._resources = resources
		self.resources = DictExposer(self._resources)
	
	@json_expose
	def index(self):
		ret = {}
		ret['_links'] = object_hal_links(self)
		return ret

class CubeResource(object):
	MAX_ENTRIES=100

	def __init__(self, lazycube):
		# A "lazy" cube so that we don't have to keep
		# it in memory
		# TODO: May be confusing
		self._lazycube = lazycube
		cube = self._lazycube()
		# Cache here so we don't have to deserialize
		# the large cube-object every time
		self._specification = cube.specification
		self._metadata = cube.metadata

	@json_expose
	def index(self):
		spec = self._specification
		spec['_links'] = object_hal_links(self)
		return spec

	@json_expose
	def json_entries(self, start=0, end=None,
			dimension_labels=False, category_labels=False):
		# TODO: No need to really iterate if
		# pydatacube would support slicing

		if end is None:
			end = self._specification['length']
		end = int(end)
		start = int(start)

		if end - start > self.MAX_ENTRIES:
			raise ValueError("No more than %i entries allowed at a time."%self.MAX_ENTRIES)

		entry_iter = self._lazycube().toEntries(
			dimension_labels=dimension_labels,
			category_labels=category_labels)
		entry_iter = itertools.islice(entry_iter, start, end)
		return list(map(OrderedDict, entry_iter))
	
	@json_expose
	def json_table(self, start=0, end=None, labels=False):
		# TODO: No need to really iterate if
		# pydatacube would support slicing

		if end is None:
			end = self._specification['length']
		end = int(end)
		start = int(start)

		if end - start > self.MAX_ENTRIES:
			raise ValueError("No more than %i entries allowed at a time."%self.MAX_ENTRIES)
		
		entry_iter = self._lazycube().toTable(labels=labels)
		entry_iter = itertools.islice(entry_iter, start, end)
		return list(map(list, entry_iter))
	
	@json_expose
	def columns(self,
			start=0, end=None,
			dimension_labels=False, category_labels=False,
			collapse_unique=True):
		return self._lazycube().toColumns(
			start=start, end=end,
			dimension_labels=dimension_labels,
			category_labels=category_labels,
			collapse_unique=collapse_unique)
	
	@json_expose
	def group_columns(self, as_values=None,
			dimension_labels=False, category_labels=False):
		if as_values is not None:
			as_values = as_values.split(',')
		groups = self._lazycube().groups(*as_values)
		groupcols = []
		for group in groups:
			col = group.toColumns(
				dimension_labels=dimension_labels,
				category_labels=category_labels)
			groupcols.append(col)
		return groupcols

	# TODO: Expose only if can be converted?
	@json_expose
	def jsonstat(self):
		return pydatacube.jsonstat.to_jsonstat(self._lazycube())

	
	def __filter(self, **kwargs):
		filters = {}
		for dim, catstr in kwargs.iteritems():
			filters[dim] = catstr.split(',')
		return CubeResource(lambda: self._lazycube().filter(**filters))
	
	def __getattr__(self, attr):
		parts = attr.split('&')
		if parts[0] != 'filter':
			return object.__getattr__(self, attr)
		args = []
		kwargs = {}
		for part in parts[1:]:
			split = part.split('=', 1)
			if len(split) == 1:
				args.append(split[0])
			else:
				kwargs[split[0]] = split[1]
		
		return self.__filter(*args, **kwargs)
	
	def _preview(self):
		return {'metadata': self._metadata}

class PxResource(CubeResource):
	def __init__(self, data, metadata, datastore):
		px_data = data.read()
		data = StringIO(px_data)
		datastore['cube'] = pydatacube.pcaxis.to_cube(data)
		CubeResource.__init__(self, lambda: datastore['cube'])
		datastore['pc-axis'] = px_data
	
	@cp.expose
	def pc_axis(self):
		return datastore['pc-axis']
	
def fetch_px_resource(spec, datastore):
	metadata = {}
	if 'file' in spec:
		data = open(spec['file'])
		url = "file://"+spec['file']
	else:
		url = spec['url']
		data = urlopen(spec['url'])
		
	if 'id' not in spec:
		parsed = urlparse.urlparse(url)
		basename = os.path.basename(parsed.path)
		basename = os.path.splitext(basename)[0]
		id = '%s:%s'%(parsed.netloc, basename)
	else:
		id = spec['id']
	
	metadata = dict(
		id=id
		)
	return id, PxResource(data, metadata, datastore(id))

class _Substore(object):
	def __init__(self, prefix, backend):
		self._prefix = prefix
		self._backend = backend
	
	def _getid(self, attr):
		return str(self._prefix + '/' + attr)

	def __getitem__(self, attr):
		return self._backend[self._getid(attr)]
	
	def __setitem__(self, attr, value):
		self._backend[self._getid(attr)] = value

class PrefixStore(object):
	def __init__(self, backend):
		self._backend = backend
	
	def __call__(self, id):
		return _Substore(id, self._backend)

class KeyValueCacheHack(object):
	def __init__(self, backend):
		self._last_key = None
		self._last_value = None
		self._backend = backend
	
	def __getitem__(self, key):
		if key == self._last_key:
			return self._last_value
		return self._backend[key]
	
	def __setitem__(self, key, value):
		self._last_key = key
		self._last_value = value
		self._backend[key] = value

def serve_px_resources(resources):
	my_root = os.path.dirname(os.path.abspath('__file__'))
	
	# TODO: Figure out nicer persistence
	# TODO: Really not necessary to recreate every time!
	shelve_file_path = my_root + "/px_json_server.shelve"
	backend = shelve.open(shelve_file_path, flag='c')
	storer = PrefixStore(KeyValueCacheHack(backend))
	
	px_resources = {}

	for spec in resources:
		try:
			id, px_resource = fetch_px_resource(spec, storer)
			px_resources[id] = px_resource
		except urllib2.HTTPError, e:
			print >>sys.stderr, "Fetching file failed", e, spec
		except pydatacube.pcaxis.PxSyntaxError, e:
			print >>sys.stderr, "Px parsing failed:", e, spec
	backend.sync()
	server = ResourceServer(px_resources)
	import string
	dispatch = cp.dispatch.Dispatcher(translate=string.maketrans('', ''))

	def CORS():
		cp.response.headers["Access-Control-Allow-Origin"] = "*"
	
	cp.tools.CORS = cp.Tool('before_finalize', CORS)
		

	config = {
		'/': {
			'request.dispatch': dispatch,
			'tools.CORS.on': True
		},
		'/browser': {
			'tools.staticdir.on': True,
			'tools.staticdir.root': my_root,
			'tools.staticdir.dir': 'browser',
			'tools.staticdir.index': 'index.html'
		}
	}
	
	cp.config.update(config)
	app = cp.tree.mount(server, '/', config=config)
	
	conffilepath = os.path.join(my_root, 'px_json_server.conf')
	if os.path.exists(conffilepath):
		cp.config.update(conffilepath)
		app.merge(conffilepath)

	cp.engine.signals.subscribe()
	cp.engine.start()
	cp.engine.block()

if __name__ == '__main__':
	import json
	serve_px_resources(json.load(open(sys.argv[1])))

import sys
import itertools
from collections import OrderedDict
import urllib2
from urllib2 import urlopen
import urlparse
import os
from cStringIO import StringIO
import shelve
import itertools
import re
import psycopg2
#import MySQLdb as mysql
#from MySQLdb.cursors import SSCursor
#import oursql as mysql
#import mysql.connector as mysql
import json

import cherrypy as cp
import pydatacube
import pydatacube.jsonstat
import pydatacube.sql

jsonp_callback_check = re.compile("^[a-zA-Z0-9_]+$")

def jsonp_tool(callback_name='callback'):
	def jsonp_handler(*args, **kwargs):
		request = cp.serving.request
		orig_handler = request._jsonp_inner_handler
		if callback_name not in request.params:
			return orig_handler(*args, **kwargs)
		callback = request.params.pop(callback_name)
		
		if not jsonp_callback_check.match(callback):
			raise ValueError("Invalid JSONP callback name")

		value = orig_handler(*args, **kwargs)
		ct = cp.serving.response.headers['Content-Type']

		if not ct.startswith("application/json"):
			return value
		
		cp.serving.response.headers['Content-Type'] = "application/javascript"
		if isinstance(value, basestring):
			return "%s(%s)"%(callback, str(value))
		# We probably have an iterator
		return itertools.chain((callback, '('), value, (')'))
		
	
	request = cp.serving.request
	request._jsonp_inner_handler = request.handler
	request.handler = jsonp_handler
	
cp.tools.jsonp = cp.Tool('before_handler', jsonp_tool, priority=31)

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

def int_or_none(val):
	if val is None: return None
	return int(val)

def str_to_bool(val):
	if val == 'true':
		return True
	if val == 'false':
		return False
	return val

class DbCubeResource(object):
	MAX_ENTRIES=1000
	MAX_GROUPS=100

	def __init__(self, cube):
		self._cube = cube
	
	@json_expose
	def index(self):
		spec = OrderedDict(self._cube.specification)
		spec['_links'] = object_hal_links(self)
		return spec
	
	def _get_rows(self, start, end, category_labels):
		start = int(start)
		end = int_or_none(end)
		if end is None:
			end = len(self._cube)
		if end - start > self.MAX_ENTRIES:
			raise ValueError("No more than %i entries allowed at a time. Use 'start' and 'end' parameters to limit the selection."%self.MAX_ENTRIES)
		result = self._cube.rows(start=start, end=end,
				category_labels=category_labels)
		return result

	@json_expose
	def entries(self, start=0, end=None, category_labels=False):
		names = self._cube.dimension_ids()
		result = self._get_rows(start, end, str_to_bool(category_labels))
		return [dict(zip(names, row)) for row in result]
	
	@json_expose
	def table(self, start=0, end=None, labels=False):
		result = self._get_rows(start, end, str_to_bool(labels))
		# mysql.connector's __len__ returns -1 which
		# breaks using list(result). Nice.
		return [r for r in result]
	
	@json_expose
	def columns(self, start=0, end=None, category_labels=False,
			dimension_labels=False):
		start = int(start)
		end = int_or_none(end)
		if end is None:
			end = len(self._cube)
		
		if end - start > self.MAX_ENTRIES:
			raise ValueError("No more than %i entries allowed at a time. Use 'start' and 'end' parameters to limit the selection."%self.MAX_ENTRIES)

		return self._cube.toColumns(start=start, end=end,
				category_labels=str_to_bool(category_labels),
				dimension_labels=str_to_bool(dimension_labels))
	
	@json_expose
	def group_for_columns(self, start=0, end=None, as_values=None,
			category_labels=False,
			dimension_labels=False):
		# TODO: This could be done more efficiently in SQL
		if as_values is not None:
			as_values = as_values.split(',')
		groups = self._cube.group_for(*as_values)
		if len(groups) > self.MAX_GROUPS:
			raise ValueError("No more than %i groups allowed at a time. Please use finer filtering."%self.MAX_GROUPS)
		groupcols = []
		category_labels = str_to_bool(category_labels)
		start = int(start)
		end = int_or_none(end)
		dimension_labels = str_to_bool(dimension_labels)
		for group in groups:
			if len(group) > self.MAX_ENTRIES:
				raise ValueError("No more than %i entries allowed at a time. Use 'start' and 'end' parameters to limit the selection."%self.MAX_ENTRIES)
			col = group.toColumns(start=start, end=end,
				category_labels=category_labels,
				dimension_labels=dimension_labels)
			groupcols.append(col)
		return groupcols
	
	@json_expose
	def jsonstat(self):
		return pydatacube.jsonstat.to_jsonstat(self._cube)
	
	@cp.expose
	def csv(self):
		cp.response.headers['Content-Type']='text/plain; charset=utf-8'
		
		hdr = [d['id'] for d in self._cube.specification['dimensions']]
		hdr = ",".join(hdr) + "\n"
		rows = (",".join(row)+"\n" for row in self._cube)
		return itertools.chain(hdr, rows)
	
	
	
	def __filter(self, **kwargs):
		filters = {}
		for dim, catstr in kwargs.iteritems():
			filters[dim] = catstr.split(',')
		return self.__class__(self._cube.filter(**filters))
	
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

	
class DatabaseExposer(object):
	def __init__(self, connector):
		self._connector = connector
	
	@json_expose
	def index(self):
		query = "SELECT id, specification FROM _datasets"
		con = self._connector()
		c = con.cursor()
		c.execute(query)
		entries = dict()
		for key, spec in c:
			spec = json.loads(spec)
			entry = OrderedDict()
			entry['metadata'] = spec['metadata']
			entry['_links'] = OrderedDict()
			entry['_links']['self'] = {
				'href': cp.url(key, relative=False)
				}
			entries[key] = entry


		ret = OrderedDict()
		ret['_embedded'] = entries
		ret['_links'] = object_hal_links(self)
		return ret
	
	def __getattr__(self, resource_id):
		if resource_id.startswith('_'):
			return object.__getattr__(self, resource_id)
		if resource_id is 'default':
			return object.__getattr__(self, resource_id)
		if resource_id is 'exposed':
			return object.__getattr__(self, resource_id)

		cube = pydatacube.sql.SqlDataCube(self._connector(), resource_id)
		return DbCubeResource(cube)
	

class ResourceServer(object):
	def __init__(self, resources):
		self.resources = resources
	
	@json_expose
	def index(self):
		ret = {}
		ret['_links'] = object_hal_links(self)
		return ret

def serve_sql():
	SERVER_ROOT = os.path.dirname(os.path.abspath('__file__'))
	
	import string
	dispatch = cp.dispatch.Dispatcher(translate=string.maketrans('', ''))

	def CORS():
		cp.response.headers["Access-Control-Allow-Origin"] = "*"
	
	cp.tools.CORS = cp.Tool('before_finalize', CORS)
		

	config = {
		'global': {
			'SERVER_ROOT_DIR': SERVER_ROOT
		},
		'/': {
			'request.dispatch': dispatch,
			'tools.CORS.on': True,
			'tools.jsonp.on': True
		},
		'/browser': {
			'tools.staticdir.on': True,
			'tools.staticdir.root': SERVER_ROOT,
			'tools.staticdir.dir': 'browser',
			'tools.staticdir.index': 'index.html'
		}
	}
	
	cp.config.update(config)
	conffilepath = os.path.join(SERVER_ROOT, 'sql_json_server.conf')
	if os.path.exists(conffilepath):
		cp.config.update(conffilepath)
	
	db_config = cp.config['database.connection']
	def connector():
		#import psycopg2.extras
		#con = psycopg2.extras.LoggingConnection(db_config)
		#con.initialize(sys.stdout)
		con = psycopg2.connect(db_config)
		# Autocommit allows query cache to work. This is a
		# bit of a hack, the proper way would be to automatically
		# commit the session after the request. Autocommit is
		# a bit slower, but with readonly mode shouldn't really
		# affect anything else.
		con.set_session(readonly=True, autocommit=True)
		return con
		#return mysql.connect(charset='utf8', use_unicode=True,
		#		cursorclass=SSCursor,
		#		**db_config)

	resources = DatabaseExposer(connector)
	server = ResourceServer(resources)

	app = cp.tree.mount(server, '/', config=config)
	
	if os.path.exists(conffilepath):
		app.merge(conffilepath)
	
	if hasattr(cp.engine, 'signals'):
		# Conditional for older cherrpy versions.
		# Not even sure what this does.
		cp.engine.signals.subscribe()
	cp.engine.start()
	cp.engine.block()

if __name__ == '__main__':
	serve_sql()

	


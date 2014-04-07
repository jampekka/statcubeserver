class @Statproxy
	constructor: (@url) ->
		if @url[0] != '/'
			@url = @url+'/'
	
	specification: =>
		return $.getJSON @url
	
	@specification_to_object: (spec) =>
		dictspec = _.clone spec
		dictspec.dimensions = {}
		dictspec.dimension_order = []
		for dim in spec.dimensions
			dictdim = dictspec.dimensions[dim.id] = _.clone dim
			dictspec.dimensions[dim.id] = dictdim
			dictspec.dimension_order.push dim.id
			dictdim.categories = {}
			dictdim.category_order = []
			if 'categories' not of dim
				continue
			for cat in dim.categories
				dictdim.categories[cat.id] = _.clone cat
				dictdim.category_order.push cat.id
		return dictspec

		

	filter: (categories) =>
		if _.isEmpty(categories)
			return @
		filters = []
		for dim, cats of categories
			if _.isArray cats
				cats = cats.join(',')
			if _.isObject cats
				cats = (cat for cat, en of cats when en)
				cats = cats.join(',')

			filters.push("#{dim}=#{cats}")
		url = @url + "filter&" + filters.join("&")
		return new Statproxy(url)

	entries: =>
		return $.getJSON @url + "/entries"

	columns: =>
		return $.getJSON @url + "/columns"
	
	group_for_columns: (as_values, opts={}) =>
		as_values = as_values.join(',')
		url = @url + "/group_for_columns?"
		url += $.param as_values: as_values
		opts = $.param opts
		if opts
			url += "&" + opts
		return $.getJSON url
		

class @Statproxy
	constructor: (@url) ->
		if @url[0] != '/'
			@url = @url+'/'
	
	specification: =>
		return $.getJSON @url

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

	columns: =>
		return $.getJSON @url + "/columns"
	
	group_columns: (as_values, opts={}) =>
		as_values = as_values.join(',')
		url = @url + "/group_columns?"
		url += $.param as_values: as_values
		opts = $.param opts
		if opts
			url += "&" + opts
		return $.getJSON url
		

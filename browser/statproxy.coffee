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
			filters.push("#{dim}=#{cats}")
		url = @url + "filter&" + filters.join("&")
		return new Statproxy(url)

	columns: =>
		return $.getJSON @url + "/columns"
		

label = (obj) ->
	if 'label' of obj
		return obj.label
	return obj.id

# TODO: This escalated quickly. Use nicer way to track
#	the state (eg. via pushstate etc)
@table_view = (el, columns, dataurl, datalen, pagelen=100) ->
	container = $('<div class="stat_table">').appendTo el
	filterlink = $('<a class="btn btn-success disabled pull-right">View filtered</a>').appendTo container

	hdrdiv = $('<div class="pull-right">')#.appendTo container
	table = $('<table class="table table-striped">').appendTo container
	header = $('<thead>').appendTo table
	headers = $('<tr>').appendTo header
	actual_url = dataurl
	
	n_pages = Math.round datalen/pagelen + 0.5
	
	filters = {}
	refilter = ->
		param = {}
		for dim, cats of filters
			enabled_cats = (cat for cat, enabled of cats when enabled)
			if enabled_cats.length == 0
				continue
			param[dim] = enabled_cats.join(',')
		
		if _.isEmpty param
			actual_url = dataurl
			filterlink.removeAttr('href')
			filterlink.addClass 'disabled'
		else
			actual_url = dataurl + 'filter&' + $.param(param) + "/"
			filterlink.attr('href', '?resource=' + encodeURIComponent actual_url)
			filterlink.removeClass 'disabled'
		$.getJSON(actual_url).done (spec) ->
			n_pages = Math.round spec.length/pagelen + 0.5
			load_data 1

	for dim in columns
		if 'categories' not of dim
			headers.append $("<th>#{label dim}</th>")
			continue
		filters[dim.id] = {}
		dropdown = $("""<select name="#{dim.id}" class="multiselect" multiple="multiple">""")
		for cat in dim.categories
			dropdown.append $ """
				<option value="#{cat.id}">#{label cat}</option>
				"""
		headers.append $("<th>").append dropdown
		dropdown.multiselect
			buttonText: do (dim) ->-> label dim
			onChange: do (dim) -> (el, selected) ->
				field = el.val()
				if selected
					filters[dim.id][field] = true
				else
					filters[dim.id][field] = false
				refilter()
			enableCaseInsensitiveFiltering: true

		
	body = $('<tbody>').appendTo table
	footer = $('<div class="pull-right">').appendTo container
	
	
	load_data = (page) ->
		start = (page-1)*pagelen
		end = start + pagelen
		body.empty()
		footer.empty()
		hdrdiv.empty()
		param = $.param
			start: start
			end: end
			labels: true
		
		url = actual_url + 'table?' + param
		$.ajax(url).done (rows) ->
			for row in rows
				rowel = $('<tr>').appendTo body
				for col in row
					rowel.append($ "<td>#{col}</td>")

			if page > 1
				prev = $('<a href="#">&lt; Previous</a>')
					.appendTo(footer)
				prev.click -> load_data page-1
				hdrdiv.append prev.clone(true)
			$("<span> page #{page} of #{n_pages} </span>")
				.appendTo(footer)
				.clone(true).appendTo(hdrdiv)
			
			if page < n_pages
				next = $('<a href="#">Next &gt;</a>')
					.appendTo(footer)
				next.click -> load_data page+1
				hdrdiv.append next.clone(true)
		

	
	load_data 1

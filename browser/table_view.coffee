@table_view = (el, columns, dataurl, datalen, pagelen=100) ->
	container = $('<div class="stat_table">').appendTo el
	hdrdiv = $('<div class="pull-right">').appendTo container
	table = $('<table class="table table-striped">').appendTo container
	header = $('<thead>').appendTo table
	headers = $('<tr>').appendTo header
	for col in columns
		headers.append $("<th>#{col}</th>")
	body = $('<tbody>').appendTo table
	footer = $('<div class="pull-right">').appendTo container
	
	n_pages = Math.round datalen/pagelen + 0.5
	
	load_data = (page) ->
		start = (page-1)*pagelen
		end = start + pagelen
		body.empty()
		footer.empty()
		hdrdiv.empty()
		param = $.param
			start: start
			end: end
		url = dataurl + '?' + param
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

#make_HTML_file(start,end,'12:00',search.filtered_table,just_best=True)
#[address,rating,# reviews,yelp link,rating img,duration to resto,distance to resto,minutes out of way,distance out of way]

import codecs
import pandas as pd

just_best=False

columns = {
	'address':0,
	'rating':1,
	'reviews':2,
	'url':3,
	'rating_img':4,
	'pic':5,
	'time_detour':6,
	'distance_detour':7,
	'time_to_resto':8,
	'distance_to_resto':9,
	'iphone_link':10
}

def write_resturants(resto_table_keys, resto_table, resto_destination_time, html_file, just_best):
	"""For each restaurant in the dict, make string of these restaurants in HTML file."""
	text = """\n<div class="col-lg-6">\n"""

	for resto_name in resto_table_keys:
		resto_data = resto_table[resto_name]

		first_batch = tuple([
			resto_data[columns['url']],
			resto_data[columns['pic']],
			resto_data[columns['url']],
			resto_name,
			resto_data[columns['rating_img']],
			resto_data[columns['reviews']],
			resto_data[columns['distance_to_resto']]
			])

		second_batch = tuple([
			resto_data[columns['distance_detour']],
			resto_data[columns['time_detour']],
			resto_data[columns['iphone_link']]
			])

		text += """<div class="media">\n<a class="pull-right" href="%s">\n<img class="media-object" class=\'img-responsive\' src="%s">\n</a>\n<div class="media-body">\n<h4 class="media-heading"><a href="%s">%s</a>\n<br><img src="%s" alt="Yelp rating image"></h4>\n<p>%i reviews\n<br>%.f mi away\n<br>""" % first_batch
		if just_best == False:
			text += """You will arrive in %.f mins""" % resto_data[columns['time_to_resto']]
		else:
			text += """You will arrive at %.f""" % resto_data[columns['time_to_resto']]
		text += """\n<br>%.f mi/%.f min detour\n<br><a href=\'%s'>view in iPhone app</a>\n</p>\n</div>\n</div>\n""" % second_batch

	html_file.write(text)

def write_results_file(resto_destination_time, search, just_best):
	"""Opens HTML file and writes to it."""
	sorted_resto_keys = sort_restos(search.filtered_table)

	html_file = codecs.open("./templates/results.html",'w','utf-8')
	html_file.write("""<!DOCTYPE html>\n<html lang="en"><head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8">\n<meta charset="utf-8">\n<meta http-equiv="X-UA-Compatible" content="IE=edge">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<meta name="description" content="Results page for Yelp Road Trip app">\n<meta name="author" content="Alexander Ko">\n\n<title>Yelp Road Trip results</title>\n\n<!-- Bootstrap core CSS -->\n<link href="./../static/css/bootstrap.min.css" rel="stylesheet">\n<!-- Custom styles for this template -->\n<link href="./../static/css/jumbotron-narrow.css" rel="stylesheet">\n<link href="./../static/css/navbar-fixed-top.css" rel="stylesheet">\n\n</head>\n\n\n<body class=" hasGoogleVoiceExt">\n\n<div class="container">\n\n<nav class="navbar navbar-default navbar-fixed-top" role="navigation">\n  <div class="container-fluid">\n    <!-- Brand and toggle get grouped for better mobile display -->\n    <div class="navbar-header">\n      <button type="button" class="navbar-toggle" data-toggle="collapse" data-target="#bs-example-navbar-collapse-1">\n        <span class="sr-only">Toggle navigation</span>\n        <span class="icon-bar"></span>\n        <span class="icon-bar"></span>\n        <span class="icon-bar"></span>\n      </button>\n      <a class="navbar-brand" href="{{ url_for(\'show_input_form\') }}">Yelp Road Trip</a>\n\n      <!--<div class="page-header">\n        <h1>Yelp</h1>\n        <div class="tagline">Road trip</div>\n      </div>-->\n    </div>\n\n    <!-- Collect the nav links, forms, and other content for toggling -->\n    <div class="collapse navbar-collapse" id="bs-example-navbar-collapse-1">\n      <ul class="nav navbar-nav">\n        <li><a href="{{ url_for(\'map\') }}">Map</a></li>\n        <li class="active"><a href="#">Results</a></li>\n      </ul>\n\n    </div><!-- /.navbar-collapse -->\n  </div><!-- /.container-fluid -->\n</nav>\n\n<div class="row marketing">""")

	# I do this twice bc there are 2 columns for the HTML file
	write_resturants(sorted_resto_keys[:4], search.filtered_table, resto_destination_time, html_file, just_best)
	html_file.write('\n</div>\n')
	write_resturants(sorted_resto_keys[4:], search.filtered_table, resto_destination_time, html_file, just_best)

	html_file.write("""\n</div> <!-- /container -->\n\n\n<!-- Bootstrap core JavaScript\n================================================== -->\n<!-- Placed at the end of the document so the pages load faster -->\n\n\n<iframe id="rdbIndicator" width="100%" height="270" border="0" src="./results_files/indicator.html" style="display: none; border: 0; position: fixed; left: 0; top: 0; z-index: 2147483647"></iframe></body></html>""")

	html_file.close()

def sort_restos(filtered_table):
	"""Take dict of restos and their attributes, and get a sorted list of keys as a list, sorted by distance to resto."""
	df = pd.DataFrame(filtered_table).T
	df = df.sort(columns=columns['time_to_resto'])

	return df.index

#write_results_file('3:00pm', False)

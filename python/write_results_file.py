#make_HTML_file(start,end,'12:00',search.filtered_table,just_best=True)
#[address,rating,# reviews,yelp link,rating img,duration to resto,distance to resto,minutes out of way,distance out of way]

import codecs

def write_resturants(resto_table_keys, resto_table, resto_destination_time, html_file, just_best):
	"""For each restaurant in the dict, make string of these restaurants in HTML file."""
	text = """\n<div class="col-lg-6">\n"""

	for resto_name in resto_table_keys:
		resto_data = resto_table[resto_name]

		info = ['resto pic', resto_name, str(resto_data[4]), str(resto_data[2]), str(int(resto_data[8]*0.000621371))]
		if just_best==False:
			info.append(str(resto_destination_time))
		else:
			info.append(str(resto_destination_time))
		info.append(str(int(resto_data[6]*0.000621371)))
		info.append(str(int(float(resto_data[5])/60))) # converting to minutes
		info.append(str(resto_data[3]))
		info.append(convert_to_yelp_app_link(str(resto_data[3]))) # which is the Yelp mobile link

		text += """<div class="media">\n<a class="pull-right" href="#">\n<img class="media-object" class=\'img-responsive\' src="%s">\n</a>\n<div class="media-body">\n<h4 class="media-heading">%s\n<br><img src="%s" alt="Yelp rating image"></h4>\n<p>%s reviews\n<br>%s mi away\n<br>""" % tuple(info[:5])
		if just_best == False:
			text += """You will arrive in %s mins""" % info[5]
		else:
			text += """You will arrive at %s""" % info[5]
		text += """\n<br>%s mi/%s min detour\n<br><a href=\'%s\'>visit Yelp page</a>\n<br><a href=\'%s'>view in iPhone app</a>\n</p>\n</div>\n</div>\n""" % tuple(info[6:])

	html_file.write(text)

def write_results_file(resto_destination_time, search, just_best):
	"""Opens HTML file and writes to it."""
	html_file = codecs.open("./templates/results.html",'w','utf-8')

	html_file.write("""<!DOCTYPE html>\n<html lang="en"><head><meta http-equiv="Content-Type" content="text/html; charset=UTF-8">\n<meta charset="utf-8">\n<meta http-equiv="X-UA-Compatible" content="IE=edge">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<meta name="description" content="Results page for Yelp Road Trip app">\n<meta name="author" content="Alexander Ko">\n\n<title>Yelp Road Trip results</title>\n\n<!-- Bootstrap core CSS -->\n<link href="./../static/css/bootstrap.min.css" rel="stylesheet">\n<!-- Custom styles for this template -->\n<link href="./../static/css/jumbotron-narrow.css" rel="stylesheet">\n<link href="./../static/css/navbar-fixed-top.css" rel="stylesheet">\n\n</head>\n\n\n<body class=" hasGoogleVoiceExt">\n\n<div class="container">\n\n<nav class="navbar navbar-default navbar-fixed-top" role="navigation">\n  <div class="container-fluid">\n    <!-- Brand and toggle get grouped for better mobile display -->\n    <div class="navbar-header">\n      <button type="button" class="navbar-toggle" data-toggle="collapse" data-target="#bs-example-navbar-collapse-1">\n        <span class="sr-only">Toggle navigation</span>\n        <span class="icon-bar"></span>\n        <span class="icon-bar"></span>\n        <span class="icon-bar"></span>\n      </button>\n      <a class="navbar-brand" href="{{ url_for(\'show_input_form\') }}">Yelp Road Trip</a>\n\n      <!--<div class="page-header">\n        <h1>Yelp</h1>\n        <div class="tagline">Road trip</div>\n      </div>-->\n    </div>\n\n    <!-- Collect the nav links, forms, and other content for toggling -->\n    <div class="collapse navbar-collapse" id="bs-example-navbar-collapse-1">\n      <ul class="nav navbar-nav">\n        <li class="active"><a href="./map.html">Map</a></li>\n        <li><a href="#">Results</a></li>\n      </ul>\n\n    </div><!-- /.navbar-collapse -->\n  </div><!-- /.container-fluid -->\n</nav>\n\n<div class="row marketing">""")

	# I do this twice bc there are 2 columns for the HTML file
	write_resturants(search.filtered_table.keys()[:4], search.filtered_table, resto_destination_time, html_file, just_best)
	html_file.write('\n</div>\n')
	write_resturants(search.filtered_table.keys()[4:], search.filtered_table, resto_destination_time, html_file, just_best)

	html_file.write("""\n</div> <!-- /container -->\n\n\n<!-- Bootstrap core JavaScript\n================================================== -->\n<!-- Placed at the end of the document so the pages load faster -->\n\n\n<iframe id="rdbIndicator" width="100%" height="270" border="0" src="./results_files/indicator.html" style="display: none; border: 0; position: fixed; left: 0; top: 0; z-index: 2147483647"></iframe></body></html>""")

	html_file.close()

def convert_to_yelp_app_link(website_link):
	"""Takes a Yelp mobile website link and converts it to open in the iPhone app"""
	unique_id=website_link[17:]
	yelp_link_start='yelp://'
	return yelp_link_start+unique_id

#write_results_file('3:00pm', False)

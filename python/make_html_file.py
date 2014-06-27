import codecs, grequests, datetime
from python.sensitive_info import *
from numpy import average

def make_HTML_file(start_point,end_point,time_leaving,resto_table,just_best=False):
	"""Resto_addresses is a table of just addresses."""

	file=codecs.open("./templates/map.html",'w','utf-8')

	locations=[] # many locations to put on map
	infowindows=[]
	coordinates=[]

	### Part 0: Take dict resto_table and put JS infowindow code into a list on the HTML file
	def fix_quotes(input):
		"""Take a string that might contain single quotes and adds backslash before each one."""
		# doesn't account for double quotes
		output=[]
		for i in range(len(input)):
			if input[i]=="'":
				output.append('\\')
				output.append(input[i])
			else:
				output.append(input[i])
		return ''.join(output)

	def add_infowindow(resto,number,time_leaving,just_best=False):
		resto_data=resto_table[resto]
		
		if just_best==False:
			start_time_repr=datetime.datetime.strptime(time_leaving, '%H:%M')
			resto_destination_time=datetime.datetime.strftime(start_time_repr+datetime.timedelta(seconds=resto_data[7]),'%I:%M%p')
			resto_destination_time = resto_destination_time.lstrip('0')
			resto_destination_time = resto_destination_time[:len(resto_destination_time)-2]+resto_destination_time[len(resto_destination_time)-2:].lower() # makes the last two characters lowercase
		else:
			resto_destination_time=int(resto_data[7]/60)

		infowindow=range(22)
		infowindow[0]="var contentString"
		infowindow[1]=str(number)
		infowindow[2]="= \n\'<h3 id=\"firstHeading\" class=\"firstHeading\">"
		infowindow[3]=fix_quotes(resto)
		infowindow[4]="\'+\n\'<br><img src=\""
		infowindow[5]=str(resto_data[4])
		infowindow[6]="\" alt=\"Yelp rating image\">\'+\n\'</h3><p>"
		infowindow[7]=str(resto_data[2])
		infowindow[8]=" reviews<br>\'+\n\'"
		infowindow[9]=str("%0.1f" % (resto_data[8]*0.000621371)) # keepin this as 1 decimal place bc more important this be accurate
		if just_best==False:
			infowindow[10]=" mi away<br>'+\n\'You will arrive at "
			infowindow[11]=str(resto_destination_time)
			infowindow[12]="<br>\'+\n\'"
		else:
			infowindow[10]=" mi away<br>'+\n\'You will arrive in "
			infowindow[11]=str(resto_destination_time)
			infowindow[12]=" mins.<br>\'+\n\'"		
		infowindow[13]=str(int(resto_data[6]*0.000621371)) 
		infowindow[14]=" mi/"
		infowindow[15]=str(int(float(resto_data[5])/60)) # converting to minutes
		infowindow[16]=" min detour</p>\'+\n\'<a href=\""
		infowindow[17]=str(resto_data[3])
		infowindow[18]="\" target=\"\_blank\">visit Yelp page</a>\'+"
		infowindow[19]="\n\'<p><a href=\""
		infowindow[20]=convert_to_yelp_app_link(infowindow[17]) # which is the Yelp mobile link
		infowindow[21]="\" target=\"\_blank\">view in iPhone app</a></p>\'"
		return ''.join(infowindow)

	number=0
	for resto in resto_table:
		number+=1
		if just_best==False:
			infowindows.append(add_infowindow(resto,number,time_leaving))
		else:
			infowindows.append(add_infowindow(resto,number,'placeholder',just_best=True))

	### Part 1: Take resto addresses and add their coordinates to a JS list called locations on the HTML file.

	def geocode_address(address,sensor='false'):
		"""Input address and returns back the response object."""
		payload = {'address':address+', USA','sensor':sensor,'key': key}
		site='https://maps.googleapis.com/maps/api/geocode/json'
		r = grequests.get(site, params=payload)
		return r

	def show_coordinates(thejson):
		"""Inputs Geoccoding JSON and returns the lat long dict."""
		return thejson['results'][0]['geometry']['location']

	def add_location(latlngdict,number):
		"""Takes latlong dict and puts it as a string into locations. When written, this will be a JS location object."""
		location=range(4)
		location[0]='[contentString' # to change
		location[1]=str(number)+', '
		location[2]=str(latlngdict['lat'])+','+str(latlngdict['lng'])+','
		location[3]=str(number)+'],'

		return ''.join(location)

	address_table = [resto_table[resto][0] for resto in resto_table]
		
	rs = [geocode_address(address) for address in address_table]
	print 'Geocoding all',len(rs),'addresses at once...'
	responses = grequests.map(rs)
	thejsons = [response.json() for response in responses]
	coordinates = [show_coordinates(ajson) for ajson in thejsons]

	number=0
	for coordinate in coordinates:
		number+=1
		locations.append(add_location(coordinate,number)) # 0 being the address
		
	print 'done'

	lats=[row['lat'] for row in coordinates]
	lngs=[row['lng'] for row in coordinates]
	
	avg_lat=average(sorted(lats)[1:len(lats)-1]) # removes the first and last values, in case 1 address was weird and messes up the center point
	avg_lng=average(sorted(lngs)[1:len(lngs)-1])

	### Part 2: Take all the elements of the HTML file and write them.

	list_of_elements=range(14)

	list_of_elements[0]="""<!DOCTYPE html>\n<html>\n  <head>\n    <meta name="viewport" content="initial-scale=1.0, user-scalable=no">\n    <meta charset="utf-8">\n    <title>Directions service</title>\n    <link href="./../static/css/bootstrap.min.css" rel="stylesheet">\n    <style>\n      html, body, #map-canvas {\n        height: 100%;\n        margin: 0px;\n        padding: 0px\n      }\n      #panel {\n        position: absolute;\n        top: 5px;\n        left: 50%;\n        margin-left: -180px;\n        z-index: 5;\n        background-color: #fff;\n        padding: 5px;\n        border: 1px solid #999;\n      }\n    </style>\n    <script src="https://maps.googleapis.com/maps/api/js?v=3.exp&sensor=false"></script>\n    <script>\n\tvar directionsDisplay;\n\tvar directionsService = new google.maps.DirectionsService();\n\tvar map;\n\n\tvar start_point = \'"""
	list_of_elements[1]=start_point #'2312,31321'
	list_of_elements[2]="';\n\tvar end_point = '"
	list_of_elements[3]=end_point #'2312,31321'
	list_of_elements[4]="\';\n\n\tfunction initialize() {\n\t\tvar mapOptions = {\n\t\t  center: new google.maps.LatLng("
	list_of_elements[5]=str(avg_lat)+", "
	list_of_elements[6]=str(avg_lng)+"),\n\t\t  zoom: 10\n\t\t};\n\t\t\n\t"
	list_of_elements[7]='\n\n'.join(infowindows)
	list_of_elements[8]="\n\n\tvar map = new google.maps.Map(document.getElementById(\"map-canvas\"),mapOptions);\n\n    var locations = [\n\t"
	list_of_elements[9]='\n\t'.join(locations)
	list_of_elements[10]="\n    ];\n\n    var infowindow = new google.maps.InfoWindow();\n\n    var marker, i;\n\n    for (i = 0; i < locations.length; i++) {  \n      marker = new google.maps.Marker({\n        position: new google.maps.LatLng(locations[i][1], locations[i][2]),\n        map: map\n      });\n\n      google.maps.event.addListener(marker, \'click\', (function(marker, i) {\n        return function() {\n          infowindow.setContent(locations[i][0]);\n          infowindow.open(map, marker);\n        }\n      })(marker, i));\n\t  \n\t  google.maps.event.addListener(map, \'click\', function() {\n\t\tinfowindow.close(map,marker);\n\t});\n    }\n\n\tdirectionsDisplay = new google.maps.DirectionsRenderer();"
	if just_best==False:
		list_of_elements[11]="\n\t  directionsDisplay.setOptions({preserveViewport:true});"
	else:
		list_of_elements[11]=''
	list_of_elements[12]="\n\t  directionsDisplay.setMap(map);\n\t}\n\n\tfunction calcRoute() {\n\t\tvar request = {\n\t\t  origin:start_point,\n\t\t  destination:end_point,\n\t\t  travelMode: google.maps.TravelMode.DRIVING\n\t\t};\n\t\t\n\t\tdirectionsService.route(request, function(response, status) {\n\t\t\tif (status == google.maps.DirectionsStatus.OK) {\n\t\t\t  directionsDisplay.setDirections(response);\n\t\t\t}\n\t\t});\n\t}\n\n\tcalcRoute()\n\tgoogle.maps.event.addDomListener(window, \'load\', initialize);\n    </script>\n  </head>\n"
	list_of_elements[13]="""<body>\n\n<nav class="navbar navbar-default navbar-fixed-top" role="navigation">\n  <div class="container-fluid">\n    <!-- Brand and toggle get grouped for better mobile display -->\n    <div class="navbar-header">\n      <button type="button" class="navbar-toggle" data-toggle="collapse" data-target="\\#bs-example-navbar-collapse-1">\n        <span class="sr-only">Toggle navigation</span>\n        <span class="icon-bar"></span>\n        <span class="icon-bar"></span>\n        <span class="icon-bar"></span>\n      </button>\n      <a class="navbar-brand" href="{{ url_for(\'show_input_form\') }}">Yelp Road Trip</a>\n    </div>\n\n    <!-- Collect the nav links, forms, and other content for toggling -->\n    <div class="collapse navbar-collapse" id="bs-example-navbar-collapse-1">\n      <ul class="nav navbar-nav">\n        <li class="active"><a href="#">Map</a></li>\n        <li><a href="{{ url_for(\'results\') }}">Results</a></li>\n      </ul>\n\n    </div><!-- /.navbar-collapse -->\n  </div><!-- /.container-fluid -->\n</nav>\n    <div id="map-canvas"/>\n  </body>\n</html>"""

	for each in list_of_elements:
		file.write(each)
	
	file.close()

def convert_to_yelp_app_link(website_link):
	"""Takes a Yelp mobile website link and converts it to open in the iPhone app"""
	unique_id=website_link[17:]
	yelp_link_start='yelp://'
	return yelp_link_start+unique_id
import codecs
import grequests
import datetime
from python.main import columns
from numpy import average
from python.main import make_arrival_phrase
from os import environ

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

def geocode_address(address):
	"""Input address and returns back the response object."""
	payload = {'address':address+', USA', 'key': environ['gmaps_key']}
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

def convert_to_yelp_app_link(website_link):
	"""Takes a Yelp mobile website link and converts it to open in the iPhone app"""
	unique_id=website_link[17:]
	yelp_link_start='yelp://'
	return yelp_link_start+unique_id

class write_map_file(object):
	def __init__(self, start_point, end_point, resto_table, just_best, time_leaving=None):
		self.just_best = just_best
		self.resto_table = resto_table
		self.time_leaving = time_leaving
		self.main(start_point, end_point)

	def add_infowindow(self, resto, number):
		resto_data = self.resto_table[resto]

		first_batch = tuple([
			number,
			resto_data[columns['url']],
			fix_quotes(resto),
			resto_data[columns['url']],
			resto_data[columns['rating_img']],
			resto_data[columns['reviews']],
			resto_data[columns['distance_to_resto']]
			])

		second_batch = tuple([
			resto_data[columns['distance_detour']],
			resto_data[columns['time_detour']],
			resto_data[columns['iphone_link']]
			])

		text = """var contentString%i= \n\'<h4 class="media-heading"><a href="%s" target="\\_blank">%s</a>\'+\n\'<br><a href="%s" target="\\_blank"><img src="%s" alt="Yelp rating image"></a>\'+\n\'</h4><p>%i reviews<br>\'+\n\'%.f mi away<br>\'+\n\'""" % first_batch
		text += make_arrival_phrase(self.time_leaving, resto_data[columns['time_to_resto']], self.just_best)
		text += """<br>\'+\n\'%.f mi/%.f min detour</p>\'+\n\'<p><a href="%s" target="\\_blank">view in iPhone app</a></p>\'""" % second_batch

		return text

	def main(self, start_point, end_point):
		file = codecs.open("./templates/map.html",'w','utf-8')

		locations=[] # many locations to put on map
		infowindows=[]
		coordinates=[]

		### Part 0: Take dict resto_table and put JS infowindow code into a list on the HTML file
		number=0
		for resto in self.resto_table:
			number+=1
			if self.just_best==False:
				infowindows.append(self.add_infowindow(resto,number))
			elif self.just_best==True:
				infowindows.append(self.add_infowindow(resto,number))

		### Part 1: Take resto addresses and add their coordinates to a JS list called locations on the HTML file.
		address_table = [self.resto_table[resto][0] for resto in self.resto_table]
			
		rs = [geocode_address(address) for address in address_table]
		print 'Geocoding all',len(rs),'addresses at once...'
		responses = grequests.map(rs)
		thejsons = [response.json() for response in responses]
		coordinates = [show_coordinates(ajson) for ajson in thejsons]

		self.json = thejsons
		self.coordinates = coordinates
		self.address = address_table

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

		list_of_elements[0]="""<!DOCTYPE html>\n<html>\n  <head>\n    <meta name="viewport" content="initial-scale=1.0, user-scalable=no">\n    <meta name="viewport" content="width=device-width, minimal-ui"><meta charset="utf-8">\n<meta charset="utf-8">\n    <title>Directions service</title>\n    <link href="./../static/css/bootstrap.min.css" rel="stylesheet">\n    <style>\n      html, body, #map-canvas {\n        height: 100%;\n        margin: 0px;\n        padding: 0px\n      }\n      #panel {\n        position: absolute;\n        top: 5px;\n        left: 50%;\n        margin-left: -180px;\n        z-index: 5;\n        background-color: #fff;\n        padding: 5px;\n        border: 1px solid #999;\n      }\n    </style>\n    <script src="https://maps.googleapis.com/maps/api/js?v=3.exp&sensor=false"></script>\n    <script>\n\tvar directionsDisplay;\n\tvar directionsService = new google.maps.DirectionsService();\n\tvar map;\n\n\tvar start_point = \'"""
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
		if self.just_best==False:
			list_of_elements[11]="\n\t  directionsDisplay.setOptions({preserveViewport:true});"
		elif self.just_best==True:
			list_of_elements[11]=''
		list_of_elements[12]="\n\t  directionsDisplay.setMap(map);\n\t}\n\n\tfunction calcRoute() {\n\t\tvar request = {\n\t\t  origin:start_point,\n\t\t  destination:end_point,\n\t\t  travelMode: google.maps.TravelMode.DRIVING\n\t\t};\n\t\t\n\t\tdirectionsService.route(request, function(response, status) {\n\t\t\tif (status == google.maps.DirectionsStatus.OK) {\n\t\t\t  directionsDisplay.setDirections(response);\n\t\t\t}\n\t\t});\n\t}\n\n\tcalcRoute()\n\tgoogle.maps.event.addDomListener(window, \'load\', initialize);\n    </script>\n  </head>\n"
		list_of_elements[13]="""<body>\n\n<nav class="navbar navbar-default navbar-fixed-top" role="navigation">\n  <div class="container-fluid">\n    <!-- Brand and toggle get grouped for better mobile display -->\n    <div class="navbar-header">\n      <button type="button" class="navbar-toggle" data-toggle="collapse" data-target="\\#bs-example-navbar-collapse-1">\n        <span class="sr-only">Toggle navigation</span>\n        <span class="icon-bar"></span>\n        <span class="icon-bar"></span>\n        <span class="icon-bar"></span>\n      </button>\n      <a class="navbar-brand" href="{{ url_for(\'show_input_form\') }}">Yelp Road Trip</a>\n    </div>\n\n    <!-- Collect the nav links, forms, and other content for toggling -->\n    <div class="collapse navbar-collapse" id="bs-example-navbar-collapse-1">\n      <ul class="nav navbar-nav">\n        <li class="active"><a href="{{ url_for('map') }}">Map</a></li>\n        <li><a href="{{ url_for(\'results\') }}">Results</a></li>\n      </ul>\n\n    </div><!-- /.navbar-collapse -->\n  </div><!-- /.container-fluid -->\n</nav>\n    <div id="map-canvas"/>\n  </body>\n</html>"""

		for each in list_of_elements:
			file.write(each)
		
		file.close()
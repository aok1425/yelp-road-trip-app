import os, codecs, datetime
from flask import Flask, request, url_for, render_template, redirect, flash
from python.main import *

app = Flask(__name__)

@app.route('/')
def show_input_form():
    return render_template('input_form.html')

def check_time(start,end,start_time,eating_time_start):
	"""Did I put an eating time correctly, before I arrive?."""
	result=get_gmaps_json(start,end)

	start_time_repr=datetime.datetime.strptime(start_time, '%H:%M')
	drive_duration=result['routes'][0]['legs'][0]['duration']['value'] # in seconds
	destination_time_repr=start_time_repr+datetime.timedelta(seconds=drive_duration)
	destination_time=datetime.datetime.strftime(destination_time_repr,'%I:%M%p')
	destination_time = destination_time.lstrip('0')
	destination_time = destination_time[:len(destination_time)-2]+destination_time[len(destination_time)-2:].lower() # makes the last two characters lowercase
	print 'You will arrive at',end,'at',destination_time
	
	eating_time_repr=datetime.datetime.strptime(eating_time_start, '%H:%M')
	
	if eating_time_repr<destination_time_repr:
		return 'yes'
	else:
		return destination_time
	
def change_loading_screen(end,destination_time): # not used bc loading page doesn't update like that
	"""Adds time to destination on layout.html."""
	#f=open('c:/users/alex/desktop/test.html','r')
	f=open(app.root_path+"/templates/layout.html",'r')
	g=f.readlines()
	f.close()
	#f=open('c:/users/alex/desktop/test.html','w')
	f=open(app.root_path+"/templates/layout.html",'w')
	g[18]='    <p>You will arrive in ' + end + ' at ' + destination_time + '.</p><p>...loading great restaurants</p>\n'
	f.writelines(g)
	f.close()
	
@app.route('/test')
def test():
    return redirect(url_for('static', filename='search_points.html'))

@app.errorhandler(500)
def pageNotFound(error):
	print 'writing error file...'
	with codecs.open(app.root_path+"/static/log.txt",'a','utf-8') as f:
		f.write('"'+'","'.join([str(datetime.datetime.now()),'ERROR',request.form['start'],request.form['end'],request.form['time_leaving'],request.form['eating_time']])+'"'+'\n')
	print 'done writing'
	return redirect(url_for('static', filename='error_page.htm'))
	
@app.route('/add', methods=['POST'])
def add_entry():
	start=request.form['start']
	end=request.form['end']
	time_leaving=request.form['time_leaving']
	eating_time=request.form['eating_time']
		
	if request.form['button']=='Find great restaurants':
		print 'I\'m feeling lucky option chosen.'
		with codecs.open(app.root_path+"/static/log.txt",'a','utf-8') as f:
			f.write('"'+'","'.join([str(datetime.datetime.now()),start,end,'I\'m feeling lucky','I\'m feeling lucky'])+'"'+'\n')
		search = RestaurantFinder(start,end,20,2,'12:00','15:00',9,30,15,15,just_best=True,radius=20000) # GMaps Dist Matrix API can only handle 9
		make_HTML_file(start,end,'12:00',search.filtered_table,just_best=True)
	else:
		print 'Regular option chosen.'
		destination_time=check_time(start,end,time_leaving,eating_time)
		#change_loading_screen(end,destination_time) # not used bc loading page doesn't update like that
		print 'Checking the times...'
		if destination_time=='yes':
			with codecs.open(app.root_path+"/static/log.txt",'a','utf-8') as f:
				f.write('"'+'","'.join([str(datetime.datetime.now()),start,end,time_leaving,eating_time])+'"'+'\n')
			search = RestaurantFinder(start,end,20,20,time_leaving,eating_time,9,40,20,20) # GMaps Dist Matrix API can only handle 9
		else:
			print 'Bc eating time is too late, I will replace that w/destination time.'
			destination_time_repr=datetime.datetime.strptime(destination_time, '%I:%M%p')
			final_time_repr=destination_time_repr-datetime.timedelta(minutes=45) # choose a point 30 mins before final destination
			final_time=datetime.datetime.strftime(final_time_repr,'%H:%M')	
			with codecs.open(app.root_path+"/static/log.txt",'a','utf-8') as f:
				f.write('"'+'","'.join([str(datetime.datetime.now()),start,end,time_leaving,eating_time,destination_time,'eating time is after destination time'])+'"'+'\n')
			print 'time I will input is',final_time
			search = RestaurantFinder(start,end,20,20,time_leaving,final_time,9,40,20,20) # GMaps Dist Matrix API can only handle 9
		make_HTML_file(start,end,time_leaving,search.filtered_table)

	return redirect(url_for('static', filename='map.html'))

def make_HTML_file(start_point,end_point,time_leaving,resto_table,just_best=False):
	"""Resto_addresses is a table of just addresses."""
	# I'm assumong here that w/the dixt, the order will always be the same, so I can make mltuple lists out of it.
	#file=open('c:/users/alex/desktop/map.html','w')
	file=codecs.open(app.root_path+"/static/map.html",'w','utf-8')
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
			#print 'You will arrive at',end,'at',datetime.datetime.strftime(start_time_repr+datetime.timedelta(seconds=drive_duration),'%I:%M%p')
		else:
			resto_destination_time=int(resto_data[7]/60)

		infowindow=range(22)
		infowindow[0]="var contentString"
		infowindow[1]=str(number)
		infowindow[2]="= \n\'<h2 id=\"firstHeading\" class=\"firstHeading\">"
		infowindow[3]=fix_quotes(resto)
		infowindow[4]="</h2>\'+\n\'<img src=\""
		infowindow[5]=str(resto_data[4])
		infowindow[6]="\" alt=\"Yelp rating image\">\'+\n\'<p>"
		infowindow[7]=str(resto_data[2])
		infowindow[8]=" reviews</p>\'+\n\'<p>"
		infowindow[9]=str("%0.1f" % (resto_data[8]*0.000621371)) # keepin this as 1 decimal place bc more important this be accurate
		if just_best==False:
			infowindow[10]=" mi away</p>'+\n\'<p>You will arrive at "
			infowindow[11]=str(resto_destination_time)
			infowindow[12]="</p>\'+\n\'<p>"
		else:
			infowindow[10]=" mi away</p>'+\n\'<p>You will arrive in "
			infowindow[11]=str(resto_destination_time)
			infowindow[12]=" mins.</p>\'+\n\'<p>"		
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

	list_of_elements=range(13)

	list_of_elements[0]="<!DOCTYPE html>\n<html>\n  <head>\n    <meta name=\"viewport\" content=\"initial-scale=1.0, user-scalable=no\">\n    <meta charset=\"utf-8\">\n    <title>Directions service</title>\n    <style>\n      html, body, #map-canvas {\n        height: 100%;\n        margin: 0px;\n        padding: 0px\n      }\n      #panel {\n        position: absolute;\n        top: 5px;\n        left: 50%;\n        margin-left: -180px;\n        z-index: 5;\n        background-color: #fff;\n        padding: 5px;\n        border: 1px solid #999;\n      }\n    </style>\n    <script src=\"https://maps.googleapis.com/maps/api/js?v=3.exp&sensor=false\"></script>\n    <script>\n\tvar directionsDisplay;\n\tvar directionsService = new google.maps.DirectionsService();\n\tvar map;\n\n\tvar start_point = \'"
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
	list_of_elements[12]="\n\t  directionsDisplay.setMap(map);\n\t}\n\n\tfunction calcRoute() {\n\t\tvar request = {\n\t\t  origin:start_point,\n\t\t  destination:end_point,\n\t\t  travelMode: google.maps.TravelMode.DRIVING\n\t\t};\n\t\t\n\t\tdirectionsService.route(request, function(response, status) {\n\t\t\tif (status == google.maps.DirectionsStatus.OK) {\n\t\t\t  directionsDisplay.setDirections(response);\n\t\t\t}\n\t\t});\n\t}\n\n\tcalcRoute()\n\tgoogle.maps.event.addDomListener(window, \'load\', initialize);\n    </script>\n  </head>\n  <body>\n    <div id=\"map-canvas\"/>\n  </body>\n</html>"

	for each in list_of_elements:
		file.write(each)
	
	file.close()


def convert_to_yelp_app_link(website_link):
	"""Takes a Yelp mobile website link and converts it to open in the iPhone app"""
	unique_id=website_link[17:]
	yelp_link_start='yelp://'
	return yelp_link_start+unique_id

""" For running Flask locally"""
if __name__ == '__main__':
    app.run(debug=True)
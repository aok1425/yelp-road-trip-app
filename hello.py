import os
from flask import Flask, request, url_for, render_template, redirect, flash

app = Flask(__name__)

logging_input_data=[]
resto_table={}
filtered_table={}

@app.route('/')
def show_input_form():
	#return app.root_path+"\\static\\map.html"
    return render_template('input_form.html')

@app.route('/test')
def show_path():
	return app.root_path+"/static/map.html"
	
@app.route('/add', methods=['POST'])
def add_entry():
	start=request.form['start']
	end=request.form['end']
	time_leaving=request.form['time_leaving']
	eating_time=request.form['eating_time']
	logging_input_data.append([start,end,time_leaving,eating_time])
	print start,end,time_leaving,eating_time
	#do_everything(start,end,1,1,time_leaving,eating_time,10,40,20,20)
	do_everything('reno,nv','jackpot,nv',1,1,'3:00pm','7:30pm',10,40,20,20)
	#make_HTML_file(start,end,filtered_table)
	make_HTML_file('reno,nv','jackpot,nv',filtered_table)
	
	#return 'You want to start at '+start+', end at '+end+', leave at '+time_leaving+', and eat around '+eating_time+'.'
	return redirect(url_for('static', filename='map.html'))
	
# MY MASSIVE ASS SCRIPT
#####
# btwn time_to_restos(), time_to_restos_json(), and resto_table, I am betting that resto_table.keys() will always match up w/[sth out of the JSON?]. keys() is sometimes random though... 
# schema of resto_table is [address,rating,# reviews,yelp link,rating img,duration to resto,distance to resto,minutes out of way,distance out of way]
 
# if time_block using Bing Maps points < cull_block, cull_search_points() won't filter out any too-long steps
 
# Google Distance Matrix API has limit of 100 elements/query
 
#len(yelp_json_to_table(yelp_search(20,radius=40000,location='fernley,nv')))
#do_everything('reno,nv','jackpot,nv',7,5,'3:00pm','3:30pm')
 
import oauth2, requests, datetime, pandas as pd
from numpy import cumsum

key='AIzaSyBsbGsLbD2hM5jr1bewKc6hotr3iV1lpmw'
bingkey='Aigw5zUPIFl1h-DVWxs3co1hFyupx-K1oWe8ss2SRpdTfQJKGzILySBUdQ0GBFH3'

def get_gmaps_json(start,end,sensor='false'):
	"""Input start and end locations, and it returns JSON from GMaps."""
	payload = {'origin':start, 'destination':end,'sensor':sensor,'key': key}
	site='https://maps.googleapis.com/maps/api/directions/json'
	r = requests.get(site, params=payload)
	return r.json()

def break_up_step(start,end,time_block=30):
	"""Using rows w/format [cumm duration, duration, latlong], input start and end rows for this long stretch. Returns a table of multiple rows w/their own cumm duration, duration, and latlong values using Bing (instead of guessing midpoints as the crow flies)."""
	start_point=','.join([str(item) for item in start[2]])
	end_point=','.join([str(item) for item in end[2]])
	
	payload = {'wp.0':start_point, 'wp.1':end_point,'rpo':'Points','key': bingkey}
	site='http://dev.virtualearth.net/REST/V1/Routes/Driving'
	r = requests.get(site, params=payload)
	thejson=r.json()
	coordinates=thejson['resourceSets'][0]['resources'][0]['routePath']['line']['coordinates']
	
	# filtering the list of coordinate points by every 30 minute duration, assuming constant speed
	time_blocks=time_block*60 # 30 mins * 60s
	segments=end[1]/time_blocks # always rounds down; i can make this err on the side of pulling 1 more search point instead
	skip_amt=len(coordinates)/segments
	duration=end[1]/float(segments) # shld be very similar to time_blocks
	
	# I'm taking the time duration of the trip, and dividing that by every 30 min duration to get the number of segments.
	# But, I take the number of segments and use that to filter the latlong points.
	# If the latlong points are given to me by Bing for every x mins that pass, everything is golden.
	# If they are given to me by every y distance, then I'm using the duration scale on the distance scale, even though they are two different scales, since speed will not be constant.
	# Only if speed is constant would the two scales translate cleanly into each other.
	# I'm going to take the time scale, and 'translate' it to the distance scale. Funny. Like the Kahneman book.
	
	filtered_coordinates=coordinates[::skip_amt]
	
	# adding cumm durations and duration to latlong points
	search_points=[]
	for number in range(segments): # always rounds down; can chg this if i want
		new_search_point=[start[0]+duration*(number+1),duration,filtered_coordinates[number]]
		search_points.append(new_search_point)
	
	last_coordinate_index=len(coordinates)-1
	#print start[0]+duration*(segments+1),duration,coordinates[last_coordinate_index]
	search_points.append([start[0]+duration*(segments+1),duration,coordinates[last_coordinate_index]]) # appends final search point as well
	
	#for row in search_points: print row
	return search_points

def make_search_points(thejson,time_block=30,too_long_step=60):
	"""Take JSON file of GMaps directions and returns a table of cumulative durations, durations, and locations."""
	steps=thejson['routes'][0]['legs'][0]['steps']
	durations,locs=[],[]
	some_distance=too_long_step*60 # if a step lasts 60 minutes, it will be broken up into 30 minute sub-steps where Yelp will search from
	# some_distance needs to be at least 2x of time_blocks. otherwise, there will only be 1 segment
	# and the whole point is to break up a long segment into multiple sub-segments!
	#print 'time_Block is',time_block
	#print 'too_long_step is',too_long_step
	for each in steps:
		duration=each['duration']['value']
		durations.append(duration)
		latlongdict=each['end_location']
		locs.append([latlongdict['lat'],latlongdict['lng']])

	cummdurations = cumsum(durations)
	""" This is the table before long pieces are broken up.
	testtable=[]
	for i in range(len(durations)):
		testtable.append([cummdurations[i],durations[i],locs[i]])
	for row in testtable:
		print row"""
	
	table=[]
	for i in range(len(durations)):
		if durations[i] > some_distance:
			to_insert=break_up_step([cummdurations[i-1],durations[i-1],locs[i-1]],[cummdurations[i],durations[i],locs[i]],time_block)
			for row in to_insert:
				table.append(row)
		else:
			table.append([cummdurations[i],durations[i],locs[i]])

	#print 'from make_search_points()'
	#for row in table: print row
	
	return table

# because only the search points that are AFTER 30 mins has passed will show up, if i'm at 28 mins, and the next step is 29 mins, then i'll only get a point at 28+29 mins
def cull_search_points(search_points,cull_block=30):
	"""Takes table of search points and returns only those steps that occur after 30 min driving."""
	cumm_durations=[row[0]/float(cull_block*60) for row in search_points] # isolate the first column; 60 for 60s
	subset_search_points=[]
	redundant_cumm_durations=[]
	
	#print 'Before the cull'
	#for row in search_points: print row
	
	#for row in cumm_durations: print int(row)
	
	for i in range(len(search_points)):
		if str(int(cumm_durations[i])) not in [str(int(each)) for each in redundant_cumm_durations]: # maybe just int(12.123) might work.
			redundant_cumm_durations.append(cumm_durations[i])
			subset_search_points.append(search_points[i])
			
	subset_search_points.append(search_points[len(search_points)-1]) # appends final destination as well
	
	#print 'After the cull'
	#for row in subset_search_points: print row
	
	return subset_search_points
	
def time_diff(start_time,eating_time_start):
	"""Take input and add it to start_time. Return desired start eating time as # of seconds past start time."""
	eating_time_start=datetime.datetime.strptime(eating_time_start, '%I:%M%p')
	start_time=datetime.datetime.strptime(start_time, '%I:%M%p')
	
	diff=eating_time_start-start_time
	seconds_diff=diff.seconds
	
	return seconds_diff
	
def filter_search_points_by_eating_time(search_points,eating_time_start):
	"""Takes search table and returns only those rows after eating_time start until eating_time_end, set at 1.5 hours here."""
	eating_time_end=eating_time_start+1.5*60*60 # 1.5 hour duration
	filtered_search_points=[]
	
	for i in range(len(search_points)):
		cumm_duration=search_points[i][0]
		
		if eating_time_start<=cumm_duration<=eating_time_end:
			filtered_search_points.append(search_points[i])
			
	return filtered_search_points	

# I will want to chg this later to give me the most popular restaurants that have a minimum number of stars, maybe w/weights instead of absolute filters. Maybe something Bayesian!?!?!?! whatever that may mean lol.

def yelp_search(limit,radius,latlong=None,location=None,sort_method=0): # either input latlong or location
	"""Takes in certain parameters, and outputs the Yelp Search JSON file.
	Radius is in meters; max is 40000.
	Max limit is 20.
	Limit and radius are integers."""
	# If I can figure out a way to get the URL w/the params w/o making a GET request, that wld be great!
	# The way I'm doing it is kinda ghetto.
	payload = {'limit':limit,'radius_filter':radius,'category_filter': 'restaurants','sort':sort_method}
	if latlong:
		payload['ll'] = latlong
	else:
		payload['location']=location
	
	consumer_key = 'p0z-o-8cwOH7c5h4GO8vhg'
	consumer_secret = 'qwPaxGEydLqHlNTYTAls-AGwy28'
	token = 'VPHPmXFuhRDtEYWPL56pAPgPFOdc1Gk0'
	token_secret = 'SChhpSGhdwKgGGoqjQ-vplr-0C4'
	
	# Make initial URL w/params
	url = 'http://api.yelp.com/v2/search'
	r = requests.get(url, params=payload)
	#print 'URL: %s' % (r.url,)
	
	# Sign the URL
	consumer = oauth2.Consumer(consumer_key, consumer_secret)
	
	oauth_request = oauth2.Request('GET', r.url, {})
	oauth_request.update({'oauth_nonce': oauth2.generate_nonce(),
						  'oauth_timestamp': oauth2.generate_timestamp(),
						  'oauth_token': token,
						  'oauth_consumer_key': consumer_key})
	token = oauth2.Token(token, token_secret)
	oauth_request.sign_request(oauth2.SignatureMethod_HMAC_SHA1(), consumer, token)
	signed_url = oauth_request.to_url()
	#print 'Signed URL: %s' % (signed_url,)
	
	s=requests.get(signed_url)

	return s.json()
	
def yelp_json_to_table(thejson):
	"""Takes JSON from Yelp Search API and adds restos' name, address, and rating to the dict resto_table."""
	new_table=[]
	for category in thejson['businesses']:
		address=', '.join([category['location']['address'][0],category['location']['postal_code']])
		new_table.append([category['name'],address,category['rating'],category['review_count'],category['url'],category['rating_img_url']])
	return new_table

def yelp_table_to_dict(table,cutoff=3):
	"""Takes in a table, sorts the rows by the review count. Takes this table, and puts the first n restos into resto_table.
	Puts the cutoff-number of most reviewed restos into resto_table."""
	sorted_table=sorted(table, key=lambda row: row[1],reverse=True)

	for row in sorted_table[:cutoff]:
		resto_table[row[0]]=row[1:]
	
def turn_latlong_list_to_string(item):
	"""In order to pass to yelp_search(). Dict search_points currently has them a a string."""
	return str(item[0])+','+str(item[1])
	
def extra_distance_json(start, end, resto, sensor='false'):
	"""Returns JSON response for extra distance to resto address."""
	key='AIzaSyBsbGsLbD2hM5jr1bewKc6hotr3iV1lpmw'
	
	payload = {'origins':start+'|'+resto, 'destinations':end+'|'+resto, 'key':key, 'units':'imperial', 'sensor':sensor}
	url = 'https://maps.googleapis.com/maps/api/distancematrix/json'
	
	r = requests.get(url, params=payload)
	#print 'URL: %s' % (r.url,)
	return r.json()

def extra_distance_to_resto(thejson):
	"""Takes in a JSON from Google Distance Matrix API and returns the diff to go to resto, in time and distance."""
	durations,distances=[],[]

	for row in thejson['rows']:
		for element in row['elements']:
			try:
				distances.append(element['distance']['value']) # in seconds
				durations.append(element['duration']['value']) # in meters
			except KeyError:
				print '\nGMaps can\'t understand an address. Program will crash here...'
				print 'what is',row
				print 'what is',element
			
	route_w_resto=[durations[1]+durations[2],distances[1]+distances[2]] # time, then distance
	original_route=[durations[0],distances[0]]
	diff=[route_w_resto[0]-original_route[0],route_w_resto[1]-original_route[1]]

	#print 'shorter route is',original_route[1]*0.000621371,'miles long and',"%0.2f" % (float(original_route[0])/3600),'hours to drive.'
	#print 'longer route is',route_w_resto[1]*0.000621371,'miles long and',"%0.2f" % (float(route_w_resto[0])/3600),'hours to drive.'
	#print 'It takes an extra',"%0.2f" % (float(diff[0])/60),'minutes and',diff[1]*0.000621371,'miles to get to the restaurant.'
	return diff
	
def time_to_restos_json(start,filtered_table,sensor='false'):
	"""Input starting location, table of end locations, and get JSON back from Google Directions Matrix.
	
	I'm inputting a table instead of each destination address so that I can make fewer calls to the API."""
	addresses=[]
	for restaurant in filtered_table.keys():
		addresses.append(filtered_table[restaurant][0])
	end='|'.join(addresses)
	
	key='AIzaSyBsbGsLbD2hM5jr1bewKc6hotr3iV1lpmw'
	payload = {'origins':start, 'destinations':end, 'key':key, 'units':'imperial', 'sensor':sensor}
	url = 'https://maps.googleapis.com/maps/api/distancematrix/json'
	r = requests.get(url, params=payload)
	#print 'URL: %s' % (r.url,)
	
	return r.json()
	
def time_to_restos(thejson,start,start_time):
	try: # I hope hope hope this isn't too hacky!!!
		dict_of_durations=thejson['rows'][0]['elements']
		
		start_time_repr=datetime.datetime.strptime(start_time, '%I:%M%p')

		info_table=[]
		
		for i in range(len(filtered_table)):
			duration=dict_of_durations[i]['duration']['value']
			distance=dict_of_durations[i]['distance']['value']
			name=filtered_table.keys()[i]
			
			preaddress=thejson['destination_addresses'][i]
			address=pull_town_from_address(preaddress)
			time_delta=datetime.timedelta(seconds=duration)
			end_time=datetime.datetime.strftime(start_time_repr+time_delta,'%I:%M%p')
			print 'Since you started at',start_time,'you will arrive at',name,'at',end_time,'. It\'s in',address,'.'
			minutes_away=duration
			
			info_table.append([name,preaddress,minutes_away,distance])
			
		return info_table
	
	except IndexError:
		print 'There are no restaurants available in that time frame!'

def pull_town_from_address(address):
	split_address=address.split(', ')
	return ', '.join(split_address[1:3])

def filter_resto_table(resto_table,review_cutoff=15):
	"""Takes resto_table, and filters it. Now, I have it filtering by # of reviews only. Adds the result to the dict filtered_table"""
	columns=['address','rating','rs','img link','yelp link']
	df=pd.DataFrame(resto_table).T
	df.columns=columns
	#df=df.drop(['address','img link','yelp link'],axis=1)
	df=df.sort(['rs'],ascending=False)

	temp_filtered_resto_table=df.head(review_cutoff).T.to_dict('list') # makes new resto_table taking the review_cutoff most reviewed restos
	
	for row in temp_filtered_resto_table:
		filtered_table[row]=temp_filtered_resto_table[row]
	
def do_everything(start,end,search_limit,return_limit,start_time,eating_time_start,review_cutoff=15,too_long_step=60,time_block=30,cull_block=30,radius=40000,sensor='false'):
	"""Input START and END location, and program will search Yelp after every step within RADIUS, return LIMIT # of restos, then tell you the time to drive to each of them from starting location.
	
	Search_limit is how many restos Yelp searches for at each search point. Max of search_limit is 20. Return_limit is how many restos I cut off to find the most reviewed ones.
	
	Review_cutoff is how many restos do you want to return after sorting them my # of reviews.
	
	Around what time do you want to start eating? Program will look 1.5 hours after that in terms of places to look, not time to final destinations."""
	result=get_gmaps_json(start,end)
	
	start_time_repr=datetime.datetime.strptime(start_time, '%I:%M%p')
	drive_duration=result['routes'][0]['legs'][0]['duration']['value'] # in seconds
	print 'You will arrive at',end,'at',datetime.datetime.strftime(start_time_repr+datetime.timedelta(seconds=drive_duration),'%I:%M%p')
	
	search_points=make_search_points(result,time_block,too_long_step)
	search_points_to_return=cull_search_points(search_points,cull_block)
	search_points=filter_search_points_by_eating_time(search_points_to_return,time_diff(start_time,eating_time_start))
	
	for row in range(len(search_points)):
		yelp_table_to_dict(yelp_json_to_table(yelp_search(search_limit,radius,latlong=turn_latlong_list_to_string(search_points[row][2]))),return_limit)
	
	filter_resto_table(resto_table, review_cutoff)
	
	# adds extra time and distance to each of the filtered restos
	for each in range(len(filtered_table)):
		address=filtered_table[filtered_table.keys()[each]][0] # 0 is for address; 1 for rating
		name=filtered_table.keys()[each]
		result=extra_distance_to_resto(extra_distance_json(start,end,address))
		print 'It takes an extra',"%0.1f" % int(float(result[0])/60),'minutes and',"%0.1f" % (result[1]*0.000621371),'miles to get to',name,'.'
		if name in filtered_table.keys():
			filtered_table[name].append(result[0])
			filtered_table[name].append(result[1])
	
	# adds time and distance to each of the filtered restos
	table2=time_to_restos(time_to_restos_json(start,filtered_table),start,start_time) # can change this to duration/distance from any location
	for row in table2:
		print row
		try:
			filtered_table[row[0]].append(row[2])
			filtered_table[row[0]].append(row[3])
		except:
			print 'skipping',row[0]
			pass
	
	return table2
	#return search_points_to_return # can chg this to return previous search_points; input that into 'plot bing points on map.py'
		
def make_HTML_file(start_point,end_point,resto_table):
	"""Resto_addresses is a table of just addresses."""
	# I'm assumong here that w/the dixt, the order will always be the same, so I can make mltuple lists out of it.
	#file=open('c:/users/alex/desktop/flask/static/map.html','w')
	#file=open('/static/map.html','w')
	#file=open(os.path.join(app.root_path,"\\static\\map.html"),'w')
	file=open(app.root_path+"/static/map.html",'w')
	key='AIzaSyBsbGsLbD2hM5jr1bewKc6hotr3iV1lpmw'
	locations=[] # many locations to put on map
	infowindows=[]

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
	  
	def add_infowindow(resto,number):
		resto_data=resto_table[resto]

		infowindow=range(19)
		infowindow[0]="var contentString"
		infowindow[1]=str(number)
		infowindow[2]="= \n\'<h2 id=\"firstHeading\" class=\"firstHeading\">"
		infowindow[3]=fix_quotes(resto)
		infowindow[4]="</h2>\'+\n\'<img src=\""
		infowindow[5]=str(resto_data[4])
		infowindow[6]="\" alt=\"Yelp rating image\">\'+\n\'<p>"
		infowindow[7]=str(resto_data[2])
		infowindow[8]=" reviews</p>\'+\n\'<p>"
		infowindow[9]=str("%0.1f" % (resto_data[6]*0.000621371))
		infowindow[10]=" mi/"
		infowindow[11]=str("%0.1f" % int(float(resto_data[5])/60)) # converting to minutes
		infowindow[12]=" mins away</p>\'+\n\'<p>"
		infowindow[13]=str("%0.1f" % (resto_data[8]*0.000621371))
		infowindow[14]=" mi/"
		infowindow[15]=str("%0.1f" % int(float(resto_data[7])/60)) # converting to minutes
		infowindow[16]=" min detour</p>\'+\n\'<a href=\""
		infowindow[17]=str(resto_data[3])
		infowindow[18]="\" target=\"\_blank\">visit Yelp page</a>\'"
		return ''.join(infowindow)

	number=0
	for resto in resto_table:
		number+=1
		infowindows.append(add_infowindow(resto,number))
		
	### Part 1: Take resto addresses and add their coordinates to a JS list called locations on the HTML file.
	
	def geocode_address(address,sensor='false'):
		"""Input address and return lat long dictionary."""
		payload = {'address':address,'sensor':sensor,'key': key}
		site='https://maps.googleapis.com/maps/api/geocode/json'
		r = requests.get(site, params=payload)
		return r.json()
		
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

	number=0
	for resto in resto_table: 
		number+=1
		resto_data=resto_table[resto]
		locations.append(add_location(show_coordinates(geocode_address(resto_data[0])),number)) # 0 being the address

			
	### Part 2: Take all the elements of the HTML file and write them.	
		
	list_of_elements=range(9)

	list_of_elements[0]="<!DOCTYPE html>\n<html>\n  <head>\n    <meta name=\"viewport\" content=\"initial-scale=1.0, user-scalable=no\">\n    <meta charset=\"utf-8\">\n    <title>Directions service</title>\n    <style>\n      html, body, #map-canvas {\n        height: 100%;\n        margin: 0px;\n        padding: 0px\n      }\n      #panel {\n        position: absolute;\n        top: 5px;\n        left: 50%;\n        margin-left: -180px;\n        z-index: 5;\n        background-color: #fff;\n        padding: 5px;\n        border: 1px solid #999;\n      }\n    </style>\n    <script src=\"https://maps.googleapis.com/maps/api/js?v=3.exp&sensor=false\"></script>\n    <script>\n\tvar directionsDisplay;\n\tvar directionsService = new google.maps.DirectionsService();\n\tvar map;\n\n\tvar start_point = \'"
	list_of_elements[1]=start_point #'2312,31321'
	list_of_elements[2]="';\n\tvar end_point = '"
	list_of_elements[3]=end_point #'2312,31321'
	list_of_elements[4]="\';\n\n\tfunction initialize() {\n\t\tvar mapOptions = {\n\t\t  center: new google.maps.LatLng(-33.92, 151.25),\n\t\t  zoom: 2\n\t\t};\n\t\t\n\t"
	list_of_elements[5]='\n\n'.join(infowindows)
	list_of_elements[6]="\n\n\tvar map = new google.maps.Map(document.getElementById(\"map-canvas\"),mapOptions);\n\n    var locations = [\n\t"
	list_of_elements[7]='\n\t'.join(locations)
	list_of_elements[8]="\n    ];\n\n    var infowindow = new google.maps.InfoWindow();\n\n    var marker, i;\n\n    for (i = 0; i < locations.length; i++) {  \n      marker = new google.maps.Marker({\n        position: new google.maps.LatLng(locations[i][1], locations[i][2]),\n        map: map\n      });\n\n      google.maps.event.addListener(marker, \'click\', (function(marker, i) {\n        return function() {\n          infowindow.setContent(locations[i][0]);\n          infowindow.open(map, marker);\n        }\n      })(marker, i));\n\t  \n\t  google.maps.event.addListener(map, \'click\', function() {\n\t\tinfowindow.close(map,marker);\n\t});\n    }\n\n\tdirectionsDisplay = new google.maps.DirectionsRenderer();\n\t  directionsDisplay.setMap(map);\n\t}\n\n\tfunction calcRoute() {\n\t\tvar request = {\n\t\t  origin:start_point,\n\t\t  destination:end_point,\n\t\t  travelMode: google.maps.TravelMode.DRIVING\n\t\t};\n\t\t\n\t\tdirectionsService.route(request, function(response, status) {\n\t\t\tif (status == google.maps.DirectionsStatus.OK) {\n\t\t\t  directionsDisplay.setDirections(response);\n\t\t\t}\n\t\t});\n\t}\n\n\tcalcRoute()\n\tgoogle.maps.event.addDomListener(window, \'load\', initialize);\n    </script>\n  </head>\n  <body>\n    <div id=\"map-canvas\"/>\n  </body>\n</html>"

	for each in list_of_elements:
		file.write(each)
	file.close()
	

"""
if __name__=='__main__':
	start=raw_input('Where will you start your day?\n')
	end=raw_input('What is your destination?\n')
	start_time=raw_input('What time are you starting?\n')
	eating_time=raw_input('What time do you want to eat?\n')
	do_everything(start,end,5,3,start_time,eating_time)
	make_HTML_file(start,end,resto_table)
"""
#do_everything('reno,nv','jackpot,nv',7,5,'3:00pm','3:30pm',10,40,20,20)
#make_HTML_file('reno,nv','jackpot,nv',filtered_table)


	
#####
""" For running Flask locally
if __name__ == '__main__':
    app.run(debug=True)"""
import os, codecs, datetime
from flask import Flask, request, url_for, render_template, redirect, flash

app = Flask(__name__)

resto_table={}
filtered_table={}

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
    return redirect(url_for('static', filename='search_points.htm'))

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
	
	reset_tables()
	
	if request.form['button']=='Just find the best! (takes longer)':
		print 'I\'m feeling lucky option chosen.'
		with codecs.open(app.root_path+"/static/log.txt",'a','utf-8') as f:
			f.write('"'+'","'.join([str(datetime.datetime.now()),start,end,'I\'m feeling lucky','I\'m feeling lucky'])+'"'+'\n')
		do_everything(start,end,20,20,'12:00','15:00',9,60,30,30,just_best=True) # GMaps Dist Matrix API can only handle 9
		make_HTML_file(start,end,'12:00',filtered_table,just_best=True)
	else:
		print 'Regular option chosen.'
		destination_time=check_time(start,end,time_leaving,eating_time)
		#change_loading_screen(end,destination_time) # not used bc loading page doesn't update like that
		print 'Checking the times...'
		if destination_time=='yes':
			with codecs.open(app.root_path+"/static/log.txt",'a','utf-8') as f:
				f.write('"'+'","'.join([str(datetime.datetime.now()),start,end,time_leaving,eating_time])+'"'+'\n')
			do_everything(start,end,20,20,time_leaving,eating_time,9,40,20,20) # GMaps Dist Matrix API can only handle 9
		else:
			print 'Bc eating time is too late, I will replace that w/destination time.'
			destination_time_repr=datetime.datetime.strptime(destination_time, '%I:%M%p')
			final_time_repr=destination_time_repr-datetime.timedelta(minutes=45) # choose a point 30 mins before final destination
			final_time=datetime.datetime.strftime(final_time_repr,'%H:%M')	
			with codecs.open(app.root_path+"/static/log.txt",'a','utf-8') as f:
				f.write('"'+'","'.join([str(datetime.datetime.now()),start,end,time_leaving,eating_time,destination_time,'eating time is after destination time'])+'"'+'\n')
			print 'time I will input is',final_time
			do_everything(start,end,20,20,time_leaving,final_time,9,40,20,20) # GMaps Dist Matrix API can only handle 9
		make_HTML_file(start,end,time_leaving,filtered_table)

	return redirect(url_for('static', filename='map.html'))

##### MY MASSIVE ASS SCRIPT
# btwn time_to_restos(), time_to_restos_json(), and resto_table, I am betting that resto_table.keys() will always match up w/[sth out of the JSON?]. keys() is sometimes random though...
# also assuming this to add the distance/duration/extra distance/extra duration to the dict filtered_table

# schema of resto_table is [address,rating,# reviews,yelp link,rating img,duration to resto,distance to resto,minutes out of way,distance out of way]

# if time_block using Bing Maps points < cull_block, cull_search_points() won't filter out any too-long steps
# Google Distance Matrix API has limit of 100 elements/query

import oauth2, requests, pandas as pd, codecs, datetime
from numpy import cumsum, average

key='AIzaSyBsbGsLbD2hM5jr1bewKc6hotr3iV1lpmw'
bingkey='Aigw5zUPIFl1h-DVWxs3co1hFyupx-K1oWe8ss2SRpdTfQJKGzILySBUdQ0GBFH3'
# for yelp


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
	eating_time_start=datetime.datetime.strptime(eating_time_start, '%H:%M')
	start_time=datetime.datetime.strptime(start_time, '%H:%M')

	diff=eating_time_start-start_time
	seconds_diff=diff.seconds

	return seconds_diff

def filter_search_points_by_eating_time(search_points,eating_time_start,duration=0.75,time_back=0.25):
	"""Takes search table and returns only those rows after eating_time-time_back until eating_time_end, set at 1 hour here."""
	eating_time_end=eating_time_start+duration*60*60 # 1 hour duration
	eating_time_start=eating_time_start-time_back*60*60 # does yelp search at points up to a 1/4 hr before my eating time
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

	# Make initial URL w/params
	url = 'http://api.yelp.com/v2/search'
	r = requests.get(url, params=payload)
	#print 'URL: %s' % (r.url,)

	consumer_key = 'p0z-o-8cwOH7c5h4GO8vhg'
	consumer_secret = 'qwPaxGEydLqHlNTYTAls-AGwy28'
	token = 'VPHPmXFuhRDtEYWPL56pAPgPFOdc1Gk0'
	token_secret = 'SChhpSGhdwKgGGoqjQ-vplr-0C4'
	
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
		try: # because of Ragtime in Elko, NV, which has no address on Yelp!
			addresses=[]
			for each_address in category['location']['address']:
				addresses.append(each_address)
			addresses.append(category['location']['postal_code'])
			address=', '.join(addresses)
		except:
			address='3 Oyster Bay Rd, 02125'
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

def time_and_distance_json(start, end, filtered_table, sensor='false'):
	"""Returns JSON response for extra distance to resto address.
	GMaps Directions Matrix API accepts a max of 9 restos, making 11 elements including start and end."""
	key='AIzaSyBsbGsLbD2hM5jr1bewKc6hotr3iV1lpmw'
	
	list_of_addresses=[filtered_table[name][0] for name in filtered_table.keys()]
	origins=[start]
	destinations=[end]
	[origins.append(address+',USA') for address in list_of_addresses]
	[destinations.append(address+',USA') for address in list_of_addresses]	
	
	payload = {'origins':'|'.join(origins), 'destinations':'|'.join(destinations), 'key':key, 'units':'imperial', 'sensor':sensor}
	url = 'https://maps.googleapis.com/maps/api/distancematrix/json'

	r = requests.get(url, params=payload)
	#print 'URL: %s' % (r.url,)
	#print len(filtered_table),'restos, ',len(filtered_table)+2,' elements.'
	#return r.url
	return r.json()

def time_and_distance_to_resto(thejson):
	"""Takes in a JSON from Google Distance Matrix API and returns the diff to go to resto, in time and distance."""
	durations,distances=[],[]
	num_elements=len(thejson['rows'])
	
	for row in thejson['rows']:
		for element in row['elements']:
			try:
				distances.append(element['distance']['value']) # in seconds
				durations.append(element['duration']['value']) # in meters
			except KeyError:
				print 'GMaps can\'t understand an address. Program will crash here...'
				#print 'what is',row
				#print 'what is',element
	
	original_route_list_duration=durations[1:num_elements]
	original_route_list_distance=distances[1:num_elements]
	
	first_element_duration=original_route_list_duration
	second_element_duration=[durations[len(durations)-n*num_elements] for n in range(1,num_elements)][::-1]
	diff_list_duration=[first_element_duration[i]+second_element_duration[i]-durations[0] for i in range(len(first_element_duration))]
	
	first_element_distance=original_route_list_distance
	second_element_distance=[distances[len(distances)-n*num_elements] for n in range(1,num_elements)][::-1]
	diff_list_distance=[first_element_distance[i]+second_element_distance[i]-distances[0] for i in range(len(first_element_distance))]

	return diff_list_duration,diff_list_distance,original_route_list_duration,original_route_list_distance

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

def do_everything(start,end,search_limit,return_limit,start_time,eating_time_start,review_cutoff=9,too_long_step=40,time_block=20,cull_block=20,just_best=False,radius=40000,sensor='false'):
	"""Input START and END location, and program will search Yelp after every step within RADIUS, return LIMIT # of restos, then tell you the time to drive to each of them from starting location.

	Search_limit is how many restos Yelp searches for at each search point. Max of search_limit is 20. Return_limit is how many restos I cut off to find the most reviewed ones.

	Review_cutoff is how many restos do you want to return after sorting them my # of reviews.

	Around what time do you want to start eating? Program will look 1.5 hours after that in terms of places to look, not time to final destinations."""
	print 'Pulling results from Google Directions'
	result=get_gmaps_json(start,end)

	#start_time_repr=datetime.datetime.strptime(start_time, '%H:%M')
	drive_duration=result['routes'][0]['legs'][0]['duration']['value'] # in seconds
	#print 'You will arrive at',end,'at',datetime.datetime.strftime(start_time_repr+datetime.timedelta(seconds=drive_duration),'%I:%M%p')

	print 'Making search points'
	search_points=make_search_points(result,time_block,too_long_step)
	print 'culling them'
	search_points=cull_search_points(search_points,cull_block)
	if just_best==False:
		search_points=filter_search_points_by_eating_time(search_points,time_diff(start_time,eating_time_start))
	else:
		search_points=search_points[1:len(search_points)-2] # takes away first and last points. finds best restos along the way

	len_search_points=len(search_points)
	counter=0
	for row in range(len_search_points):
		counter+=1
		print 'Searching on Yelp point',counter,'out of',len_search_points
		yelp_table_to_dict(yelp_json_to_table(yelp_search(search_limit,radius,latlong=turn_latlong_list_to_string(search_points[row][2]),sort_method=2)),return_limit)

	filter_resto_table(resto_table, review_cutoff)
	
	print 'Finding distance and driving durations for',len(filtered_table),'restos...'
	# adds extra time and distance to each of the filtered restos
	
	thejson=time_and_distance_json(start,end,filtered_table)
	result=time_and_distance_to_resto(thejson)
			
	for i in range(len(filtered_table.keys())):
		for j in result:
			filtered_table[filtered_table.keys()[i]].append(j[i])
			
	print 'done'
	#return search_points_to_return # can chg this to return previous search_points; input that into 'plot bing points on map.py'

def convert_to_yelp_app_link(website_link):
	"""Takes a Yelp mobile website link and converts it to open in the iPhone app"""
	unique_id=website_link[17:]
	yelp_link_start='yelp://'
	return yelp_link_start+unique_id
	
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
		"""Input address and return lat long dictionary."""
		payload = {'address':address+', USA','sensor':sensor,'key': key}
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
	len_resto_table=len(resto_table)
	for resto in resto_table:
		number+=1
		print 'Geocoding address',number,'out of',len_resto_table
		resto_data=resto_table[resto]
		coordinate=show_coordinates(geocode_address(resto_data[0]))
		coordinates.append(coordinate)
		locations.append(add_location(coordinate,number)) # 0 being the address

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

def reset_tables():
	globals()['resto_table']={}
	globals()['filtered_table']={}


#do_everything('canton,oh','columbus,oh',20,20,'12:00','13:00',9,40,20,20)
#make_HTML_file('reno,nv','jackpot,nv','3:00',filtered_table)



#####

""" For running Flask locally"""
if __name__ == '__main__':
    app.run(debug=False)
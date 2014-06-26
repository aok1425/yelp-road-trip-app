##### MY MASSIVE ASS SCRIPT
# btwn time_to_restos(), time_to_restos_json(), and self.resto_table, I am betting that self.resto_table.keys() will always match up w/[sth out of the JSON?]. keys() is sometimes random though...
# also assuming this to add the distance/duration/extra distance/extra duration to the dict filtered_table

# schema of self.resto_table is [address,rating,# reviews,yelp link,rating img,duration to resto,distance to resto,minutes out of way,distance out of way]

# if time_block using Bing Maps points < cull_block, cull_search_points() won't filter out any too-long steps
# Google Distance Matrix API has limit of 100 elements/query

import oauth2, requests, pandas as pd, codecs, datetime, grequests, sensitive_info
from numpy import cumsum, average

key = sensitive_info.key
bingkey = sensitive_info.bingkey

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
	search_points.append([start[0]+duration*(segments+1),duration,coordinates[last_coordinate_index]]) # appends final search point as well

	return search_points

def make_search_points(thejson,time_block=30,too_long_step=60):
	"""Take JSON file of GMaps directions and returns a table of cumulative durations, durations, and locations."""
	steps=thejson['routes'][0]['legs'][0]['steps']
	durations,locs=[],[]
	some_distance=too_long_step*60 # if a step lasts 60 minutes, it will be broken up into 30 minute sub-steps where Yelp will search from
	# some_distance needs to be at least 2x of time_blocks. otherwise, there will only be 1 segment
	# and the whole point is to break up a long segment into multiple sub-segments!

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

	return table

# because only the search points that are AFTER 30 mins has passed will show up, if i'm at 28 mins, and the next step is 29 mins, then i'll only get a point at 28+29 mins
def cull_search_points(search_points,cull_block=30):
	"""Takes table of search points and returns only those steps that occur after 30 min driving."""
	cumm_durations=[row[0]/float(cull_block*60) for row in search_points] # isolate the first column; 60 for 60s
	subset_search_points=[]
	redundant_cumm_durations=[]

	for i in range(len(search_points)):
		if str(int(cumm_durations[i])) not in [str(int(each)) for each in redundant_cumm_durations]: # maybe just int(12.123) might work.
			redundant_cumm_durations.append(cumm_durations[i])
			subset_search_points.append(search_points[i])

	subset_search_points.append(search_points[len(search_points)-1]) # appends final destination as well

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

	consumer_key = sensitive_info.consumer_key
	consumer_secret = sensitive_info.consumer_secret
	token = sensitive_info.token
	token_secret = sensitive_info.token_secret
	
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

	s=grequests.get(signed_url)

	return s

def yelp_json_to_table(thejson):
	"""Takes JSON from Yelp Search API and adds restos' name, address, and rating to the dict self.resto_table."""
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



class RestaurantFinder(object):
	"""Takes start and end points, and returns a dictionary of applicable restaurants."""
	def __init__(self,start,end,search_limit,return_limit,start_time,eating_time_start,review_cutoff=9,too_long_step=40,time_block=20,cull_block=20,just_best=False,radius=40000,sensor='false'):
		self.resto_table = {}
		self.filtered_table = {}
		self.main(start,end,search_limit,return_limit,start_time,eating_time_start,review_cutoff,too_long_step,time_block,cull_block,just_best,radius,sensor)

	def yelp_table_to_dict(self, table,cutoff=3):
		"""Takes in a table, sorts the rows by the review count. Takes this thisable, and puts the first n restos into self.resto_table.
		Puts the cutoff-number of most reviewed restos into self.resto_table."""
		sorted_table=sorted(table, key=lambda row: row[1],reverse=True)

		for row in sorted_table[:cutoff]:
			self.resto_table[row[0]]=row[1:]

	def filter_resto_table(self, resto_table,review_cutoff=15):
		"""Takes self.resto_table, and filters it. Now, I have it filtering by # of reviews only. Adds the result to the dict filtered_table"""
		columns=['address','rating','rs','img link','yelp link']
		df=pd.DataFrame(self.resto_table).T
		df.columns=columns
		df=df.sort(['rs'],ascending=False)

		self.temp_filtered_resto_table=df.head(review_cutoff).T.to_dict('list') # makes new self.resto_table taking the review_cutoff most reviewed restos

		for row in self.temp_filtered_resto_table:
			self.filtered_table[row]=self.temp_filtered_resto_table[row]

	def main(self,start,end,search_limit,return_limit,start_time,eating_time_start,review_cutoff=9,too_long_step=40,time_block=20,cull_block=20,just_best=False,radius=40000,sensor='false'):
		"""Input START and END location, and program will search Yelp after every step within RADIUS, return LIMIT # of restos, then tell you the time to drive to each of them from starting location.
		Search_limit is how many restos Yelp searches for at each search point. Max of search_limit is 20. Return_limit is how many restos I cut off to find the most reviewed ones.
		Review_cutoff is how many restos do you want to return after sorting them my # of reviews.
		Around what time do you want to start eating? Program will look 1.5 hours after that in terms of places to look, not time to final destinations."""
		
		print 'Pulling results from Google Directions'
		result=get_gmaps_json(start,end)

		drive_duration=result['routes'][0]['legs'][0]['duration']['value'] # in seconds

		print 'Making search points'
		search_points=make_search_points(result,time_block,too_long_step)
		print 'culling them'
		search_points=cull_search_points(search_points,cull_block)
		if just_best==False:
			search_points=filter_search_points_by_eating_time(search_points,time_diff(start_time,eating_time_start))
		else:
			search_points=search_points[3:len(search_points)-2] # takes away first and last points. finds best restos along the way

		len_search_points=len(search_points)
		yelp_rs = []
		
		for row in range(len_search_points):
			yelp_rs.append(yelp_search(search_limit,radius,latlong=turn_latlong_list_to_string(search_points[row][2]),sort_method=2))
		
		print 'Searching Yelp for all',len_search_points,'points at once...'
		responses = grequests.map(yelp_rs)
		thejsons = [response.json() for response in responses]

		for response in thejsons:
			self.yelp_table_to_dict(yelp_json_to_table(response),return_limit)
		
		print 'done'

		self.filter_resto_table(self.resto_table, review_cutoff)
		
		print 'Finding distance and driving durations for',len(self.filtered_table),'restos...'
		# adds extra time and distance to each of the filtered restos
		
		thejson=time_and_distance_json(start,end,self.filtered_table)
		result=time_and_distance_to_resto(thejson)
				
		for i in range(len(self.filtered_table.keys())):
			for j in result:
				self.filtered_table[self.filtered_table.keys()[i]].append(j[i])
				
		print 'done'
		#return search_points_to_return # can chg this to return previous search_points; input that into 'plot bing points on map.py'

#main('canton,oh','columbus,oh',20,20,'12:00','13:00',9,40,20,20)
#make_HTML_file('reno,nv','jackpot,nv','3:00',filtered_table)
import os
from flask import Flask, request, url_for, render_template, redirect, flash

app = Flask(__name__)

logging_input_data=[]
resto_table={}
filtered_table={}

@app.route('/')
def show_input_form():
    return render_template('input_form.html')

@app.route('/add', methods=['POST'])
def add_entry():
	start=request.form['start']
	end=request.form['end']
	time_leaving=request.form['time_leaving']
	eating_time=request.form['eating_time']
	logging_input_data.append([start,end,time_leaving,eating_time])

	#do_everything(start,end,7,5,time_leaving,eating_time,10,40,20,20)
	#make_HTML_file(start,end,filtered_table)
	
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
 
import oauth2, requests, datetime
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

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



import os
import codecs
import datetime
from flask import Flask, request, url_for, render_template, redirect, flash
from flask.ext.sqlalchemy import SQLAlchemy
from python.main import *
from python.write_map_file import *
from python.write_results_file import *

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)

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
	f=open(app.root_path+"/templates/layout.html",'r')
	g=f.readlines()
	f.close()
	f=open(app.root_path+"/templates/layout.html",'w')
	g[18]='    <p>You will arrive in ' + end + ' at ' + destination_time + '.</p><p>...loading great restaurants</p>\n'
	f.writelines(g)
	f.close()
	
@app.route('/results')
def results():
    return render_template('results.html')

@app.route('/test')
def test():
    return render_template('test.html')

@app.route('/map')
def map():
    return render_template('map.html')    

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
		#db_entry = Search(datetime.datetime.now(), start, end, 'I\'m feeling lucky', 'I\'m feeling lucky')
		search = RestaurantFinder(start,end,20,2,'12:00','15:00',9,30,15,15,just_best=True,radius=20000) # GMaps Dist Matrix API can only handle 9
		write_map_file(start, end, search.filtered_table, just_best=True)
		write_results_file(search.filtered_table, time_leaving, just_best=True)
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
		write_map_file(start, end, search.filtered_table, just_best=False, time_leaving=time_leaving)
		write_results_file(search.filtered_table, time_leaving, just_best=False, time_leaving=time_leaving)

	return render_template('map.html')

class Search(db.Model):
    timestamp = db.Column(db.DateTime.__init__(), primary_key=True)
    starting_loc = db.Column(db.String(80))
    destination = db.Column(db.String(80))
    start_time = db.Column(db.String(80))
    destination_time = db.Column(db.String(80))

    def __init__(self, timestamp, starting_loc, destination, start_time, destination_time):
        self.timestamp = timestamp
        self.starting_loc = starting_loc
        self.destination = destination
        self.start_time = start_time
        self.destination_time = destination_time

    def __repr__(self):
        return '<Timestamp %r><Name %r><End %r><Start Time %r><Time Eating %r>' % self.timestamp, self.starting_loc, self.destination, self.start_time, self.destination_time

""" For running Flask locally"""
if __name__ == '__main__':
    app.run(debug=True)
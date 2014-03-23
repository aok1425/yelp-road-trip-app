import os
from flask import Flask, request, url_for, render_template, redirect, flash

app = Flask(__name__)

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

	do_everything(start,end,7,5,time_leaving,eating_time,10,40,20,20)
	make_HTML_file(start,end,filtered_table)
	
	return 'You want to start at '+start+', end at '+end+', leave at '+time_leaving+', and eat around '+eating_time+'.'
	#return redirect(url_for('static', filename='map.html'))
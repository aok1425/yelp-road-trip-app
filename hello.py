import os
from flask import Flask, request, url_for, render_template, redirect, flash

app = Flask(__name__)

@app.route('/')
def show_input_form():
    return 'This should work!!!'
	
@app.route('/test')
def show_this_page():
    return render_template('input_form.html')
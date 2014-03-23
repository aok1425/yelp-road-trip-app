import os
from flask import Flask

app = Flask(__name__)

@app.route('/')
def show_input_form():
    return 'This should work!!!'
#! /usr/bin/python

from flask import Flask, request, render_template
import random
import logging
import zmq
import os 
import datetime
os.chdir("/home/pi/html/cyclo/")

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Global Variables
datestr = '2017-01-01'

app = Flask(__name__)
requestID = 0
context = zmq.Context()
sock = context.socket(zmq.REQ)
sock.connect("tcp://127.0.0.1:5680")
# Define the socket using the "Context"

# Define subscription and messages with prefix to accept.

@app.route('/')
def home():
  return render_template("sensor.html")


@app.route('/settime', methods=["PUT"])
def settime():
    global datestr
    global requestID
    requestID = 1 

    timestr = '10:10:10'
    timestr = request.form['ctime']
    #cmd = sudo date -s "2017-07-18 18:00:00"
    cmd = 'sudo date -s '
    cmd = cmd + '"'+ datestr 
    cmd = cmd + ' ' + timestr  +  '"'
    print "Setting date and time"
    print cmd
    os.system(cmd)
    time.sleep(5)
    return "OK"

@app.route('/setdate', methods=["PUT"])
def setdate():
    global datestr 
    datestr = request.form['ctime']
    return "OK"
 
@app.route('/reset', methods=["POST"])
def ResetAll():
   global requestID
   requestID = 1 
   return "OK"

@app.route('/speed', methods=["POST"])
def sendspeed():
   global context
   global sock
   global requestID

   if requestID == 1:
      sock.send("ResetTrip")
   elif requestID == 2:
      sock.send("Shutdown")
   else:
      sock.send("hello")
      
   message = sock.recv()
   requestID =  0
   return str(message) 


if __name__ == '__main__':
  app.run(host="0.0.0.0", port=5000,debug=False)


from flask import Flask, request, render_template
import random

app = Flask(__name__)

myspeed = 0
mycadence = 0
@app.route('/')
def home():
  return render_template("sensor.html")

@app.route('/speed', methods=["POST"])
def sendspeed():
  global myspeed
  print "speed"
  myspeed = myspeed + 1 
  return str(myspeed) 

@app.route('/cadence', methods=["POST"])
def sendCadence():
  global mycadence 
  print  "Cadence"
  mycadence = mycadence + 1
  return str(mycadence) 

if __name__ == '__main__':
  app.run(host="0.0.0.0", port=5000,debug=False)


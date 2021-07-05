import threading
import os
import time
import cv2
import pytz
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_required, current_user, login_user, logout_user
from flask import Response, send_file

ip_camera_url = "YourStreamURL"
stream = cv2.VideoCapture(ip_camera_url)
frame_to_display = None
tz_RO = pytz.timezone('Europe/Bucharest')
frame_ = None
ret_ = None
db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(70), unique=True)
    password = db.Column(db.String(100))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secretKey11'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
db.init_app(app)

lm = LoginManager()
lm.login_view = 'login'
lm.init_app(app)
stream_live = False
detect_movement = True
record = True

@lm.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def welcome():
    test = None
    if stream_live:
        test = 'true'
    else:
        test = 'false'
    return render_template('welcome.html', name = current_user.name, live = test)

@app.route('/stream_live', methods=['POST'])
@login_required
def stream_live():
    global stream_live
    json = request.json['status']
    if json == 1:
        stream_live = True
    else:
        stream_live = False
    return jsonify({'success' : 'success'})

@app.route('/get_gifs')
@login_required
def get_gifs():
    path = os.getcwd() + "\movement_gifs"
    list_of_files = []
    for filename in os.listdir(path):
        list_of_files.append(filename)
    return render_template('get_gifs.html', list_of_files=list_of_files)

@app.route("/send_gif/<name>")
@login_required
def send_gif(name):
    try:
        return send_file('movement_gifs/' + name, attachment_filename=name, as_attachment=True)
    except FileNotFoundError:
        print("File not found")

@app.route('/get_move_videos')
@login_required
def get_move_videos():
    path = os.getcwd() + "\movement_detected"
    list_of_files = []
    for filename in os.listdir(path):
        list_of_files.append(filename)
    return render_template('get_move_videos.html', list_of_files=list_of_files)

@app.route("/send_move/<name>")
@login_required
def send_move(name):
    try:
        return send_file('movement_detected/' + name, attachment_filename=name, as_attachment=True)
    except FileNotFoundError:
        print("File not found")

@app.route('/recordings')
@login_required
def recordings():
    path = os.getcwd() + "\continous_recording"
    list_of_files = []
    for filename in os.listdir(path):
        list_of_files.append(filename)
    return render_template('recordings.html', list_of_files=list_of_files)

@app.route("/send_rec/<name>")
@login_required
def send_rec(name):
    try:
        return send_file('continous_recording/' + name, attachment_filename=name, as_attachment=True)
    except FileNotFoundError:
        print("File not found")

@app.route('/controls')
@login_required
def controls():
    global detect_movement, record
    v1 = None
    v2 = None

    if detect_movement:
        v1 = 'true'
    else:
        v1 = 'false'

    if record:
        v2 = 'true'
    else:
        v2 = 'false'

    return render_template('controls.html', v1 = v1, v2 = v2)

@app.route('/controls_post', methods=['POST'])
@login_required
def controls_post():
    global detect_movement, record
    json = request.json['movement']
    json1 = request.json['record']
    if json == 1:
        detect_movement = True
    else:
        detect_movement = False
    if json1 == 1:
        record = True
    else:
        record = False
    return jsonify({'success' : 'success'})

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')
    remember = True

    user = User.query.filter_by(email=email).first()

    if not user:
        flash('Wrong email')
        return redirect(url_for('login'))

    if not check_password_hash(user.password, password):
        flash('Wrong password')
        return redirect(url_for('login'))

    login_user(user, remember=remember)
    return redirect(url_for('welcome'))

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register_post():
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')

    user = User.query.filter_by(email=email).first()

    if user:
        flash('Email address already exists.')
        return redirect(url_for('register'))

    new_user = User(email=email, name=name, password=generate_password_hash(password, method='sha256'))

    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

def display():
    global frame_, stream_live

    while True:
        if frame_ is None or not stream_live:
            continue

        # frame = imutils.resize(frame_, width=1280)
        (f, image) = cv2.imencode(".jpg", frame_)
        if not f:
            continue
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' +
               bytearray(image) + b'\r\n')
        time.sleep(.018)

@app.route("/video_feed")
@login_required
def video_feed():
    return Response(display(), mimetype="multipart/x-mixed-replace; boundary=frame")

def grab_frames():
    global ret_, frame_
    while True:
        if stream.isOpened():
            (status, frame) = stream.read()
            ret_ = status
            frame_ = frame
        time.sleep(.01)
from email.mime.application import MIMEApplication
from os.path import basename
import flask_server
import cv2
import numpy as np
import imutils
import time
from datetime import datetime
import pytz
import threading
from PIL import Image
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import socket
import requests

gifname = ''
movement_pending = False

def motion_detect():
    global gifname
    global movement_pending
    frame1 = None
    frame2 = None
    counter = 1
    motion_detected = False
    numar = 50
    no_presence = numar
    out = 0
    images = []

    stream_width = 500  # int(stream.get(3))
    stream_height = int((stream_width * 9) / 16)  # int(stream.get(4))
    start = 0
    last = False
    recording = False
    start_gif = 0
    current_gif = 0
    end_gif = False

    while True:
        if not flask_server.detect_movement:
            cv2.destroyAllWindows()
            if out.isOpened():
                out.release()
            continue
        ret = flask_server.ret_
        frame = flask_server.frame_
        if not ret:
            # print("Stream maybe down. Please check.")
            continue
        frame = imutils.resize(frame, width=stream_width)
        gray_conversion = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gaussian_blur = cv2.GaussianBlur(gray_conversion, (21, 21), 0)

        if frame1 is None:
            frame1 = gaussian_blur

        if counter >= 20:
            frame1 = frame2
            counter = 1
        counter = counter + 1

        frame2 = gaussian_blur
        difference = cv2.absdiff(frame1, frame2)
        tresh_difference = cv2.threshold(difference, 30, 255, cv2.THRESH_BINARY)[1]
        tresh_difference = cv2.dilate(tresh_difference, None, iterations=2)
        cnts, h = cv2.findContours(tresh_difference, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        for p in cnts:
            if cv2.contourArea(p) < 3000:
                continue
            motion_detected = True
            (x, y, w, h) = cv2.boundingRect(p)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
            if no_presence >= numar:
                start = time.time()
            last = True

        if motion_detected:
            motion_detected = False
            no_presence = 0
            if not recording:
                datetime_RO = datetime.now(flask_server.tz_RO)
                recording = True
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                filename = 'movement_detected/' + datetime_RO.strftime('%Y-%m-%d--%H-%M-%S') + '.mp4'
                out = cv2.VideoWriter(filename, fourcc, 25, (stream_width, stream_height))
                start = time.time()
                end_gif = False

        if no_presence < numar:
            no_presence = no_presence + 1
            recording = True
            out.write(frame)
            current_gif = time.time()
            datetime_ROq = datetime.now(flask_server.tz_RO)
            if (current_gif - start_gif >= 1) and (not end_gif):
                imgRGB = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(imgRGB, 'RGB')
                images.append(img)
                start_gif = current_gif
                if len(images) == 3:
                    end_gif = True
                    filename = 'movement_gifs/' + datetime_ROq.strftime('%Y-%m-%d--%H-%M-%S') + '.gif'
                    images[0].save(filename, save_all=True, append_images=images[1:], optimize=False,
                                   duration=300, loop=0)
                    gifname = filename
                    movement_pending = True

            if len(images) == 3:
                images.clear()
        elif last:
            last = False
            recording = False
            out.release()
            movement_pending = False
            current = time.time()
            print("recording ended")
            print("No movement")
        cv2.imshow("frame", frame)

        key = cv2.waitKey(1)
        if key & 0xFF == ord('q'):
            if out.isOpened():
                out.release()
            images.clear()
            break
        time.sleep(.018)

    cv2.destroyAllWindows()

def continous_recording():
    stream1_width = int(flask_server.stream.get(3))
    stream1_height = int(flask_server.stream.get(4))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    datetime_RO = datetime.now(flask_server.tz_RO)
    filename1 = 'continous_recording/' + datetime_RO.strftime('%Y-%m-%d--%H-%M-%S') + '.mp4'
    out = cv2.VideoWriter(filename1, fourcc, 25,
                          (stream1_width, stream1_height))
    video_closed = False
    start = time.time()

    try:
        while True:
            if not flask_server.record:
                if out.isOpened():
                    out.release()
                    video_closed = True
                continue
            current = time.time()
            if current - start >= 30:
                if out.isOpened():
                    out.release()
                    video_closed = True
            if video_closed:
                video_closed = False
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                datetime_RO = datetime.now(flask_server.tz_RO)
                filename1 = 'continous_recording/' + datetime_RO.strftime('%Y-%m-%d--%H-%M-%S') + '.mp4'
                out = cv2.VideoWriter(filename1, fourcc, 25,
                                (stream1_width, stream1_height))
                start = time.time()
            else:
                ret = flask_server.ret_
                frame = flask_server.frame_
                if not ret:
                    # print("Stream maybe down. Please check.")
                    continue
                # frame = imutils.resize(frame, width=1280)
                out.write(frame)
                time.sleep(0.018)
    except KeyboardInterrupt:
        print("Closing recording")
        if out.isOpened():
            out.release()
        flask_server.stream.release()

def send_mail():
    global gifname
    last_sent_time = 0
    last_sent_file = ''
    host_name = socket.gethostname()
    host_ip = socket.gethostbyname(host_name)
    print(host_ip)

    while True:
        current_time = time.time()
        if last_sent_file != gifname and current_time - last_sent_time >= 60 and movement_pending:
            last_sent_file = gifname
            last_sent_time = current_time
            mail_content = 'Motion detected. Please check the stream and the attached GIF. http://' + host_ip + ':5000/'
            sender_address = 'YourEmailHere'
            sender_pass = 'YourPasswordHere'
            receiver_address = 'YourEmailHere'

            filename = gifname
            file = open(filename, 'rb')
            msg = MIMEMultipart()
            msg['From'] = sender_address
            msg['To'] = receiver_address
            msg['Subject'] = 'Motion detected ' + basename(filename)
            msg.attach(MIMEText(mail_content, 'plain'))
            part = MIMEApplication(
                file.read(),
                Name=basename(filename)
            )
            part['Content-Disposition'] = 'attachment; filename="%s"' % basename(filename)
            msg.attach(part)

            smtp = smtplib.SMTP('smtp.gmail.com', 587)
            smtp.ehlo()
            smtp.starttls()
            smtp.login(sender_address, sender_pass)

            smtp.sendmail(sender_address, receiver_address, msg.as_string())
            smtp.quit()
            print('Mail Sent')
        else:
            time.sleep(1)

t4 = threading.Thread(target=flask_server.grab_frames, name='thread4')
# t4.daemon = True
t4.start()
# video_stream_widget = flask_server.VideoStreamWidget()
t1 = threading.Thread(target=motion_detect, name='thread1')
t1.start()
t2 = threading.Thread(target=continous_recording, name='thread2')
t2.start()
t3 = threading.Thread(target=send_mail, name='thread3')
t3.start()


flask_server.app.run(host='0.0.0.0', port=5000, debug=True, threaded=True, use_reloader=False)
#!/usr/bin/env python3

import os
import time
import math
import busio
import board
import cv2
import adafruit_amg88xx
import matplotlib as cm
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
from scipy.interpolate import griddata
from twilio.rest import Client

def draw_label(img, text, pos, bg_color):
    font_face = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.6
    color = (0, 0, 0)
    thickness = cv2.FILLED
    margin = 2
    txt_size = cv2.getTextSize(text, font_face, scale, thickness)
    end_x = pos[0] + txt_size[0][0] + margin
    end_y = pos[1] - txt_size[0][1] - margin
    start_x = pos[0] - margin
    start_y = pos[1] + margin
    cv2.rectangle(img, (start_x, start_y), (end_x, end_y), bg_color, thickness)
    cv2.putText(img, text, pos, font_face, scale, color, 1, cv2.LINE_AA)

account_sid = os.environ['ACCOUNT_SID']
auth_token = os.environ['AUTH_TOKEN']

#out = cv2.VideoWriter('therm.avi',cv2.VideoWriter_fourcc('M','J','P','G'), 10, (800,480))

plt.ion()
status = "reading"
face_in_frame = False
temp_readings = []
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
face_cascade = cv2.CascadeClassifier('/home/pi/Scripts/therm/haarcascade_frontalface_default.xml')
i2c = busio.I2C(board.SCL, board.SDA)
amg = adafruit_amg88xx.AMG88XX(i2c)
ambient_temp = [ 65 ]
temp_offset = 25.0
alpha = 1
corrected_temp = [ 98.6 ]
display_temp = 98.6
room_temp = 65.0
og_frame = cv2.imread("/home/pi/Scripts/therm/static/img/therm_background.png")
blank_screen = cv2.imread("/home/pi/Scripts/therm/static/img/default2.png")
wait_ = cv2.imread("/home/pi/Scripts/therm/static/img/clock.png")
stop = cv2.imread("/home/pi/Scripts/therm/static/img/stop.png")
go = cv2.imread("/home/pi/Scripts/therm/static/img/go.png")
cv2.namedWindow('therm', cv2.WINDOW_FREERATIO)
cv2.setWindowProperty('therm', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
fig = plt.figure(num='AMG8833 Thermal Scanner', figsize=(2.0, 2.0));
points = [(math.floor(ix / 8), (ix % 8)) for ix in range(0,64)]
grid_x, grid_y = np.mgrid[0:7:64j, 0:7:64j]
ax = fig.add_subplot(111)
colors = ['b', 'c', 'k', 'g', 'm', 'y' ]

#fourcc = cv2.VideoWriter_fourcc(*'XVID')
#out = cv2.VideoWriter('therm.avi', fourcc, 10.0, (800,480))

while(True):
    ret, img = cap.read()
    img  = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    img = cv2.flip(img, 1)
    frame = og_frame.copy()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.2, 5)
    face_sizes = []
    for (x, y, w, h) in faces:
        face_sizes.append(w*h)
        cv2.rectangle(img, (x-5, y-5), (x+w+5, y+h+5), (255, 255, 255), 2)
        
    if len(face_sizes) > 0:
        (x, y, w, h) = faces[np.argmax(face_sizes)]
        tx = int(x+w/2-75)
        ty = int(y+h/2-75)
        if tx < 0: tx = 0
        if ty < 0: ty = 0
        bx = tx + 150
        by = ty + 150
        if bx > 240:
            tx = tx - (bx-240)
            bx = tx + 150 
        img = img[ty:ty+150, tx:bx]
        img = cv2.resize(img,(300,300))
        faces = faces[np.argmax(face_sizes):np.argmax(face_sizes)+1]
    else:
        tx = int(img.shape[1]/2 - 75)
        ty = int(img.shape[0]/2 - 75)
        img = img[ty:ty+150, tx:tx+150]
            
    pixels = np.fliplr(np.rot90(np.asarray(amg.pixels), k=3)).flatten()
    label = "Room Temp: {0:.1f} F".format(np.average(ambient_temp))
    draw_label(frame, label, (490,210), (255,255,255))
    label = "Stdev: {0:.4f}".format(np.std(ambient_temp))
    draw_label(frame, label, (490, 230), (255,255,255))
    if type(faces) is tuple:
        if np.std(pixels) < 1.5:
            if len(ambient_temp) == 100:
                ambient_temp = ambient_temp[1:]
            temp_scan = np.asarray(amg.pixels).flatten()
            temp_scan_f = (9/5)*temp_scan + 32
            room_f = temp_scan_f[temp_scan_f > 50.0]
            room_f = room_f[room_f < 75.0]
            if len(room_f) >= 1:
                ambient_temp.append( np.average(room_f))
            room_temp = np.average(ambient_temp)
            #if room_temp < 70:
            #    client = Client(account_sid, auth_token)
            #    client.messages.create(
            #        body="Um, it's getting a bit cold in here. \n\nTemp: {0:.1f} F".format(display_temp),
            #        media_url=['https://precisionathleticswi.com/images/jack_on_ice.jpg'],
            #        from_="+19202602260",
            #        to="+19206295560"
            #    )
        draw_label(img, 'No Face Detected', (20,30), (255,255,255))
        if face_in_frame:
            if display_temp >= 100 and alpha <= 0.05 and len(corrected_temp) >= 1:
                client = Client(account_sid, auth_token)
                client.messages.create(
                    body="A scan of {0:.1f} F was detected by Thermie.".format(display_temp),
                    from_="+19202602260",
                    to="+19206295560"
                )
            if display_temp < 100 and alpha <= 0.05 and len(corrected_temp) >= 1:
                message_body = "A scan of {temp:.1f} F was detected by Thermie. \n\nRoom temp: {room_temp:.1f} F \nalpha: {alpha:.4}"
                client = Client(account_sid, auth_token)
                client.messages.create(
                    body=message_body.format(temp=display_temp, room_temp = room_temp, alpha=alpha),
                    from_="+19202602260",
                    to="+19206295560"
                )
            corrected_temp = [ 98.6 ]
            display_temp = 98.6
            temp_readings = []
            face_in_frame = False
            
    for (x, y, w, h) in faces:
        if face_in_frame == False:
            temp_readings = []
        face_in_frame = True
        if h*w < 2500:
            label = "Please step closer."
            draw_label(img, label, (20, 30), (255, 255, 255))
        elif h*w >= 6000:
            label = "Please step back a bit."
            draw_label(img, label, (20, 30), (255, 255, 255)) 
        else:
            temp_scan = np.fliplr(np.rot90(np.asarray(amg.pixels), k=3)).flatten()
            temp_scan_f = (9/5)*temp_scan + 32
            human_f = temp_scan_f[temp_scan_f > 70.0]
            human_f = human_f[human_f < 95.0]
            temp_readings.append(np.average(human_f) + temp_offset)                    
            corrected_temps = temp_readings
            if len(corrected_temp) > 10 or np.std(corrected_temp) > 0.10:
                corrected_temp = corrected_temp[1:]
            corrected_temp.append(np.average(corrected_temps))
            display_temp = np.average(corrected_temp)
            alpha = np.std(corrected_temp)
            label = "alpha: {0:.4f}".format(np.std(corrected_temp))
            draw_label(frame, label, (490, 270), (255,255,255))
            label = "Temp: {0:.1f} F".format(display_temp)
            draw_label(img, label, (40, 30), (255,255,255))
            if alpha <= 0.05:
                label = "Observed Temp: {0:.1f} F".format(display_temp)
                draw_label(frame, label, (490, 250), (255,255,255))
                if display_temp >= 101.0:
                    frame[300:400, 550:650] = stop
                    status = "high"
                else:
                    frame[300:400, 550:650] = go
                    status = "normal"
            else:
                label = "Reading Temp. Please Wait."
                draw_label(frame, label, (490, 250), (255,255,255))
                frame[300:400, 550:650] = wait_
                status = "reading"
            pixels_f = (9/5)*pixels+32
            grid_z = griddata(points, pixels_f, (grid_x, grid_y), method='cubic')
            flat_grid = grid_z.flatten()
            filtered_flat_grid = flat_grid[flat_grid >=70]
            flat_grid = filtered_flat_grid[filtered_flat_grid <=95]
            hist, bin_edges = np.histogram(flat_grid, bins=16)
            grid_z[grid_z < bin_edges[len(bin_edges) - 4]] = 0
            x_scatter_data = []
            y_scatter_data = []
            for y, row in enumerate(grid_z):
                for x, cell in enumerate(row):
                    if cell != 0:
                        x_scatter_data.append(x)
                        y_scatter_data.append(63 - y)

            found_groups = False
            group_count = 0
            data_grid = np.dstack((x_scatter_data, y_scatter_data))[0]
            j = 1
            ax.clear()
            while found_groups == False and j < 11:
                kmeans = KMeans(n_clusters=j, init='k-means++', max_iter=10, n_init=10, random_state=0)
                kmeans.fit(data_grid)
                j += 1
                if kmeans.inertia_ < 15000 and found_groups == False:
                    group_count = j
                    found_groups = True
            if group_count > 0:
                kmeans = KMeans(n_clusters=group_count, init="k-means++", max_iter=10, n_init=10, random_state=0)
                pred_y = kmeans.fit_predict(data_grid)
            i = 0
            max_size = 0
            group_index = 0
            group_x = 0
            group_w = 0
            group_y = 0
            group_h = 0
            zone_x = -1
            zone_w = 0
            zone_y = 0
            zone_h = 0
            temp_reading = 0
            while i < group_count:
                series = data_grid[pred_y == i]
                total = 0
                data_buffer = []
                for cell in series:
                    data_buffer.append(grid_z[63-cell[1]][cell[0]])
                    if zone_x == -1:
                        zone_x = cell[0]
                        zone_w = zone_x - cell[0]
                        zone_y = 63 - cell[1]
                    if zone_x > cell[0]: 
                        zone_x = cell[0]
                        zone_w = zone_x - cell[0]
                    if zone_y < 63 - cell[1]:
                        zone_y = 63 - cell[1]
                        zone_h = zone_y - (63-cell[1])
                    total += grid_z[63 - cell[1]][cell[0]]
                zone_average = total / len(series)
                if max_size < len(data_buffer):
                    max_size = len(data_buffer)
                    group_x = zone_x
                    group_w = zone_w
                    group_y = zone_y
                    group_h = zone_h
                    group_index = i
                    temp_reading = zone_average
                ax.scatter(kmeans.cluster_centers_[:, 0], kmeans.cluster_centers_[:,1], s=100, c='blue')
                ax.scatter(series[:,0], series[:,1], label=pred_y[pred_y == i], s=25, c=colors[i % 6])
                #ax.set_xlim(group_x, group_x + group_w)
                #ax.set_ylim(group_y, group_y + group_h)
                print(group_x, group_x + group_w)
                print(group_y, group_y + group_h)
                i += 1
            print("Group Number: {}".format(group_index), " Temp: {:.2f} F".format(temp_reading), " Size {}".format(max_size))
            fig.tight_layout()
            fig.canvas.draw()
   
    x_offset = 75
    y_offset = 90
    if face_in_frame:
        frame[y_offset:y_offset+img.shape[0], x_offset:x_offset+img.shape[1]] = img
    else:
        frame[y_offset:y_offset+300, x_offset:x_offset+300] = blank_screen
    #out.write(frame)
    cv2.imshow('therm', frame)
    #out.write(frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
#out.release()
cv2.destroyAllWindows()

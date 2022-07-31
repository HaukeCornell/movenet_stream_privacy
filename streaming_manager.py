#!/usr/bin/env python3
# start with python .\demo.py -e

import argparse
import cv2
from MovenetRenderer import MovenetRenderer  
from flask import Flask, render_template, Response, request, json, stream_with_context
import numpy as np
from threading import Thread
import polygon_test
import requests

app = Flask(__name__)

parser = argparse.ArgumentParser()
parser.add_argument("-e", "--edge", action="store_true",
                    help="Use Edge mode (the cropping algorithm runs on device)")
parser.add_argument("-m", "--model", type=str, default='thunder',
                    help="Model to use : 'thunder' or 'lightning' or path of a blob file (default=%(default)s)")
parser.add_argument('-i', '--input', type=str, default='rgb',
                    help="'rgb' or 'rgb_laconic' or path to video/image file to use as input (default=%(default)s)")
parser.add_argument('-c', '--crop', action="store_true", 
                    help="Center cropping frames to a square shape (smaller size of original frame)") 
parser.add_argument('-nsc', '--no_smart_crop', action="store_true", 
                    help="Disable smart cropping from previous frame detection")   
parser.add_argument("-s", "--score_threshold", default=0.2, type=float,
                    help="Confidence score to determine whether a keypoint prediction is reliable (default=%(default)f)") 
parser.add_argument('-f', '--internal_fps', type=int,                                                                                     
                    help="Fps of internal color camera. Too high value lower NN fps (default: depends on the model")    
parser.add_argument('--internal_frame_height', type=int, default=640,                                                                                    
                    help="Internal color camera frame height in pixels (default=%(default)i)")          
parser.add_argument("-o","--output",
                    help="Path to output video file")
 
parser.add_argument("-b", "--background_pose", action="store_true",
                    help="Calculate even without connect web client") 
# TODO: depth
parser.add_argument("-d","--depth", action="store_true",                                                                                    
                    help="Display depth image instead of color image")    

    
args = parser.parse_args()

if args.edge:
    from MovenetDepthaiEdge import MovenetDepthai
else:
    from MovenetDepthai import MovenetDepthai

pose = MovenetDepthai(input_src=args.input, 
            model=args.model,    
            score_thresh=args.score_threshold,  
            crop=args.crop,    
            smart_crop=not args.no_smart_crop,     
            internal_fps=args.internal_fps,
            internal_frame_height=args.internal_frame_height
            )

renderer = MovenetRenderer(
                pose, 
                depth=args.depth)

# privacy modes
blur = True
peek = False
mask = False
blind = False

SCORE_TRESH = 0.2
WINDOW = 30
body_location_queue = []
body_is_there = False

# visualization
render_body = True
render_trapezoid = True
pts_absolute = np.array([[0,0],[0,0],[0,0],[0,0]], np.int32)
background_pose_enabled = args.background_pose

# input camera
input_camera = args.input

def update_trapezoid(pts_percent):

    pts_adjustment_OAK = np.array([[11.52, 6.48],[11.52, 6.48],[11.52, 6.48],[11.52, 6.48]], np.half)
    pts_adjustment_PI = np.array([[6.40, 4.80],[6.40, 4.80],[6.40, 4.80],[6.40, 4.80]], np.half)

    if input_camera == '0':
        pts_multiplier = np.int_(np.multiply(pts_percent, pts_adjustment_PI))
    elif input_camera == 'rgb':
        pts_multiplier = np.int_(np.multiply(pts_percent, pts_adjustment_OAK))

    global pts_absolute
    pts_absolute = pts_multiplier.reshape((-1,1,2))
    print (pts_absolute)

def draw_gradient_alpha_rectangle(frame, rectangle_position, rotate):
    (xMin, yMin), (xMax, yMax) = rectangle_position
    color = np.array((0,0,0), np.uint8)[np.newaxis, :]
    mask1 = np.rot90(np.repeat(np.tile(np.linspace(1, 0, (rectangle_position[1][1]-rectangle_position[0][1])), ((rectangle_position[1][0]-rectangle_position[0][0]), 1))[:, :, np.newaxis], 3, axis=2), rotate) 
    frame[yMin:yMax, xMin:xMax, :] = mask1 * frame[yMin:yMax, xMin:xMax, :] + (1-mask1) * color

    return frame

def draw_black_rectangle(frame,x,y,w,h):
    start_point = ((int(frame.shape[0]*x)), (int(frame.shape[1]*y)))
    end_point = ((int(frame.shape[0]*x+frame.shape[0]*w)), (int(frame.shape[1]*y+frame.shape[1]*h)))
    color = (0, 0, 0)
    thickness = -1
    frame = cv2.rectangle(frame, start_point, end_point, color, thickness)
    return frame

@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('index.html')

@app.route('/', methods=['POST','GET'])
def post_get():
   
    data = json.loads(request.get_data())
    
    global blur, peek, render_body, render_trapezoid

    if "camera" in data:
        if data['camera'] == "open":
            blur = mask = blind = False
            peek = True 
            print("open")
        elif data['camera'] == "blur":
            peek = mask = blind = False 
            blur = True
            print("blur")
        elif data['camera'] == "mask":
            blur = peek = blind = False
            mask = True 
            print("mask")
        elif data['camera'] == "blind":    
            blur = mask = peek = False
            blind = True 
            print("blind")

    elif "visualization" in data:
        if data['visualization'] == "body_on":
            render_body = True
        elif data['visualization'] == "body_off":
            render_body = False
        elif data['visualization'] == "trapezoid_on":
            render_trapezoid = True
        elif data['visualization'] == "trapezoid_off":
            render_trapezoid = False
    elif "1x" in data:
        pts_node_red = np.array([[data['1x'],data['1y']],
                                [data['2x'],data['2y']],
                                [data['3x'],data['3y']],
                                [data['4x'],data['4y']]], np.half)
        update_trapezoid(pts_node_red)

    return 'JSON posted'

@app.route('/video_feed')
def video_feed():
    def gen():
        try:
            if background_pose_enabled:
                global t1
                global background_pose_running 

                if background_pose_running:
                    background_pose_running = False
                    t1.join()

            while True:
                frame, body = pose.next_frame()

                if frame is None: break
            
                if blur:
                    frame =  renderer.draw(cv2.blur(frame, (30, 30)), body) 
                elif peek:
                    frame =  renderer.draw(frame, body) 
                elif mask:
                    frame = draw_gradient_alpha_rectangle(frame,((0, 0), (int(frame.shape[1]*1.0), int(frame.shape[0]*0.4))), 1)
                    frame = draw_black_rectangle(frame, 0.2,0.1, 0.2,0.4)
                elif blind:
                    break

                if render_trapezoid:
                    cv2.polylines(frame,[pts_absolute],True,(0,255,255))        
                
                location, body_presence = body_presence_average(body)
                check_trapezoid(location, body_presence)

                if (body_presence > 0.1):
                    cv2.circle(frame, (int(location[0]), int(location[1])), int(8 * body_presence), (192,136,189), -11)
                
                                
                encoded_frame = cv2.imencode('.jpg', frame)[1].tobytes()
                    
                yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + encoded_frame + b'\r\n')
        except GeneratorExit:
            print('closed')
            if background_pose_enabled and not background_pose_running:
                background_pose_running = True
                t1 = Thread(target=background_pose)
                t1.start()

    return Response(stream_with_context(gen()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

def body_presence_average(body):
    body_location_queue.append(renderer.body_location(body,SCORE_TRESH))

    if (len(body_location_queue) == WINDOW):
        body_location_queue.pop(0)
        location = np.ma.average(body_location_queue, axis=0)
        body_presence = np.ma.count(body_location_queue) / WINDOW
        return location, body_presence
    else:
        return np.NaN, 0.0

def check_trapezoid(location, body_presence):
    if (body_presence > 0.9):
        global body_is_there
        if (polygon_test.is_within_polygon(pts_absolute,location) and not body_is_there):
            # body_location_queue.clear()
            print("body there")
            requests.post('http://localhost:1880/body', json = {'body': 'is_there'})
            body_is_there = True
        elif (body_is_there and not polygon_test.is_within_polygon(pts_absolute,location)):
            # body_location_queue.clear()
            print("body not there")
            requests.post('http://localhost:1880/body', json = {'body': 'not_there'})
            body_is_there = False

def background_pose ():

    while background_pose_running:
        _, body = pose.next_frame()
        location, body_presence = body_presence_average(body)
        check_trapezoid(location, body_presence)
        
if __name__ == '__main__':
    pts_initial = [[np.array([[35,10],[65,10],[70,80],[30,80]], np.half)]]
    update_trapezoid(pts_initial)

    if (background_pose_enabled):
        
        global t1
        global background_pose_running 
        background_pose_running = True
        
        t1 = Thread(target=background_pose)
        t1.start()
    
    app.run(host='0.0.0.0', threaded=True)

pose.exit()
exit()
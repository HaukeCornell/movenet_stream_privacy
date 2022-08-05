import cv2
import numpy as np

import time
from motion_detector.detector import MotionDetector
from motion_detector.packer import pack_images
from numba import jit
from flask import Flask, render_template, Response, request, json, stream_with_context
from threading import Thread
import requests

# from https://github.com/bwsw/rt-motion-detection-opencv-python/blob/master/setup.py

app = Flask(__name__)

pts_absolute = np.array([[0,0],[0,0],[0,0],[0,0]], np.int32)
background_motion_enabled = True


detector = MotionDetector(bg_history=10,
                        bg_skip_frames=1,
                        movement_frames_history=5,
                        brightness_discard_level=20,
                        bg_subs_scale_percent=0.2,
                        pixel_compression_ratio=0.05,
                        group_boxes=True,
                        expansion_step=5)


def update_trapezoid(pts_percent):

    pts_adjustment_PI = np.array([[6.40, 4.80],[6.40, 4.80],[6.40, 4.80],[6.40, 4.80]], np.half)

    pts_multiplier = np.int_(np.multiply(pts_percent, pts_adjustment_PI))

    global pts_absolute
    pts_absolute = pts_multiplier.reshape((-1,1,2))
    print (pts_absolute)

def background_motion ():
    # TODO: eliminate duplicate code
    cap = cv2.VideoCapture(0)

    b_height = 320
    b_width = 320

    res = []
    fc = dict()
    ctr = 0
    time.sleep(4)

    while background_motion_running:
        ret, frame = cap.read()
        if frame is None:
            break

        begin = time.time()
        frame = frame[int(pts_absolute.item(1)):int(pts_absolute.item(7)), int(pts_absolute.item(6)):int(pts_absolute.item(4))]
        boxes, frame = detector.detect(frame)
        results = []
        if boxes:
            results, box_map = pack_images(frame=frame, boxes=boxes, width=b_width, height=b_height,
                                            box_filter=filter_fun)

        for b in boxes:
            cv2.rectangle(frame, (b[0], b[1]), (b[2], b[3]), (0, 0, 255), 1)

        end = time.time()
        it = (end - begin) * 1000

        res.append(it)
        print("StdDev: %.4f" % np.std(res), "Mean: %.4f" % np.mean(res), "Last: %.4f" % it,
            "Boxes found: ", len(boxes))

        if len(res) > 10000:
            res = []

        ctr += 1
        nc = len(results)
        if nc in fc:
            fc[nc] += 1
        else:
            fc[nc] = 0

        if ctr % 100 == 0:
            print("Total Frames: ", ctr, "Packed Frames:", fc)
        

@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('index.html')

@app.route('/', methods=['POST','GET'])
def post_get():
   
    data = json.loads(request.get_data())

    global render_trapezoid

    if "1x" in data:
        pts_node_red = np.array([[data['1x'],data['1y']],
                                [data['2x'],data['2y']],
                                [data['3x'],data['3y']],
                                [data['4x'],data['4y']]], np.half)
        update_trapezoid(pts_node_red)

    return 'JSON posted'
@jit(nopython=True)
def filter_fun(b):
    return ((b[2] - b[0]) * (b[3] - b[1])) > 300
              

@app.route('/video_feed')
def video_feed():
    def gen():
        try:
            if background_motion_enabled:
                global t1
                global background_motion_running 

                if background_motion_running:
                    background_motion_running = False
                    t1.join()
            
            cap = cv2.VideoCapture(0)

            # group_boxes=True can be used if one wants to get less boxes, which include all overlapping boxes

            b_height = 320
            b_width = 320

            res = []
            fc = dict()
            ctr = 0
            while True:
                # Capture frame-by-frame
                ret, frame = cap.read()
                if frame is None:
                    break

                begin = time.time()
                frame = frame[int(pts_absolute.item(1)):int(pts_absolute.item(7)), int(pts_absolute.item(6)):int(pts_absolute.item(4))]

                boxes, frame = detector.detect(frame)
                # boxes hold all boxes around motion parts

                ## this code cuts motion areas from initial image and
                ## fills "bins" of 320x320 with such motion areas.
                ##
                results = []
                if boxes:
                    results, box_map = pack_images(frame=frame, boxes=boxes, width=b_width, height=b_height,
                                                    box_filter=filter_fun)

                ## end

                for b in boxes:
                    cv2.rectangle(frame, (b[0], b[1]), (b[2], b[3]), (0, 0, 255), 1)

                end = time.time()
                it = (end - begin) * 1000

                res.append(it)

                if len(res) > 10000:
                    res = []

                ctr += 1
                nc = len(results)
                if nc in fc:
                    fc[nc] += 1
                else:
                    fc[nc] = 0
                # cv2.polylines(frame,[pts_absolute],True,(0,255,255))  

                upscaled_movement  = cv2.resize(detector.color_movement, None, fx= 3, fy= 3, interpolation= cv2.INTER_LINEAR)
                h1, w1 = frame.shape[:2]
                h2, w2 = upscaled_movement.shape[:2]
                vis = np.zeros((max(h1, h2), w1+w2,3), np.uint8)
                vis[:h1, :w1,:3] = frame
                vis[:h2, w1:w1+w2,:3] = upscaled_movement

                encoded_frame = cv2.imencode('.jpg', vis)[1].tobytes()
              
                yield (b'--frame\r\n'
                            b'Content-Type: image/jpeg\r\n\r\n' + encoded_frame + b'\r\n')
        except GeneratorExit:
            print('closed')
            if background_motion_enabled and not background_motion_running:
                background_motion_running = True
                t1 = Thread(target=background_motion)
                t1.start()
    return Response(stream_with_context(gen()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    
    pts_initial = [[np.array([[35,10],[65,10],[70,80],[30,80]], np.half)]]
    update_trapezoid(pts_initial)

    if (background_motion_enabled):
        
        global t1
        global background_motion_running 
        background_motion_running = True
        
        t1 = Thread(target=background_motion)
        t1.start()
    app.run(host='0.0.0.0', threaded=True)
exit()
#!/usr/bin/env python3
# start with python .\demo.py -e

import argparse
import cv2
from MovenetRenderer import MovenetRenderer  
from flask import Flask, render_template, Response, request, json
import numpy as np


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

### Custom arguments ###
parser.add_argument("-bl","--blur", action="store_true",                                                                                    
                    help="Blur image")    
parser.add_argument("-pe","--peek", action="store_true",                                                                                    
                    help="Peek and show image without blur")    
parser.add_argument("-ma","--mask", action="store_true",                                                                                    
                    help="Mask image")          
parser.add_argument("-bli","--blind", action="store_true",                                                                                    
                    help="Do not display an image")    
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

blur = args.blur
peek = args.peek
mask = args.mask
blind = args.blind

CAM = args.input

pts_absolute = np.array([[0,0],[0,0],[0,0],[0,0]], np.int32)

def update_trapezoid(pts_percent):

    pts_adjustment_OAK = np.array([[11.52, 6.48],[11.52, 6.48],[11.52, 6.48],[11.52, 6.48]], np.half)
    pts_adjustment_PI = np.array([[6.40, 4.80],[6.40, 4.80],[6.40, 4.80],[6.40, 4.80]], np.half)

    if CAM == '0':
        pts_multiplier = np.int_(np.multiply(pts_percent, pts_adjustment_PI))
    elif CAM == 'rgb':
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

def gen():
    while True:

        # movenet
        # Run movenet on next frame
        frame, body = pose.next_frame()

        if blur:
            frame =  renderer.draw(cv2.blur(frame, (30, 30)), body) 
        elif peek:
            frame =  renderer.draw(frame, body) 
        elif mask:
            frame = draw_gradient_alpha_rectangle(frame,((0, 0), (int(frame.shape[1]*1.0), int(frame.shape[0]*0.4))), 1)
            frame = draw_black_rectangle(frame, 0.2,0.1, 0.2,0.4)
        elif blind:
            break

        cv2.polylines(frame,[pts_absolute],True,(0,255,255))        
        
        encoded_frame = cv2.imencode('.jpg', frame)[1].tobytes()
            
     
        if frame is None: break

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + encoded_frame + b'\r\n')

@app.route('/', methods=['POST','GET'])
def post_get():
   
    data = json.loads(request.get_data())
    
    global blur
    global peek

    if "camera" in data:
        if data['camera'] == "open":
            blur = False
            peek = True 
            print("open")
        elif data['camera'] == "blur":
            blur = True
            peek = False 
            print("blur")
    elif "1x" in data:
        pts_node_red = np.array([[data['1x'],data['1y']],
                                [data['2x'],data['2y']],
                                [data['3x'],data['3y']],
                                [data['4x'],data['4y']]], np.half)
        update_trapezoid(pts_node_red)

    return 'JSON posted'

@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    pts_initial = np.array([[35,10],[65,10],[70,80],[30,80]], np.half)
    update_trapezoid(pts_initial)
    app.run(host='0.0.0.0', threaded=True)

# TODO: Close from browser
renderer.exit()
pose.exit()
exit()
import cv2
import numpy as np

from time import time
from motion_detector.detector import MotionDetector
from motion_detector.packer import pack_images
from numba import jit
from flask import Flask, render_template, Response, request, json, stream_with_context


app = Flask(__name__)

@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('index.html')



@jit(nopython=True)
def filter_fun(b):
    return ((b[2] - b[0]) * (b[3] - b[1])) > 300

@app.route('/video_feed')
def video_feed():
    def gen():
        try:

            cap = cv2.VideoCapture(0)
            
            # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

            detector = MotionDetector(bg_history=10,
                                    bg_skip_frames=1,
                                    movement_frames_history=2,
                                    brightness_discard_level=5,
                                    bg_subs_scale_percent=0.2,
                                    pixel_compression_ratio=0.1,
                                    group_boxes=True,
                                    expansion_step=5)

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

                begin = time()

                boxes, frame = detector.detect(frame)
                # boxes hold all boxes around motion parts

                ## this code cuts motion areas from initial image and
                ## fills "bins" of 320x320 with such motion areas.
                ##
                results = []
                if boxes:
                    results, box_map = pack_images(frame=frame, boxes=boxes, width=b_width, height=b_height,
                                                    box_filter=filter_fun)
                    # box_map holds list of mapping between image placement in packed bins and original boxes

                ## end

                for b in boxes:
                    cv2.rectangle(frame, (b[0], b[1]), (b[2], b[3]), (0, 0, 255), 1)

                end = time()
                it = (end - begin) * 1000

                res.append(it)
                print("StdDev: %.4f" % np.std(res), "Mean: %.4f" % np.mean(res), "Last: %.4f" % it,
                    "Boxes found: ", len(boxes))

                if len(res) > 10000:
                    res = []

                # idx = 0
                # for r in results:
                #      idx += 1
                #      cv2.imshow('packed_frame_%d' % idx, r)

                ctr += 1
                nc = len(results)
                if nc in fc:
                    fc[nc] += 1
                else:
                    fc[nc] = 0

                if ctr % 100 == 0:
                    print("Total Frames: ", ctr, "Packed Frames:", fc)

                # cv2.imshow('last_frame', frame)
                # cv2.imshow('detect_frame', detector.detection_boxed)
                # cv2.imshow('diff_frame', detector.color_movement)
                
            
                encoded_frame = cv2.imencode('.jpg', detector.color_movement)[1].tobytes()
              
                yield (b'--frame\r\n'
                            b'Content-Type: image/jpeg\r\n\r\n' + encoded_frame + b'\r\n')
        except GeneratorExit:
            print('closed')
    return Response(stream_with_context(gen()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True)

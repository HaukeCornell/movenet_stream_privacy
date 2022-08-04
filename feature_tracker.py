#!/usr/bin/env python3

import cv2
import depthai as dai
from collections import deque
from flask import Flask, render_template, Response, request, json, stream_with_context

class FeatureTrackerDrawer:

    lineColor = (200, 0, 200)
    pointColor = (0, 0, 255)
    circleRadius = 2
    maxTrackedFeaturesPathLength = 30
    # for how many frames the feature is tracked
    # TODO: set from node-red
    trackedFeaturesPathLength = 10

    trackedIDs = None
    trackedFeaturesPath = None

    def trackFeaturePath(self, features):

        newTrackedIDs = set()
        for currentFeature in features:
            currentID = currentFeature.id
            newTrackedIDs.add(currentID)

            if currentID not in self.trackedFeaturesPath:
                self.trackedFeaturesPath[currentID] = deque()

            path = self.trackedFeaturesPath[currentID]

            path.append(currentFeature.position)
            while(len(path) > max(1, FeatureTrackerDrawer.trackedFeaturesPathLength)):
                path.popleft()

            self.trackedFeaturesPath[currentID] = path

        featuresToRemove = set()
        for oldId in self.trackedIDs:
            if oldId not in newTrackedIDs:
                featuresToRemove.add(oldId)

        for id in featuresToRemove:
            self.trackedFeaturesPath.pop(id)

        self.trackedIDs = newTrackedIDs

    def drawFeatures(self, img):

        for featurePath in self.trackedFeaturesPath.values():
            path = featurePath

            for j in range(len(path) - 1):
                src = (int(path[j].x), int(path[j].y))
                dst = (int(path[j + 1].x), int(path[j + 1].y))
                cv2.line(img, src, dst, self.lineColor, 1, cv2.LINE_AA, 0)
            j = len(path) - 1
            cv2.circle(img, (int(path[j].x), int(path[j].y)), self.circleRadius, self.pointColor, -1, cv2.LINE_AA, 0)

    def __init__(self, trackbarName):
        self.trackbarName = trackbarName
        self.trackedIDs = set()
        self.trackedFeaturesPath = dict()


# Create pipeline
pipeline = dai.Pipeline()

# Define sources and outputs
colorCam = pipeline.create(dai.node.ColorCamera)
featureTrackerColor = pipeline.create(dai.node.FeatureTracker)

xoutPassthroughFrameColor = pipeline.create(dai.node.XLinkOut)
xoutTrackedFeaturesColor = pipeline.create(dai.node.XLinkOut)
xinTrackedFeaturesConfig = pipeline.create(dai.node.XLinkIn)

xoutPassthroughFrameColor.setStreamName("passthroughFrameColor")
xoutTrackedFeaturesColor.setStreamName("trackedFeaturesColor")
xinTrackedFeaturesConfig.setStreamName("trackedFeaturesConfig")

# Properties
colorCam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)

if 1:
    colorCam.setIspScale(2,3)
    colorCam.video.link(featureTrackerColor.inputImage)
else:
    colorCam.isp.link(featureTrackerColor.inputImage)

# Linking
featureTrackerColor.passthroughInputImage.link(xoutPassthroughFrameColor.input)
featureTrackerColor.outputFeatures.link(xoutTrackedFeaturesColor.input)
xinTrackedFeaturesConfig.out.link(featureTrackerColor.inputConfig)

# By default the least mount of resources are allocated
# increasing it improves performance
numShaves = 2
numMemorySlices = 2
featureTrackerColor.setHardwareResources(numShaves, numMemorySlices)
featureTrackerConfig = featureTrackerColor.initialConfig.get()

app = Flask(__name__)

@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    def gen():
        try:
            with dai.Device(pipeline) as device:

                # Output queues used to receive the results
                passthroughImageColorQueue = device.getOutputQueue("passthroughFrameColor", 8, False)
                outputFeaturesColorQueue = device.getOutputQueue("trackedFeaturesColor", 8, False)

                inputFeatureTrackerConfigQueue = device.getInputQueue("trackedFeaturesConfig")

                colorFeatureDrawer = FeatureTrackerDrawer("Feature tracking duration (frames)")

                while True:
                    inPassthroughFrameColor = passthroughImageColorQueue.get()
                    passthroughFrameColor = inPassthroughFrameColor.getCvFrame()
                    colorFrame = passthroughFrameColor

                    trackedFeaturesColor = outputFeaturesColorQueue.get().trackedFeatures
                    colorFeatureDrawer.trackFeaturePath(trackedFeaturesColor)
                    colorFeatureDrawer.drawFeatures(colorFrame)
                    
                    if colorFrame is None: break
            
                    encoded_frame = cv2.imencode('.jpg', colorFrame)[1].tobytes()
                                        
                    yield (b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' + encoded_frame + b'\r\n')
        except GeneratorExit:
            print('closed')
    return Response(stream_with_context(gen()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# Connect to device and start pipeline
if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True)

""" key = cv2.waitKey(1)
if key == ord('q'):
    break
elif key == ord('s'):
    if featureTrackerConfig.motionEstimator.type == dai.FeatureTrackerConfig.MotionEstimator.Type.LUCAS_KANADE_OPTICAL_FLOW:
        featureTrackerConfig.motionEstimator.type = dai.FeatureTrackerConfig.MotionEstimator.Type.HW_MOTION_ESTIMATION
        print("Switching to hardware accelerated motion estimation")
    else:
        featureTrackerConfig.motionEstimator.type = dai.FeatureTrackerConfig.MotionEstimator.Type.LUCAS_KANADE_OPTICAL_FLOW
        print("Switching to Lucas-Kanade optical flow")

    cfg = dai.FeatureTrackerConfig()
    cfg.set(featureTrackerConfig)
    inputFeatureTrackerConfigQueue.send(cfg)
"""
# Movenet & Motion Stream Privacy
This project originated out of an idea from the course Human-AI-Interaction Design taught at Cornell University. We use motorized camera blockers to limit what surveillance cameras can capture. These camera blockers are visual to the person under monitoring and help to explain the surveillance status. The first use and trial of the contextually switching blockers were during a Public Interest Fellowship from Cornell Tech with the YAI yetwork.

The work in this repository is a combination of code and libraries from many prior projects. It may be advisable to refer to those documentations directly. 

The repository uses three different python enviornments streaming_manager.py starts the movenet pose recognition running on depthai. The dependencies are listed in the top folder requirements.txt. For motion-detection without pose recogniton, i.e. when in bed, non AI motion detection is used. The environment dependencies are listed in the subfolder. The subfolder physical_camera_interface has two script for controlling the LED ring at the cameras lens, and rotating the camera blockers into position. 

This is the python code for video monitoring as well as calibrating motors. The Node-Red flows that tie individual components together can be fount at: https://github.com/HaukeCornell/WOZ_AI_Camera_Surveillance 

## Sources
- https://github.com/geaxgx/depthai_movenet
- https://github.com/bwsw/rt-motion-detection-opencv-python

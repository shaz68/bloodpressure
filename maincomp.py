# Code for LCD number recognition source https://pyimagesearch.com/2017/02/13/recognizing-digits-with-opencv-and-python/
# Code for COMMS author Rob Poulter February 2024
# Code for camera capture original source Original webcam image capture code from https://stackoverflow.com/questions/34588464/python-how-to-capture-image-from-webcam-on-click-using-opencv
# Additional mod authors Sarah Boyd and Sharon Harrison February 2024

# Program has 3 distinct sections:
# 1. Take a snapshot of the bloodpressure monitor display
# 2. Use OpenCV to recognise numbers
# 3. Pass numbers to VEX IQ
# 4. VEX IQ displays results, lights a LED Touch sensor with specific colour, depending
#    on results.


#vex:disable=repl
import platform
import serial
from random import randint
import cv2
import time
from imutils import contours
import imutils
import numpy as np


# define the dictionary of digit segments so we can identify each digit
DIGITS_LOOKUP = {
    (1, 1, 1, 0, 1, 1, 1): 0,
    (0, 0, 1, 0, 0, 1, 0): 1,
    (1, 0, 1, 1, 1, 0, 1): 2,
    (1, 0, 1, 1, 0, 1, 1): 3,
    (0, 1, 1, 1, 0, 1, 0): 4,
    (1, 1, 0, 1, 0, 1, 1): 5,
    (1, 1, 0, 1, 1, 1, 1): 6,
    (1, 0, 1, 0, 0, 1, 0): 7,
    (1, 1, 1, 1, 1, 1, 1): 8,
    (1, 1, 1, 1, 0, 1, 1): 9,
    (1, 1, 1, 0, 0, 1, 0): 9 # Additional mapping to compensate shade over last reading
}

readings = []
counter = 0


# Capture image from blood pressure monitor by pressing space bar
camera = cv2.VideoCapture(0)
cv2.namedWindow("Reading")
# Set a counter so we can take and save multiple images, if necessary
img_counter = 0
get_image = True

while get_image == True:
    ret, frame = camera.read()
    if not ret:
        print("failed to grab frame")
        break
    cv2.imshow("webcam", frame)

# wait for user to press space bar to take picture. 
# When finished, user presses <ESC> to finish 
    k = cv2.waitKey(1)
    # Check if space bar pressed
    if k%256==32:
        img_name = "image_{}.png".format(img_counter)
        cv2.imwrite(img_name, frame)
        print("{} saved".format(img_name))
        img_counter += 1
    elif k%256==27:
        get_image = False

for i in range(0, img_counter):
    image = cv2.imread("image_{}.png".format(i))
    red_size = cv2.resize(image, (0, 0), fx = 0.5, fy = 0.5)
    new_image = "image_red_{}.png".format(i) 
    cv2.imwrite(new_image, red_size)          

camera.release()
cv2.destroyAllWindows()

# Extract the section of the image with the LCD display in it
img = cv2.imread("image_1.png")
# # Define the coordinates of the top-left corner and the width and height
x, y, w, h = 320,160,110,150
# # Extract the region of interest using array slicing
roi = img[y:y+h, x:x+w]
# Show the extracted ROI
cv2.imwrite("LCDOnly.png",roi)
cv2.waitKey(0)

# Chop into 3 boxes to do three separate recognitions
rows = []
top_roi = roi[5:60,:]
rows.append(top_roi)
mid_roi = roi[61:115,:]
rows.append(mid_roi)
bottom_roi = roi[115:,:]
rows.append(bottom_roi)

for i, roi in enumerate(rows):
    # convert image to grayscale, threshold and then apply a series of morphological
    # operations to cleanup the thresholded image
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    img_blur = cv2.GaussianBlur(gray,(5,5),0)
    thresh = cv2.adaptiveThreshold(img_blur,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,11,2)

    # # # Join the fragmented digit parts
    kernel = np.ones((3,3),np.uint8)
    dilation = cv2.dilate(thresh,kernel,iterations = 1)
    erosion = cv2.erode(dilation,kernel,iterations = 1)
    #cv2.imshow("dilated and eroded image",erosion)
    #cv2.waitKey(0)
    # # find contours in the thresholded image, and put bounding box on the image
    cnts = cv2.findContours(erosion.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)
    #print(f'Number of contours found: {len(cnts)}')
    digitCnts = []
    # # # loop over the digit area candidates
    image_w_bbox = roi.copy()
    height,width = roi.shape[:2]
    print(f"Width: {width}")
    print(f"Height: {height}")
    #image_w_bbox = imutils.rotate_bound(image_w_bbox, 2)
    #print("Printing (x, y, w, h) for each bounding rectangle found in the image...")
    for i,c in enumerate(cnts):
        #print(i)
        # compute the bounding box of the contour
        (x, y, w, h) = cv2.boundingRect(c)
        #print(x, y, w, h)
        # if the contour is sufficiently large, it must be a digit
        if h > 0.75 * height:
            digitCnts.append(c)
            image_w_bbox = cv2.rectangle(image_w_bbox,(x, y),(x+w, y+h),(0, 255, 0),2)
    cv2.imshow("image with bounding boxes",image_w_bbox)
    #cv2.waitKey(0)
    # # # sort the contours from left-to-right
    digitCnts = contours.sort_contours(digitCnts,   method="left-to-right")[0]
    # len(digitCnts) # to check how many digits have been recognized
    digits = []
    # loop over each of the digits
    for c in digitCnts:
        # extract the digit ROI
      (x, y, w, h) = cv2.boundingRect(c)
      if w<0.5*height: # it turns out we can recognize number 1 based on the ROI width
        #print('its a one!')
        digits.append(1)
      else: # for digits othan than the number 1
        roi = erosion[y:y + h, x:x + w]
        # compute the width and height of each of the 7 segments we are going to examine
        (roiH, roiW) = roi.shape
        (dW, dH) = (int(roiW * 0.25), int(roiH * 0.15))
        dHC = int(roiH * 0.05)
        # define the set of 7 segments
        segments = [
          ((0, 0), (w, dH)),    # top
          ((0, 0), (dW, h // 2)),   # top-left
          ((w - dW, 0), (w, h // 2)),   # top-right
          ((0, (h // 2) - dHC) , (w, (h // 2) + dHC)), # center
          ((0, h // 2), (dW, h)),   # bottom-left
          ((w - dW, h // 2), (w, h)),   # bottom-right
          ((0, h - dH), (w, h)) # bottom
        ]
        on = [0] * len(segments)
      # loop over the segments
        for (i, ((xA, yA), (xB, yB))) in enumerate(segments):
            # extract the segment ROI, count the total number of thresholded pixels
            # in the segment, and then compute the area of the segment
          segROI = roi[yA:yB, xA:xB]
          total = cv2.countNonZero(segROI)
          area = (xB - xA) * (yB - yA)
            # if the total number of non-zero pixels is greater than
            # 40% of the area, mark the segment as "on"
          if total / float(area) > 0.4:
            on[i]= 1
          # lookup the digit and draw it on the image
        digit = DIGITS_LOOKUP[tuple(on)]
        digits.append(digit)
    string_num = ''.join(str(d) for d in digits)
    readings.append(string_num)
    print("Here are the digits from left to right...")
    print(digits)

# Pass data to VEX. Make sure main.py is downloaded and running on VEX IQ
# May need to open Device Manager on Windows to check COM port number. 
# Once initialised, this program stays in a loop until <q> pressed

SERIAL_DEVICE_MACOS = "/dev/tty.usbmodem1103"
SERIAL_DEVICE_WIN = "COM7"
SERIAL_DEVICE_LINUX = "/dev/ttyACM1"

SYSTEM = platform.system()  # 'Darwin', 'Linux', 'Windows'
if SYSTEM == "Darwin":
    PORT_NAME = SERIAL_DEVICE_MACOS
elif SYSTEM == "Linux":
    PORT_NAME = SERIAL_DEVICE_LINUX
elif SYSTEM == "Windows":
    PORT_NAME = SERIAL_DEVICE_WIN

serial_port_file = serial.Serial(
    PORT_NAME,
    115200,
    timeout=0,
    write_timeout=0,
    inter_byte_timeout=None,
)     

def send_msg(serial_port, msg):
    try:
        line = msg
        serial_port.write(f"M:{line}:E\n".encode())
        serial_port.flush()
    except:
        pass


def read_serial(serial_port):
    try:
        data = serial_port.read(1024)
        if data:
            print(data.decode(), end='')
    except:
        pass

def get_vals():
    while True:
        # these are used to hold blood pressure values from device
        systolic = readings[0]
        diastolic = readings[1]
        pulse = readings[2]
        
        # sent blood pressure values to the VEX brain
        packet = str(systolic) + "," + str(diastolic) + "," + str(pulse)
        send_msg(serial_port_file, packet)
        print(packet) # this can be removed once you are confident it is working
        time.sleep(5)
        # quit if q pressed on keyboard
        if cv2.waitKey(1) == ord('q'):
            break

get_vals()

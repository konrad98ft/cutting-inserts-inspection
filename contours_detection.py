import cv2 as cv
import numpy as np
import random as rng
import matplotlib.pyplot as plt
import math
import sys
from numpy.core.fromnumeric import shape 
from scipy.optimize import fsolve
from scipy import ndimage
import time
from skimage.filters import threshold_otsu

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from skimage import data
from skimage.filters import threshold_otsu
from skimage.segmentation import clear_border
from skimage.measure import label, regionprops
from skimage.morphology import closing, square
from skimage.color import label2rgb

'''
PC version of the stand_image_processing.py used for testing purposes.
Program uses images from linked directories instead of live camera capture.
'''

# Input images directories
PATH = '\stand_samples_2\\'
PATH2 = '\oswietlacz_pierscieniowy_backlight\\'


PX2MM = 620/4 #R = 4mm R = 170px 
 
def findLinesPoints(roi,direction):   
    pts = []
    searching_msk = 5
    msk_val = (30,30,50,30,30)
    # X direction searching
    if(direction[1] == 1):              
        x_range = (0,roi.shape[0]-searching_msk,1)
        y_range = (0,roi.shape[1]-1,1) 
    if(direction[1] == -1): 
        x_range = (roi.shape[0]-1-searching_msk,0,-1)  
        y_range = (0,roi.shape[1]-1,1)              
    # Y direction searching
    if(direction[0] == 1): 
        x_range = (0,roi.shape[1]-searching_msk,1)
        y_range = (roi.shape[0]-1,0,-1) 
    if(direction[0] == -1):            
        x_range = (roi.shape[1]-1-searching_msk,0,-1)
        y_range = (roi.shape[0]-1,0,-1)  

    drawing = np.zeros((roi.shape[0], roi.shape[1], 3), dtype=np.uint8)
    for y in range(y_range[0],y_range[1],y_range[2]): #y_range
        for x in range(x_range[0],x_range[1],x_range[2]): #x_range
            box = 0
            if(direction[1] != 0):
                for i in range(searching_msk):
                    if(roi[x+i,y] > msk_val[i]): box+=1              
                if(box >= searching_msk-1):
                    xl = x + int(searching_msk/2)      
                    pts.append([y,xl])
                    for j in range(searching_msk): drawing[x+j,y]=(200,0,0)
                    drawing[xl,y]=(0,255,0)
                    break

            if(direction[0] != 0): 
                for i in range(searching_msk):
                    if(roi[y,x+i] > msk_val[i]): box+=1               
                if(box >= searching_msk-1):
                    xl = x + int(searching_msk/2)    
                    pts.append([xl,y])
                    for j in range(searching_msk): drawing[y,x+j]=(200,0,0)
                    drawing[y,xl]=(0,0,255)                    
                    break
    ### Visualization
    '''cv.namedWindow('findLinesPoints', cv.WINDOW_NORMAL)
    cv.imshow('findLinesPoints',drawing)  '''              
    roi = cv.cvtColor(roi,cv.COLOR_GRAY2BGR)
    


    return pts
 
def linesFiltration(roi,direction):
    kernel1 = np.array([[-1,-1,-1,-1,-1,-1,-1],[-1,-1,-1,-1,-1,-1,-1],[2,2,2,2,2,2,2],[4,4,4,4,4,4,4],[2,2,2,2,2,2,2],[-1,-1,-1,-1,-1,-1,-1],[-1,-1,-1,-1,-1,-1,-1]])
    kernel2 = np.array([[-1,-1,2,4,2,-1,-1],[-1,-1,2,4,2,-1,-1],[-1,-1,2,4,2,-1,-1],[-1,-1,2,4,2,-1,-1],[-1,-1,2,4,2,-1,-1]])
   
    if(direction[1]!=0): kernel = kernel1
    if(direction[0]!=0): kernel = kernel2
    
    roi2 = cv.filter2D(roi,-1,kernel)
    
    #Show filter effect
    '''cv.namedWindow('linesFiltration', cv.WINDOW_NORMAL)
    cv.imshow('linesFiltration',roi2) '''
    return roi2

def searchingBox(image, points=(300,650,400,500), direction=(0,1)): 
    ### points = (x1,x2,y1,y2) direction = (x_dir,y_dir) ###

    # Apply ROI
    roi = image.copy()[points[2]:points[3],points[0]:points[1]]
    
    #Treshold
    ret,roi = cv.threshold(roi,80,255,cv.THRESH_TOZERO)
    
    # Show ROI
    '''cv.namedWindow('Searching Box', cv.WINDOW_NORMAL)
    cv.imshow('Searching Box',  roi)
    cv.resizeWindow('Searching Box', points[1]-points[0], points[3]-points[2] )'''

    # Distract various searching directions
    roi = linesFiltration(roi,direction)
    pts = findLinesPoints(roi,direction)
   
    # Break in case of faulty input image
    if(len(pts) < 2):
        print("Any line found")
        sys.exit(1) 

    # Fit line
    vector = np.array(pts)
    vx,vy,x,y = cv.fitLine(vector,cv.DIST_HUBER, 0, 0.01, 0.05) 
    
    # Show ROI and fitted line on the orgnial image  
    x = x + points[0]   # Go back to the global coordinate system
    y = y + points[2]
    line = vx,vy,x,y

    k = 10000
    p1 = (int(x - k*vx), int(y - k * vy))
    p2 = (int(x + k*vx), int(y + k * vy))
    cv.line(image, p1,p2 , (255,255,255), 3, cv.LINE_AA, 0)
    cv.rectangle(image,(points[0],points[2]),(points[1],points[3]),(255,255,255),2)
    '''cv.namedWindow('ROI', cv.WINDOW_NORMAL)
    cv.imshow('ROI',image)
    cv.resizeWindow('ROI',800,600)'''

    return line 
     
def findArcPoint(image,line1,line2):
    # Solving linear equation to find lines crossing point
    vx1,vy1,x1,y1 = line1
    vx2,vy2,x2,y2 = line2
    A = np.array([[vx1, 0, -1,0], [vy1, 0, 0,-1], [0, vx2, -1,0], [0, vy2, 0,-1]], dtype='float')
    B = np.array([-x1,-y1,-x2,-y2], dtype='float')
    R = np.linalg.inv(A).dot(B)
    xs,ys = R[2:]
    vx = vx1 + vx2
    vy = vy1 + vy2
    
    # Find 4 possible arc centres of the cutting insert
    C = [] # coortinates of the 4 possible arc centres
    v = np.array([[vx,vy],[-vx,vy],[-vx,-vy],[vx,-vy]], dtype='float')  #possible direction vectors
    l = math.sqrt(v[0][0]**2 + v[0][1]**2)  #lenght of those vectors
    k = (PX2MM*4)/l #how many vectors is between line crossing point and cutting insert arc centre
    for i in range(len(v)): #all possible configurations
        pom = xs + v[i][0]*k  , ys + v[i][1]*k
        cv.circle(img,(int(xs + v[i][0]*k),int(ys + v[i][1]*k)),1,(255,255,255),4) ### Visualization ###
        C.append(pom)
 
    # Chose ROI with contains cutting insertarc - closest to the centre of the image
    properArc = 99
    min_dist = 9999
    img_cy,img_cx=img.shape[:2]
    for i in range(len(v)):
        dist =    math.sqrt( (C[i][0]-img_cx/2)**2 +  (C[i][1]-img_cy/2)**2 )
        if(  dist < min_dist):
            min_dist = dist
            properArc = i       
    xc,yc=C[properArc] #proper arc centre coordinates

    # Build roi between arc centre(xc,yc) and lines crossing point (xs,ys) in dependece on their location 
    inc = 50 #offset outer boundaries by some offset to avoid cutting the arc
    rx0 = int(xc) if xc < xs else int(xs-inc) 
    ry0 = int(yc) if yc < ys else int(ys-inc)
    rxk = int(xc) if xc > xs else int(xs+inc) 
    ryk = int(yc) if yc > ys else int(ys+inc)
    roi = image.copy()[ry0:ryk,rx0:rxk]
    #print(xc,xs,yc,ys)

    #Rotate roi
    ang =0
    if(xc>xs and yc<ys): ang = 90 
    if(xc>xs and yc>ys): ang = 180 
    if(xc<xs and yc>ys): ang = 270  
    roi = ndimage.rotate(roi, ang)
  
    ### Visualization ###
    cv.circle(img,(int(R[2]),int(R[3])),10,(255,255,255),3) #Lines intersection
    cv.circle(img,(int(xc),int(yc)),1,(255,255,255),3) #Arc centre
    cv.circle(img,(int(xc),int(yc)),int(PX2MM*4/math.sqrt(2)),(255,255,255),1) #Arc radius

    ### Visualization ###
    '''cv.namedWindow('Arc ROI', cv.WINDOW_NORMAL)    
    cv.imshow('Arc ROI', roi)
    cv.resizeWindow('Arc ROI', (rxk-rx0)*3,(ryk-ry0)*3) '''

    # Polar transform and filtration
    try:
        roi = polarTransform(roi,start_point=(0,0),r=(int(PX2MM*0.75),int(PX2MM*3)),theta=90,theta_inc=0.25)
    except:
        roi = roi
    ret,roi2 = cv.threshold(roi,80,255,cv.THRESH_TOZERO)
    roi2 = linesFiltration(roi2,(0,-1))
    pts = findLinesPoints(roi2,(0,-1))
    if(len(pts) < 2):
        print("Any line found")
        sys.exit(1) 
    pts_y = []
    for i in range(len(pts)): pts_y.append(pts[i][1])

    s = srednia(pts_y) 
    m = mediana(pts_y)  
    o = odchylenie(pts_y, s)  
    '''print("Średnia: {:.2f}\nMediana: {:.2f}\nOdchylenie standardowe: {:.2f}".format(s,m,o))
    if(s < 63.5 and s > 59):
        cv.putText(img,'OK',(15,15), cv.FONT_HERSHEY_PLAIN, 1,255,2)
    else:
        cv.putText(img,'N_OK',(15,15), cv.FONT_HERSHEY_PLAIN, 1,255,2)'''
   
    ### Visualization ###
    '''cv.namedWindow('orginal ROI', cv.WINDOW_NORMAL)
    cv.imshow('orginal ROI', roi)
    cv.resizeWindow('orginal ROI', (rxk-rx0)*3,(ryk-ry0)*3)

    cv.namedWindow('binary ROI', cv.WINDOW_NORMAL)
    cv.imshow('binary ROI', roi2)
    cv.resizeWindow('binary ROI', (rxk-rx0)*3,(ryk-ry0)*3) '''
    
def polarTransform(roi,start_point,r,theta,theta_inc):
    drawing = np.zeros((roi.shape[0], roi.shape[1], 3), dtype=np.uint8)
    roi2 = np.zeros((int(r[1]-r[0]),int(theta/theta_inc)+1, 1), dtype=np.uint8)
    theta_range = np.arange(0, theta, theta_inc)

    for alpha in theta_range:
        x0 = int(math.sin(math.radians(alpha))*r[0])
        y0 = int(math.cos(math.radians(alpha))*r[0])
        xk = int(math.sin(math.radians(alpha))*r[1])
        yk = int(math.cos(math.radians(alpha))*r[1])
  
        roid = cv.cvtColor(roi,cv.COLOR_GRAY2BGR)
        #cv.waitKey(1) ### Visualization ###
        for R in range(r[0],r[1]):
            x = int(math.sin(math.radians(alpha))*R)+x0
            y = int(math.cos(math.radians(alpha))*R)+y0
            cv.circle(drawing,(x,y),1,(0,0,255),1)
              
            roi2[R-r[0],int(alpha/theta_inc)] = roi[x,y]

            '''### Visualization ###
            drawing = cv.bitwise_or(drawing, roid)
            cv.namedWindow('polar lines', cv.WINDOW_NORMAL)
            cv.imshow('polar lines', drawing)
            cv.resizeWindow('polar lines',drawing.shape[0]*3,drawing.shape[1]*3)

            cv.namedWindow('polar roi', cv.WINDOW_NORMAL)
            cv.imshow('polar roi', roi2)
            cv.resizeWindow('polar roi',roi2.shape[1]*3,roi2.shape[0]*3)'''
    return roi2  

# Output analyze
def srednia(pts):
    suma = sum(pts)
    return suma / float(len(pts))
def mediana(pts):
    pts.sort()
    if len(pts) % 2 == 0:  
        half = int(len(pts) / 2)
        return float(sum(pts[half - 1:half + 1])) / 2.0
    else: 
        return pts[int(len(pts) / 2)] 
def wariancja(pts, srednia):
    sigma = 0.0
    for ocena in pts:
        sigma += (ocena - srednia)**2
    return sigma / len(pts)
def odchylenie(pts, srednia): 
    w = wariancja(pts, srednia)
    return math.sqrt(w)

def findInsertCentreOtsu(img):
       
    # Prepare image by finding conturs - otsu threshold
    thresh_val = threshold_otsu(img)
    ret,img2 = cv.threshold(img,thresh_val,255,cv.THRESH_TOZERO)

    kernel = np.ones((5, 5), np.uint8)
    edged = cv.erode(img2, kernel) 
    kernel2 = np.ones((9, 9), np.uint8)
    edged = cv.dilate(edged, kernel) 

    # Reject small non-signifficant conturs
    contours, hierarchy = cv.findContours(edged, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    cont2 = []
    for i in range(len(contours)):
        if(cv.contourArea(contours[i])>1000):
            cont2.append(contours[i])

    # Find bounding box        
    minX = 9999
    minY = 9999
    maxX = 0
    maxY = 0
    for c in cont2:
        for p in c:
            if(minX>p[0][0]):minX=p[0][0]
            if(maxX<p[0][0]):maxX=p[0][0]
            if(minY>p[0][1]):minY=p[0][1]
            if(maxY<p[0][1]):maxY=p[0][1]

    XC = int((maxX + minX)/2)
    YC = int((maxY + minY)/2)

    # Centre of the cutting insert
    Xdim = 1100
    Ydim = 650
    
    return XC,YC

def rotateImage(image):

 
    # apply threshold
    thresh = threshold_otsu(image)
    bw = closing(image > thresh, square(3))


    # remove artifacts connected to image border
    cleared = clear_border(bw)


    # label image regions
    label_image = label(cleared)


    printTime("Alt-2")
    image_label_overlay = label2rgb(label_image, image=image, bg_label=0)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.imshow(image_label_overlay)
  
    max_region = regionprops(label_image)[0]
    printTime("Alt-2.2")
    for region in regionprops(label_image):
        # find the largest region
        if region.area >= max_region.area:
            max_region = region
    printTime("Alt-3")
    # draw rectangle around segmented coins
    minr, minc, maxr, maxc = max_region.bbox
    rect = mpatches.Rectangle((minc, minr), maxc - minc, maxr - minr,fill=False, edgecolor='red', linewidth=2)
    ax.add_patch(rect)
    print("Angle:",rect)
    printTime("Alt-4")

    ax.set_axis_off()
    plt.tight_layout()
    plt.show()
    return image

def printTime(str='time'):
    elapsed_time = time.time() - start_time
    print("{}: \t {:.3f}s".format(str,elapsed_time))

def rotate(image):

    
    return image


for img_index in range(0,12):
    # Get an image
    img_path= PATH2 +"0_"+ str(img_index) +'.png'
    img = cv.imread(img_path,-1)
    try:
        img = cv.cvtColor(img, cv.COLOR_BGR2GRAY)    
    except:
        print("Image not found")
        sys.exit(1)

    start_time = time.time()

    # Find centre of the cutting insert
    XC,YC = findInsertCentreOtsu(img)

    # Reshape image for deepL clasification
    Xdim = 1100
    Ydim = 650
    start_point = (XC, YC)
    end_point = (int(XC+Xdim), int(YC+Ydim))
    deepL_img = img.copy()[start_point[1]:end_point[1],start_point[0]:end_point[0]]
    deepL_img = cv.resize(deepL_img, (256,256), interpolation = cv.INTER_AREA)
    printTime("Time-centre")

    '''#Alternative rotate
    size = (int(img.shape[1]/4),int(img.shape[0]/4))
    print(size)
    small = cv.resize(img,  size)
    small = rotateImage(small)
    printTime("Time-alt-rotate")'''

    # Rotate image
    X_offset = 1030
    Y_offset = 530 
    img2 = img.copy()
    roi = img.copy()[XC-X_offset+350:XC+X_offset-350,YC-Y_offset-150:YC-Y_offset+150]  
    line1 = searchingBox(img,(XC-X_offset+350,XC+X_offset-350,YC-Y_offset-150,YC-Y_offset+150),(0,1))
    printTime("Time-rotate 1")
    vx1, vy1, x2, y2 = line1
    rot_ang = -math.atan2(y2 - vy1, x2 - vx1) if vy1  < 0 else math.atan2(y2 - vy1, x2 - vx1) 
    printTime("Time-rotate 1.1")
    img = ndimage.rotate(img2.copy(), rot_ang, reshape=False)
    printTime("Time-rotate 2")

    # Find lines
    img2 = img.copy()  
    line1 = searchingBox(img,(XC-X_offset+350,XC+X_offset-350,YC+Y_offset-150,YC+Y_offset+150),(0,-1))
    line2 = searchingBox(img,(XC+X_offset-150,XC+X_offset+150,YC-Y_offset+300,YC+Y_offset-300),(-1,0))  
    printTime("Time-lines")

    # Check image
    findArcPoint(img2,line1,line2)
    printTime("Time-all")  

   

    # Show effects
    cv.namedWindow(str(img_index), cv.WINDOW_FREERATIO)
    cv.imshow(str(img_index), img)
    cv.resizeWindow(str(img_index), int(img.shape[1]/2),int(img.shape[0]/2)) 

    cv.namedWindow("deepL_img", cv.WINDOW_FREERATIO)
    cv.imshow("deepL_img", deepL_img)
    cv.resizeWindow("deepL_img", int(deepL_img.shape[1]),int(deepL_img.shape[0])) 
    cv.waitKey(0)
    cv.destroyAllWindows()


'''
searchingBox(img,(300,650,100,200),(0,1))
cv.waitKey(0)
searchingBox(img,(150,220,240,350),(1,0))
cv.waitKey(0) 
'''





cv.waitKey(0)
cv.destroyAllWindows()
 



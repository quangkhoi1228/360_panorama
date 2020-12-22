from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.core.files.storage import FileSystemStorage
import cv2
import numpy as np
import matplotlib.pyplot as plt
from skimage import io
import random
from tensorflow.keras.models import load_model
from PIL import Image
import os
import sys

from django.core.files.base import ContentFile
from django.conf import settings

from PIL import Image, ImageTk
import imutils
import argparse


os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'


def uploadFile(request):
    context = {}
    context['url'] = []
    if request.method == 'POST':
        for uploaded_file in request.FILES.getlist('image'):
            # uploaded_file = request.FILES
            fs = FileSystemStorage()
            name = fs.save(uploaded_file.name, uploaded_file)
            context['url'].append(fs.url(name))
    return context


def imreadx(url):
    img = io.imread(url)
    outimg = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    return outimg


def imshowx(img, title='B2DL'):
    fig_size = plt.rcParams["figure.figsize"]
    fig_size[0] = 12
    fig_size[1] = 4
    plt.rcParams["figure.figsize"] = fig_size

    plt.axis('off')
    plt.title(title)
    plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    plt.show()


def imshowgrayx(img, title='BD2L'):
    plt.axis('off')
    plt.title(title)
    plt.imshow(img, cmap=plt.get_cmap('gray'))
    plt.show()


def cropAndDetectTrafficSign(context):

    try:
        currentPythonFilePath = os.getcwd()
        # modelUrl = currentPythonFilePath+'/static/model/model.h5'
        modelUrl = currentPythonFilePath+'/static/model/model.h5'

        saveDetectImageUrl = currentPythonFilePath+'/static/image/'
        url = currentPythonFilePath + context['url']

        imageType = url.split('.')[1]

        img = imreadx(url)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask_r1 = cv2.inRange(hsv, (0, 100, 100), (10, 255, 255))
        mask_r2 = cv2.inRange(hsv, (160, 100, 100), (180, 255, 255))
        mask_r = cv2.bitwise_or(mask_r1, mask_r2)
        target = cv2.bitwise_and(img, img, mask=mask_r)
        gblur = cv2.GaussianBlur(mask_r, (9, 9), 0)
        edge_img = cv2.Canny(gblur, 30, 150)

        cv2.imwrite(saveDetectImageUrl + 'original.'+imageType, img)
        cv2.imwrite(saveDetectImageUrl + 'markrange1.'+imageType, mask_r1)
        cv2.imwrite(saveDetectImageUrl + 'markrange2.'+imageType, mask_r2)
        cv2.imwrite(saveDetectImageUrl + 'maskforredregion.'+imageType, mask_r)
        cv2.imwrite(saveDetectImageUrl + 'maskforredrigon.'+imageType, target)
        cv2.imwrite(saveDetectImageUrl + 'edgemap.'+imageType, edge_img)

        img2 = img.copy()
        itmp, cnts, hierarchy = cv2.findContours(
            edge_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(img2, cnts, -1, (0, 255, 0), 2)

        cv2.imwrite(saveDetectImageUrl +
                    'contournorestriction.'+imageType, img2)

        img2 = img.copy()
        try:
            for cnt in cnts:
                area = cv2.contourArea(cnt)
                if(area < 1000):
                    continue
                ellipse = cv2.fitEllipse(cnt)
                cv2.ellipse(img2, ellipse, (0, 255, 0), 2)
                x, y, w, h = cv2.boundingRect(cnt)
                a, b, c, d = x, y, w, h
                cv2.rectangle(img2, (x, y), (x+w, y+h), (0, 255, 0), 3)

            cv2.imwrite(saveDetectImageUrl +
                        'contourrestrictedforlargeregion.'+imageType, img2)

            crop = img2[b:b+d, a:a+c]

            cv2.imwrite(saveDetectImageUrl + 'cropimage.'+imageType, crop)

            model = load_model(modelUrl)
            data = []
            image_from_array = Image.fromarray(crop, 'RGB')
         
            crop = image_from_array.resize((30, 30))

            data.append(np.array(crop))

            X_test = np.array(data)

            X_test = X_test.astype('float32')/255

            prediction = model.predict_classes(X_test)

            return prediction
        except:
            print("cannot border box")
            os.remove(saveDetectImageUrl + 'cropimage.'+imageType)
            cv2.imwrite(saveDetectImageUrl + 'cropimage.'+imageType, img)
            model = load_model(modelUrl)
            data = []
            image_from_array = Image.fromarray(img, 'RGB')
            img = image_from_array.resize((30, 30))
            data.append(np.array(img))
            X_test = np.array(data)
            X_test = X_test.astype('float32')/255
            prediction = model.predict_classes(X_test)
            return prediction
    except:
        print("Bug when model predict")
        return [10000]


# def detectTrafficSign(request):
#     context = uploadFile(request)
#     prediction = cropAndDetectTrafficSign(context)
#     context['traffictrainid'] = prediction[0]
#     return context

def stitching(context):
    current_path = os.getcwd()
    #get all image input 
    image_list = []
    for image_url in context['url']:
        image = cv2.imread(current_path +  image_url)
        image_list.append(image)
    # create oject for sticher
    stitcher = cv2.createStitcher() if imutils.is_cv3() else cv2.Stitcher_create()
    (status, stitched) = stitcher.stitch(image_list)
    if status == 0:
        # crop out the image with 5 pixcel
        stitched = cv2.copyMakeBorder(stitched, 5, 5, 5, 5,
                                        cv2.BORDER_CONSTANT, (0, 0, 0))
        cv2.imwrite(settings.MEDIA_ROOT+ "/stitched_copyMakeBorder.jpg", stitched)
        context['stitched_copyMakeBorder'] = settings.MEDIA_URL+'stitched_copyMakeBorder.jpg'
        # convert to grayscale and threshold it
        gray = cv2.cvtColor(stitched, cv2.COLOR_BGR2GRAY)
        cv2.imwrite(settings.MEDIA_ROOT+ "/stitched_gray.jpg", gray)
        context['stitched_gray'] = settings.MEDIA_URL+'stitched_gray.jpg'

        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY)[1]
        cv2.imwrite(settings.MEDIA_ROOT+ "/stitched_thresh.jpg", thresh)
        context['stitched_thresh'] = settings.MEDIA_URL+'stitched_thresh.jpg'


        # the stitched image
        cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
                                cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        c = max(cnts, key=cv2.contourArea)

        # rectangular bounding box of the stitched image region
        mask = np.zeros(thresh.shape, dtype="uint8")
        cv2.imwrite(settings.MEDIA_ROOT+ "/stitched_mask.jpg", mask)
        context['stitched_mask'] = settings.MEDIA_URL+'stitched_mask.jpg'


        (x, y, w, h) = cv2.boundingRect(c)
        rectangle = cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)
        cv2.imwrite(settings.MEDIA_ROOT+ "/stitched_rectangle.jpg", rectangle)
        context['stitched_rectangle'] = settings.MEDIA_URL+'stitched_rectangle.jpg'
    # create two copies of the mask: one to serve as our actual
        minRect = mask.copy()
        sub = mask.copy()

        while cv2.countNonZero(sub) > 0:
            # erode the minimum rectangular mask and then subtract
            # the thresholded image from the minimum rectangular mask
            minRect = cv2.erode(minRect, None)
            sub = cv2.subtract(minRect, thresh)

        cnts = cv2.findContours(minRect.copy(), cv2.RETR_EXTERNAL,
                                cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        c = max(cnts, key=cv2.contourArea)
        (x, y, w, h) = cv2.boundingRect(c)

        # stitched image
        stitched = stitched[y:y + h, x:x + w]

        # write output to disk
        cv2.imwrite(settings.MEDIA_ROOT+ "/output.jpg", stitched)
        context['output'] = settings.MEDIA_URL+'output.jpg'
        context['status'] = True

# Not stitching
    else:
        print("Image stitching failed ")
        context['status'] = False
    return context


def detectTrafficSign(request):
    context = uploadFile(request)
    context = stitching(context)
    context['context'] = context
    return context

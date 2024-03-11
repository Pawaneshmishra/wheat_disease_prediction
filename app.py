from flask import Flask, render_template, request
import tensorflow as tf
from tensorflow.keras.models import load_model
import os
import cv2
import numpy as np
from geopy.distance import geodesic
from PIL import Image
import piexif

app = Flask(__name__)

model = load_model('wheatDiseaseModel.h5')
klass_dir = 'testCDD'
img_size = 64

label_mapping = {
    (0, 0, 1, 0): "Crown root rot",
    (0, 0, 0, 1): "Healthy",
    (1, 0, 0, 0): "Leaf rust",
    (0, 1, 0, 0): "Loose smut"
}

def calculate_distance(coord1, coord2):
    return geodesic(coord1, coord2).meters

def get_gps_info(exif_dict):
    gps_info = exif_dict.get('GPS')
    
    if gps_info:
        latitude_data = gps_info.get(2)  # GPSLatitude tag
        longitude_data = gps_info.get(4)  # GPSLongitude tag

        if latitude_data and longitude_data:
            latitude = latitude_data[0][0] / latitude_data[0][1] + latitude_data[1][0] / latitude_data[1][1] / 60 + latitude_data[2][0] / latitude_data[2][1] / 3600
            longitude = longitude_data[0][0] / longitude_data[0][1] + longitude_data[1][0] / longitude_data[1][1] / 60 + longitude_data[2][0] / longitude_data[2][1] / 3600
            return latitude, longitude
    return None, None

def process_images(images_to_be_classified):
    if len(images_to_be_classified) != 2:
        return None, "Please upload exactly 2 images."

    resized_images = []
    for image_name in images_to_be_classified:
        image_path = os.path.join(klass_dir, image_name)
        image = cv2.imread(image_path)
        resized_image = cv2.resize(image, (img_size, img_size))
        resized_images.append(resized_image)

    resized_images = np.array(resized_images)
    resized_images = resized_images / 255.0

    predictions = model.predict(resized_images)

    results = []
    for i in range(len(images_to_be_classified)):
        image_name = images_to_be_classified[i]
        prediction = predictions[i]
        rounded_prediction = tuple(np.round(prediction).astype(int))
        label = label_mapping.get(rounded_prediction, "Unknown")
        results.append({"image_name": image_name, "prediction": label})

    # Get GPS information from Exif metadata
    gps_coords = []
    for image_name in images_to_be_classified:
        image_path = os.path.join(klass_dir, image_name)
        im = Image.open(image_path)
        exif_dict = piexif.load(im.info.get('exif'))
        lat, lon = get_gps_info(exif_dict)
        if lat is not None and lon is not None:
            gps_coords.append((lat, lon))
        else:
            return None, "GPS information not found in one or both photos."

    # Calculate distance between GPS coordinates
    distance = calculate_distance(gps_coords[0], gps_coords[1])

    results.append({"distance": distance})

    return results, None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file1 = request.files['file1']
        file2 = request.files['file2']
        
        filenames = [file1.filename, file2.filename]
        
        for file in [file1, file2]:
            filename = file.filename
            file.save(os.path.join(klass_dir, filename))

        results, error = process_images(filenames)
        if results is not None:
            return render_template('index.html', results=results)
        else:
            return render_template('index.html', error=error)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
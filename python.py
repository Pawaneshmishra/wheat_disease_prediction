# from flask import Flask, request, jsonify
# from tensorflow.keras.models import load_model
# import os
# import cv2
# import numpy as np
# from geopy.distance import geodesic
# from PIL import Image
# import piexif

# app = Flask(__name__)

# model = load_model('wheatDiseaseModel.h5')
# klass_dir = 'testCDD'
# img_size = 64

# label_mapping = {
#     (0, 0, 1, 0): "Crown root rot",
#     (0, 0, 0, 1): "Healthy",
#     (1, 0, 0, 0): "Leaf rust",
#     (0, 1, 0, 0): "Loose smut"
# }

# def calculate_distance(coord1, coord2):
#     return geodesic(coord1, coord2).meters

# def get_gps_info(exif_dict):
#     gps_info = exif_dict.get('GPS')

#     if gps_info:
#         latitude_data = gps_info.get(2)  # GPSLatitude tag
#         longitude_data = gps_info.get(4)  # GPSLongitude tag

#         if latitude_data and longitude_data:
#             latitude = latitude_data[0][0] / latitude_data[0][1] + latitude_data[1][0] / latitude_data[1][1] / 60 + latitude_data[2][0] / latitude_data[2][1] / 3600
#             longitude = longitude_data[0][0] / longitude_data[0][1] + longitude_data[1][0] / longitude_data[1][1] / 60 + longitude_data[2][0] / longitude_data[2][1] / 3600
#             return latitude, longitude
#         else:
#             return None, None
#     else:
#         return None, None


# @app.route('/classify', methods=['POST'])
# def classify_images():
#     try:
#         file1 = request.files['file1']
#         file2 = request.files['file2']

#         filenames = [file1.filename, file2.filename]
#         image_paths = []

#         for file in [file1, file2]:
#             filename = file.filename
#             file.save(os.path.join(klass_dir, filename))
#             image_paths.append(os.path.join(klass_dir, filename))

#         resized_images = []
#         for image_path in image_paths:
#             image = cv2.imread(image_path)
#             resized_image = cv2.resize(image, (img_size, img_size))
#             resized_images.append(resized_image)

#         resized_images = np.array(resized_images)
#         resized_images = resized_images / 255.0

#         predictions = model.predict(resized_images)

#         results = []
#         for i in range(len(image_paths)):
#             image_name = os.path.basename(image_paths[i])
#             prediction = predictions[i]
#             rounded_prediction = tuple(np.round(prediction).astype(int))
#             label = label_mapping.get(rounded_prediction, "Unknown")
#             results.append({"image_name": image_name, "prediction": label})

#         # Get GPS information from Exif metadata
#         gps_coords = []
#         for image_path in image_paths:
#             im = Image.open(image_path)
#             exif_dict = piexif.load(im.info.get('exif'))
#             lat, lon = get_gps_info(exif_dict)
#             if lat is not None and lon is not None:
#                 gps_coords.append((lat, lon))
#             else:
#                 return jsonify({"error": "GPS information not found in one or both photos."})

#         # Calculate distance between GPS coordinates
#         distance = calculate_distance(gps_coords[0], gps_coords[1])

#         results.append({"distance": distance})

#         return jsonify({"results": results, "error": None})

#     except Exception as e:
#         return jsonify({"results": None, "error": str(e)})

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000, debug=True)


from flask import Flask, request, jsonify
from tensorflow.keras.models import load_model
import os
import cv2
import numpy as np
from geopy.distance import geodesic
from PIL import Image
import piexif
from pprint import pprint

app = Flask(__name__)

model = load_model('wheatDiseaseModel.h5')
klass_dir = 'testCDD'
img_size = 64

def calculate_distance(coord1, coord2):
    return geodesic(coord1, coord2).meters

def get_gps_info(exif_dict):
    gps_info = exif_dict.get('GPS')

    if gps_info:
        latitude_data = gps_info.get(2)  # GPSLatitude tag
        longitude_data = gps_info.get(4)  # GPSLongitude tag
        
        print(latitude_data, longitude_data) #debug
        
        if latitude_data and longitude_data:
            latitude = latitude_data[0][0] / latitude_data[0][1] + latitude_data[1][0] / latitude_data[1][1] / 60 + latitude_data[2][0] / latitude_data[2][1] / 3600
            longitude = longitude_data[0][0] / longitude_data[0][1] + longitude_data[1][0] / longitude_data[1][1] / 60 + longitude_data[2][0] / longitude_data[2][1] / 3600
            return latitude, longitude
    return None, None

@app.route('/classify', methods=['POST'])
def classify_images():
    try:
        file1 = request.files['file1']
        file2 = request.files['file2']
        filenames = [file1.filename, file2.filename]
        image_paths = []

        for file in [file1, file2]:
            filename = file.filename
            file.save(os.path.join(klass_dir, filename))
            image_paths.append(os.path.join(klass_dir, filename))
            

        print(image_paths) #debug

        gps_coords = []
        for image_path in image_paths:
            im = Image.open(image_path)
            # print(im.info.get('exif'))
            exif_dict = piexif.load(im.info.get('exif'))
            pprint(exif_dict)

            lat, lon = get_gps_info(exif_dict)

            print(lat, lon) #debug

            if lat is not None and lon is not None:
                gps_coords.append({"latitude": lat, "longitude": lon})
            else:
                return jsonify({"error": "GPS information not found in one or both photos."})

        return jsonify({"results": gps_coords, "error": None})

    except Exception as e:
        return jsonify({"results": None, "error": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
from geopy.distance import geodesic
from PIL import Image
import piexif

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

def main():
    # Replace these filenames with the actual file paths of your photos
    filename1 = r"testCDD\wheat-rusts.webp"
    filename2 = r"testCDD\a.jpg"

    im1 = Image.open(filename1)
    im2 = Image.open(filename2)

    exif_dict1 = piexif.load(im1.info.get('exif'))
    exif_dict2 = piexif.load(im2.info.get('exif'))

    # Get GPS information from Exif metadata
    lat1, lon1 = get_gps_info(exif_dict1)
    lat2, lon2 = get_gps_info(exif_dict2)

    if lat1 is not None and lon1 is not None and lat2 is not None and lon2 is not None:
        # Calculate distance between GPS coordinates
        distance = calculate_distance((lat1, lon1), (lat2, lon2))

        print(f"Distance between the two photos: {distance:.2f} meters")

        # Check if the distance is greater than or equal to 103 meters
        if distance >= 103:
            print("Different Field")
        else:
            print("Same Field")
    else:
        print("GPS information not found in one or both photos.")

if __name__ == '__main__':
    main()

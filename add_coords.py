import piexif

file_path=r"testCDD\a.jpg"

try:
    with open(file_path, "rb") as image_file:
        exif_data = image_file.read()

    exif_dict = piexif.load(exif_data)

except:
    exif_dict = {"0th":{}, "Exif":{}, "GPS":{}, "1st":{}}

exif_dict["GPS"] = {
    # piexif.GPSIFD.GPSLatitude: "N",
    piexif.GPSIFD.GPSLatitude: ((13, 1), (0, 1), (int(26.2641*10000), 10000)),
    # piexif.GPSIFD.GPSLongitudeRef: "E",
    piexif.GPSIFD.GPSLongitude: ((74, 1), (47, 1), (int(53.8111*10000), 10000)),
}

exif_bytes = piexif.dump(exif_dict)

with open(file_path, "rb+") as image_file:
    image_file.seek(0)
    piexif.insert(exif_bytes, file_path)

image_file.close()
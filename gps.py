from pprint import pprint
from PIL import Image
import piexif

codec = 'ISO-8859-1'  # or latin-1

def exif_to_tag(exif_dict):
    exif_tag_dict = {}

    # Check if 'thumbnail' exists in exif_dict and is not None
    if 'thumbnail' in exif_dict and exif_dict['thumbnail'] is not None:
        thumbnail = exif_dict.pop('thumbnail')
        exif_tag_dict['thumbnail'] = thumbnail.decode(codec)
    else:
        exif_tag_dict['thumbnail'] = None  # Handle the case when thumbnail is None

    for ifd in exif_dict:
        exif_tag_dict[ifd] = {}

        # Check if exif_dict[ifd] is not None before iterating over it
        if exif_dict[ifd] is not None:
            for tag in exif_dict[ifd]:
                try:
                    # Check if the element is not None before attempting to decode
                    element = exif_dict[ifd][tag].decode(codec) if exif_dict[ifd][tag] is not None else None
                except AttributeError:
                    element = exif_dict[ifd][tag]

                exif_tag_dict[ifd][piexif.TAGS[ifd][tag]["name"]] = element

    return exif_tag_dict


def main():
    filename = r"D:\code\minor\wheat-disease-detection\testCDD\a.jpg"  # obviously one of your own pictures
    im = Image.open(filename)

    exif_data = im.info.get('exif')
    if exif_data:
        exif_dict = piexif.load(exif_data)
        exif_dict = exif_to_tag(exif_dict)
        pprint(exif_dict['GPS'])
    else:
        print("No Exif data found for the image.")

if __name__ == '__main__':
    main()

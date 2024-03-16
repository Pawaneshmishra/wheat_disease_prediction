from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mongoengine import MongoEngine
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from geopy.distance import geodesic
import os
from PIL import Image
import piexif
from tensorflow.keras.models import load_model
from json import JSONEncoder
import cv2
import numpy as np

app = Flask(__name__)
app.config['MONGODB_SETTINGS'] = {
    'db': 'crop',
    'host': 'mongodb+srv://admin:tejkabetichod@cluster0.6lymnfb.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0',
}
app.config['SECRET_KEY'] = 'mcbrbmc'
db = MongoEngine(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(db.Document, UserMixin):
    username = db.StringField(max_length=50, unique=True, required=True)
    email = db.EmailField(unique=True, required=True)
    password_hash = db.StringField(required=True)
    latitude = db.FloatField()
    longitude = db.FloatField()
    eligible_for_insurance = db.BooleanField(default=False)
    role = db.StringField(default='USER')

@login_manager.user_loader
def load_user(user_id):
    return User.objects(id=user_id).first()

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/admin')
@login_required
def admin():
    if current_user.role != 'ADMIN':
        return redirect(url_for('home'))  # Redirect unauthorized users to the homepage

    # Query all users from the database
    users = User.objects.all()

    return render_template('admin.html', users=users)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        # Get GPS coordinates using HTML5 Geolocation API
        latitude, longitude = float(request.form['latitude']), float(request.form['longitude'])


        # Store user information in the database
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password_hash=hashed_password, latitude=latitude, longitude=longitude)
        new_user.save()

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.objects(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('result'))
    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Load the trained TensorFlow model for disease prediction
model = load_model('wheatDiseaseModel.h5')
img_size = 64

@app.route('/result', methods=['GET', 'POST'])
@login_required
def result():
    print("User's eligibility for insurance:", current_user.eligible_for_insurance)

    if request.method == 'POST' and 'cropImage' in request.files:
        # Get the uploaded image
        crop_image = request.files['cropImage']

        # Get the GPS coordinates from the image's metadata
        crop_image_data = crop_image.read()
        exif_dict = piexif.load(crop_image_data)
        gps_info = exif_dict.get('GPS')
        if gps_info:
            latitude_data = gps_info.get(2)  # GPSLatitude tag
            longitude_data = gps_info.get(4)  # GPSLongitude tag
            if latitude_data and longitude_data:
                latitude = latitude_data[0][0] / latitude_data[0][1] + latitude_data[1][0] / latitude_data[1][1] / 60 + latitude_data[2][0] / latitude_data[2][1] / 3600
                longitude = longitude_data[0][0] / longitude_data[0][1] + longitude_data[1][0] / longitude_data[1][1] / 60 + longitude_data[2][0] / longitude_data[2][1] / 3600
            else:
                return render_template('result.html', error='GPS information not found in the uploaded image.')

            # Load and preprocess the image for prediction
            image = cv2.imdecode(np.fromstring(crop_image_data, np.uint8), cv2.IMREAD_COLOR)
            resized_image = cv2.resize(image, (img_size, img_size))
            resized_image = resized_image / 255.0
            resized_image = np.expand_dims(resized_image, axis=0)

            # Predict disease using the loaded model
            prediction = model.predict(resized_image)
            # Perform analysis based on the prediction
            rounded_prediction = np.round(prediction).astype(int)
            print(rounded_prediction)
            is_healthy = rounded_prediction[0][1] == 0  # Check if the prediction indicates the crop is healthy

            # Check distance from the original location during user registration
            user_location = (current_user.latitude, current_user.longitude)
            crop_location = (latitude, longitude)
            distance = geodesic(user_location, crop_location).meters
            is_within_distance = distance <= 103  # Check if the crop is within 103 meters from the original location
            
            if is_within_distance and not is_healthy:
            # If the crop is diseased and within 103 meters, update the user's insurance eligibility in the database
                current_user.eligible_for_insurance = True
                current_user.save()
            else:
                current_user.eligible_for_insurance = False
                current_user.save()
            return render_template('result.html', is_healthy=is_healthy, is_within_distance=is_within_distance, distance=distance)
        else:
            return render_template('result.html', error='GPS metadata not found in the uploaded image.')
    return render_template('result.html', error='Please upload an image.')

@app.route('/claim_insurance', methods=['GET','POST'])
@login_required
def claim_insurance():
    # Logic for insurance claim processing
    if current_user.eligible_for_insurance:
        # Logic for insurance claim processing
        # Redirect to the appropriate page after processing the claim
        flash('Insurance claim processed successfully!')
        return redirect(url_for('claim_insurance'))  # Redirect to the homepage or any other page
    else:
        flash('You are not eligible for insurance.')
        return redirect(url_for('claim_insurance'))  # Redirect to the result page


if __name__ == '__main__':
    app.run(debug=True)
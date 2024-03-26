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
from mongoengine import Document, fields

app = Flask(__name__)
app.config['MONGODB_SETTINGS'] = {
    'db': '',
    'host': '',
}
app.config['SECRET_KEY'] = 'mcbrbmc'
db = MongoEngine(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Define the InsuranceSettings model
class InsuranceSettings(db.Document):
    insurance_amount = db.DecimalField(required=True)

class User(db.Document, UserMixin):
    username = db.StringField(max_length=50, unique=True, required=True)
    email = db.EmailField(unique=True, required=True)
    password_hash = db.StringField(required=True)
    latitude = db.FloatField()
    longitude = db.FloatField()
    eligible_for_insurance = db.BooleanField(default=False)
    role = db.StringField(default='USER')
    insurance_approved = db.BooleanField(default=False)
    applied_for_insurance = db.BooleanField(default=False)

class InsuranceClaim(Document):
    user_id = fields.ReferenceField(User, required=True)
    name = fields.StringField(required=True)
    phone = fields.StringField(required=True)
    address = fields.StringField(required=True)
    amount_insured_per_quintal = fields.DecimalField(required=True)
    is_approved = fields.BooleanField(default=False)

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

    return render_template('admin.html')

@app.route('/details')
@login_required
def details():
    if current_user.role != 'ADMIN':
        return redirect(url_for('home'))  # Redirect unauthorized users to the homepage

    # Query all users from the database
    users = User.objects.all()

    return render_template('user_details.html', users=users)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        # Get GPS coordinates using HTML5 Geolocation API
        if request.form['latitude'] == '' or request.form['longitude'] == '':
            print('user rejected location sharing')
            return redirect(url_for('register'))
        
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
    if current_user.role == 'ADMIN':
        return redirect(url_for('admin'))
    
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
            
            # rounded_prediction = np.round(prediction).astype(int)
            label_mapping = {
                (0, 0, 1, 0): "Crown root rot",
                (0, 0, 0, 1): "Healthy",
                (1, 0, 0, 0): "Leaf rust",
                (0, 1, 0, 0): "Loose smut"
            }
            rounded_prediction = tuple(np.round(prediction).flatten().astype(int))
            label = label_mapping.get(rounded_prediction, "Unknown")
            # print(label)
            # print(rounded_prediction)
            is_healthy = label == 'Healthy'  # Check if the prediction indicates the crop is healthy

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


@app.route('/admin/insurance_amount', methods=['GET', 'POST'])
@login_required
def insurance_amount():
    if current_user.role != 'ADMIN':
        return redirect(url_for('home'))  # Redirect unauthorized users to the homepage

    # Logic for handling the insurance amount decision form submission
    if request.method == 'POST':
        # Process form submission
        insurance_amount_value = request.form.get('insurance_amount')

        # Check if the InsuranceSettings document exists, if not, create it
        settings = InsuranceSettings.objects.first()
        if not settings:
            settings = InsuranceSettings()

        # Update the insurance amount and save it to the database
        settings.insurance_amount = insurance_amount_value
        settings.save()

        flash('Insurance amount decision saved successfully!')

    # Fetch the current insurance amount from the database
    current_insurance_amount = InsuranceSettings.objects.first().insurance_amount if InsuranceSettings.objects.first() else None

    return render_template('insurance_amount.html', current_insurance_amount=current_insurance_amount)

# Route for insurance claim page
@app.route('/insurance_claim', methods=['GET', 'POST'])
@login_required
def insurance_claim():
    insurance_settings = InsuranceSettings.objects.first()
    if request.method == 'POST':
        if current_user.role == 'ADMIN':
            flash('Admins cannot apply for insurance.')
            return redirect(url_for('index'))

        # User is applying for insurance
        current_user.applied_for_insurance = True
        current_user.save()
        flash('Your insurance application has been submitted for review.')
        return redirect(url_for('result'))

    # GET request - Display insurance application form for users
    if current_user.role == 'ADMIN':
        # Admins see a list of insurance applications
        users = User.objects(applied_for_insurance=True)
        return render_template('admin_panel.html', users=users, is_admin=True)
    else:
        # Users see a form to apply for insurance
        return render_template('insurance_claim.html', is_admin=False, insurance_settings=insurance_settings)

# Insurance Approval Route (for admins)
@app.route('/approve_insurance/<user_id>')
@login_required
def approve_insurance(user_id):
    if current_user.role == 'ADMIN':
        user = User.objects(id=user_id).first()
        if user:
            user.insurance_approved = True
            user.save()
            flash('Insurance request approved successfully for user {}.'.format(user.username))
        else:
            flash('User not found.')
    else:
        flash('You do not have permission to approve insurance requests.')
    return redirect(url_for('insurance_claim'))


if __name__ == '__main__':
    app.run(debug=True)

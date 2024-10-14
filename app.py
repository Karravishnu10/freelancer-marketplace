from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.security import generate_password_hash

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this to a real secret key in production
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(60), nullable=False)

@app.route('/')
def index():
    return render_template('register.html')


@app.route('/register', methods=['POST'])
def register():
    email = request.form['email']
    name = request.form['name']
    password = request.form['password']
    hashed_password = generate_password_hash(password)

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash('Email already registered')
        return redirect(url_for('register'))

    new_user = User(email=email, name=name, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return redirect('login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id  # Create a session for the logged-in user
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('home.html')

@app.route('/freelancerSearch', methods=['GET', 'POST'])
def freelancer_search():
    if request.method == 'POST':
        # Process search parameters
        search_query = request.form.get('search')
        skills = request.form.get('skills')
        min_rating = request.form.get('min-rating')
        max_rate = request.form.get('max-rate')
        # Search database for freelancers matching the criteria
        # Assume a function `search_freelancers` which queries your database
        freelancers = search_freelancers(search_query, skills, min_rating, max_rate)
        return render_template('findfreelancers.html', freelancers=freelancers)
    return render_template('findfreelancers.html', freelancers=[])


@app.route('/jobListings', methods=['GET', 'POST'])
def job_listings():
    if request.method == 'POST':
        # Handle search logic here
        pass
    # Assume you fetch jobs from your database or external source
    jobs = [{"title": "Mobile App Development", "description": "Require a content writer...", "price": 572},
            {"title": "Content Writing", "description": "Develop a mobile application...", "price": 384}]
    return render_template('jobListings.html', jobs=jobs)

@app.route('/createJobListings', methods=['GET', 'POST'])
def create_job_listing():
    if request.method == 'POST':
        # Extract form data
        job_title = request.form['job_title']
        project_description = request.form['project_description']
        budget = request.form['budget']
        project_duration = request.form.get('project_duration')  # Optional field
        experience_level = request.form.get('experience_level')  # Optional field
        skills = request.form['skills']

        # Here, insert logic to save this data to your database or another data store

        # Redirect to the job listings page or somewhere appropriate after saving
        return redirect('jobListings')

    # If GET, just render the form page
    return render_template('createJobListings.html')

@app.route('/messaging')
def messaging():
    return render_template('messaging.html')

@app.route('/contractManagement')
def contract_management():
    # You would fetch contract data from your database here
    return render_template('contractManagement.html')

@app.route('/create-contract', methods=['GET', 'POST'])
def create_contract():
    if request.method == 'POST':
        # Process the form data to create a new contract
        return redirect(url_for('contract_management'))
    return render_template('create_contract.html')  # Render the form to create a new contract


if __name__ == '__main__':
    app.run(debug=True)

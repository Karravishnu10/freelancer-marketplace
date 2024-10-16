from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from alembic import op
import sqlalchemy as sa

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db?timeout=30'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this to a real secret key in production
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(60), nullable=False)
    minimum_rate = db.Column(db.Float, nullable=True)
    skills = db.Column(db.String(500), nullable=True)
    jobs = db.relationship('Job', backref='author', lazy=True)


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f'<Category {self.name}>'

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    budget = db.Column(db.String(120), nullable=False)
    duration = db.Column(db.String(120))
    experience_level = db.Column(db.String(120))
    skills = db.Column(db.String(120))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    category = db.relationship('Category', backref='jobs')
    employer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)



def add_categories():
    categories = ['Technology', 'Design', 'Content Writing', 'Marketing', 'Sales', 'Customer Service']
    with app.app_context():
        for name in categories:
            if not Category.query.filter_by(name=name).first():  # Check if category already exists
                category = Category(name=name)
                db.session.add(category)
        db.session.commit()

class Contract(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    terms = db.Column(db.Text)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    status = db.Column(db.String(50))
    
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'))
    job = db.relationship('Job', backref=db.backref('contracts', lazy=True))

    freelancer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    freelancer = db.relationship('User', foreign_keys=[freelancer_id], backref=db.backref('freelance_contracts', lazy=True))

    employer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    employer = db.relationship('User', foreign_keys=[employer_id], backref=db.backref('employer_contracts', lazy=True))




@app.route('/')
def index():
    return render_template('register.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered')
            return redirect(url_for('register'))

        new_user = User(email=email, name=name, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Sign-up successful. Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')

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

    active_freelancers_count = User.query.count()
    available_jobs_count = Job.query.count()

    # Fetch the first job and user
    first_job = Job.query.first()
    first_user = User.query.first()

    return render_template('home.html', active_freelancers=active_freelancers_count, available_jobs=available_jobs_count, first_job=first_job, first_user=first_user)


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
    query = request.args.get('search_query')
    category_id = request.args.get('category')
    skill_filter = request.args.get('skill')

    jobs = Job.query

    if query:
        jobs = jobs.filter(Job.title.contains(query))
    if category_id and category_id != '':
        jobs = jobs.filter(Job.category_id == category_id)
    if skill_filter and skill_filter != '':
        jobs = jobs.filter(Job.skills.contains(skill_filter))  # Filter by skill

    jobs = jobs.all()
    categories = Category.query.all()

    # Extract unique skills from jobs
    unique_skills = set()
    for job in Job.query.with_entities(Job.skills).all():
        if job.skills:
            # Assuming skills are comma-separated in the database
            unique_skills.update([skill.strip() for skill in job.skills.split(',')])

    return render_template('jobListings.html', jobs=jobs, categories=categories, skills=sorted(unique_skills))


@app.route('/apply_for_job', methods=['POST'])
def apply_for_job():
    job_id = request.form.get('job_id')
    freelancer_id = session.get('user_id')  # Ensure the user is logged in and get their user ID

    if not freelancer_id:
        flash("You must be logged in to apply for jobs.", "error")
        return redirect(url_for('login'))

    job = Job.query.get(job_id)
    if job:
        employer_id = job.employer_id

        # Check if a contract already exists
        contract = Contract.query.filter_by(job_id=job_id, freelancer_id=freelancer_id).first()
        if contract:
            flash("You have already applied for this job.", "info")
        else:
            new_contract = Contract(
                job_id=job_id,
                freelancer_id=freelancer_id,
                employer_id=employer_id,
                status='pending'
            )
            db.session.add(new_contract)
            db.session.commit()
            flash("Your application has been submitted.", "success")
    else:
        flash("Job not found.", "error")

    return redirect(url_for('job_listings'))



@app.route('/add-category', methods=['POST'])
def add_category():
    name = request.form.get('name')
    if name and not Category.query.filter_by(name=name).first():
        category = Category(name=name)
        db.session.add(category)
        db.session.commit()
        return 'Category added successfully!'
    return 'Category already exists or invalid name!'


@app.route('/createJobListings', methods=['GET', 'POST'])
def create_job_listing():
    if 'user_id' not in session:
        flash('Please log in to create job listings.', 'warning')
        return redirect(url_for('login'))

    categories = Category.query.all()
    if request.method == 'POST':
        job_title = request.form['job_title']
        project_description = request.form['project_description']
        budget = request.form['budget']
        project_duration = request.form.get('project_duration')
        experience_level = request.form.get('experience_level')
        skills = request.form['skills']
        category_id = request.form['category']

        new_job = Job(
            title=job_title,
            description=project_description,
            budget=budget,
            duration=project_duration,
            experience_level=experience_level,
            skills=skills,
            category_id=category_id,
            user_id=session['user_id']  # Set the user_id from the session
        )
        db.session.add(new_job)
        db.session.commit()
        flash('Job listing created successfully!', 'success')
        return redirect(url_for('job_listings'))

    return render_template('createJobListings.html', categories=categories)


def get_current_user_id():
    return session.get('user_id')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash('Please log in to access your profile.')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user:
        flash('User not found.')
        return redirect(url_for('login'))

    if request.method == 'POST':
        user.minimum_rate = request.form.get('minimum_rate', type=float)
        user.skills = request.form.get('skills')
        db.session.commit()
        flash('Profile updated successfully!')

    return render_template('profile.html', user=user)

@app.route('/find-freelancers', methods=['GET', 'POST'])
def find_freelancers():
    unique_skills = set()
    # Fetch all users' skills and split by comma to handle multiple skills per user
    for user in User.query.with_entities(User.skills).all():
        if user.skills:
            unique_skills.update([skill.strip() for skill in user.skills.split(',')])

    if request.method == 'POST':
        search_query = request.form['search']
        selected_skill = request.form.get('skill')
        # min_rating = request.form.get('min-rating', type=int)
        # max_rate = request.form.get('max-rate', type=float)

        query = User.query.filter(User.name.contains(search_query) | User.email.contains(search_query))
        
        if selected_skill:
            query = query.filter(User.skills.contains(selected_skill))
        # if min_rating:
        #     query = query.filter(User.rating >= min_rating)  # Assuming a 'rating' field exists
        # if max_rate:
        #     query = query.filter(User.minimum_rate <= max_rate)

        freelancers = query.all()
    else:
        freelancers = []

    # Sort the skills alphabetically for better user experience in the dropdown
    sorted_skills = sorted(list(unique_skills))

    return render_template('findfreelancers.html', skills=sorted_skills, freelancers=freelancers)



@app.route('/messaging')
def messaging():
    return render_template('messaging.html')


@app.route('/contractManagement')
def contract_management():
    user_id = session.get('user_id')  # Step 2: Get user ID from session
    if not user_id:
        flash('You need to login to view this page.', 'info')  # Step 1: Check if the user is logged in
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('login'))

    # Consolidate both freelance and employer contracts
    contracts = user.freelance_contracts + user.employer_contracts
    return render_template('contractManagement.html', contracts=contracts, user=user)


@app.route('/create-contract', methods=['GET', 'POST'])
def create_contract():
    if request.method == 'POST':
        # Process the form data to create a new contract
        return redirect(url_for('contract_management'))
    return render_template('create_contract.html') 


@app.route('/logout', methods=['POST'])
def logout():
    # Clear session data
    session.pop('user_id', None)
    session.pop('user_name', None)
    
    flash('You have been logged out successfully.')
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    add_categories()
    app.run(debug=True)

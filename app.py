from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from alembic import op
import sqlalchemy as sa
import stripe
import os
from functools import wraps
import logging

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/site.db?timeout=30'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tmp/site.db?timeout=30'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this to a real secret key in production sqlite:///site.db?timeout=30
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Stripe configuration
stripe.api_key = 'sk_test_51OIS6hGfhJguOr7SCrwqtCPyCvnBCwwEcHsbv79JtwAJunR2Su6ji4GZx5jrGlULmvT0Ipx5g3pJjqI4uc3kDMfU00uPCuGOtm'


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(60), nullable=False)
    minimum_rate = db.Column(db.Float, nullable=True)
    skills = db.Column(db.String(500), nullable=True)
    jobs = db.relationship('Job', backref='author', lazy=True)
    rating = db.Column(db.Float, nullable=True, default=0.0)
    rating_count = db.Column(db.Integer, default=0)


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


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.now())
    
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')


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

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contract_id = db.Column(db.Integer, db.ForeignKey('contract.id'), nullable=False)
    freelancer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False)  # e.g., "Completed"
    transaction_date = db.Column(db.DateTime, default=db.func.now())
    
    contract = db.relationship('Contract', backref=db.backref('payments', lazy=True))
    freelancer = db.relationship('User', foreign_keys=[freelancer_id])

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)  # To mark if the notification is read
    created_at = db.Column(db.DateTime, default=db.func.now())

    user = db.relationship('User', backref='notifications')


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

def inject_notifications(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if 'user_id' in session:
            user_id = session['user_id']
            unread_notifications = Notification.query.filter_by(user_id=user_id, is_read=False).all()
            return view_func(*args, notifications=unread_notifications, **kwargs)
        return view_func(*args, **kwargs)
    return wrapper

@app.route('/mark_notification_as_read/<int:notification_id>', methods=['POST'])
def mark_notification_as_read(notification_id):
    notification = Notification.query.get(notification_id)
    if notification:
        notification.is_read = True
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False}), 404


@app.route('/home')
@inject_notifications
def home(notifications=[]):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    active_freelancers_count = User.query.count()
    available_jobs_count = Job.query.count()

    first_job = Job.query.first()
    top_rated_user = User.query.order_by(User.rating.desc()).first()

    return render_template('home.html', notifications=notifications, 
                           active_freelancers=active_freelancers_count, 
                           available_jobs=available_jobs_count, 
                           first_job=first_job, 
                           top_rated_user=top_rated_user)


@app.route('/freelancerSearch', methods=['GET', 'POST'])
def freelancer_search():
    # Fetch all users' skills and split by comma to handle multiple skills per user
    unique_skills = set()
    for user in User.query.with_entities(User.skills).all():
        if user.skills:
            unique_skills.update([skill.strip() for skill in user.skills.split(',') if skill.strip()])

    # Sort the skills alphabetically for better user experience in the dropdown
    sorted_skills = sorted(list(unique_skills))

    freelancers = []

    if request.method == 'POST':
        # Process search parameters
        search_query = request.form.get('search')
        skills = request.form.get('skills')
        min_rating = request.form.get('min-rating')
        max_rate = request.form.get('max-rate')

        # Assume a function `search_freelancers` which queries your database
        freelancers = search_freelancers(search_query, skills, min_rating, max_rate)

    return render_template('findfreelancers.html', skills=sorted_skills, freelancers=freelancers)


@app.route('/find-freelancers', methods=['GET', 'POST'])
def find_freelancers():
    unique_skills = set()
    
    # Fetch all users' skills and split by comma to handle multiple skills per user
    for user in User.query.with_entities(User.skills).all():
        if user.skills:
            unique_skills.update([skill.strip() for skill in user.skills.split(',') if skill.strip()])

    # Default to an empty list if no search parameters are provided
    freelancers = []

    search_query = request.args.get('search')
    selected_skill = request.args.get('skill')
    min_rating = request.args.get('min-rating', type=int)
    max_rate = request.args.get('max-rate', type=float)

    # Start building the query for User
    query = User.query

    # Check if search parameters are provided via GET or POST
    if search_query:
        # Filter users based on the search query (name or email)
        query = query.filter(User.name.contains(search_query) | User.email.contains(search_query))

    if selected_skill:
        # Filter users by skill; assuming skills are stored as a comma-separated string
        query = query.filter(User.skills.contains(selected_skill))

    if min_rating is not None:
        # Assuming a 'rating' field exists in User model
        query = query.filter(User.rating >= min_rating)

    if max_rate is not None:
        # Filter users based on their rate
        query = query.filter(User.minimum_rate <= max_rate)

    # Execute the query to get the freelancers
    freelancers = query.all()
    

    # Sort the skills alphabetically for better user experience in the dropdown
    sorted_skills = sorted(list(unique_skills))
    

    return render_template('findfreelancers.html', skills=sorted_skills, freelancers=freelancers)


@app.route('/jobListings', methods=['GET', 'POST'])
def job_listings():
    if 'user_id' not in session:
        flash('Please log in to view job listings.', 'warning')
        return redirect(url_for('login'))
    current_user_id = session['user_id']
    user = User.query.get(current_user_id)
    query = Job.query
    all_contracts = Contract.query.all()
    if user:
        if user.jobs:
            employer_jobs_subquery = db.session.query(Contract.job_id).filter_by(employer_id=current_user_id).subquery()
            query = query.filter(~Job.id.in_(employer_jobs_subquery))
        applied_jobs_subquery = db.session.query(Contract.job_id).filter_by(freelancer_id=current_user_id).subquery()
        query = query.filter(~Job.id.in_(applied_jobs_subquery))
    completed_or_paid_jobs = db.session.query(Contract.job_id).filter(Contract.status.in_(['completed', 'Paid'])).all()
    excluded_job_ids = [row.job_id for row in completed_or_paid_jobs]
    query = query.filter(~Job.id.in_(excluded_job_ids))


    search_query = request.args.get('search_query')
    category_id = request.args.get('category')
    skill_filter = request.args.get('skill')
    if search_query:
        query = query.filter(Job.title.contains(search_query))
    if category_id and category_id != '':
        query = query.filter(Job.category_id == category_id)
    if skill_filter and skill_filter != '':
        query = query.filter(Job.skills.contains(skill_filter))

    jobs = query.all()
    categories = Category.query.all()

    
    unique_skills = set()
    for job in Job.query.with_entities(Job.skills).all():
        if job.skills:
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
            employer_id=session['user_id']  # Set the user_id from the session
        )
        db.session.add(new_job)
        db.session.commit()
        flash('Job listing created successfully!', 'success')

        notification = Notification(
            user_id=new_job.employer_id,
            message=f"You have created a job - {new_job.title}."
        )
        db.session.add(notification)
        db.session.commit()

        # Use flash to pass the notification message to the next request
        flash(f"Job '{job_title}' created successfully!", "success")

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

@app.route('/messaging', methods=['GET'])
def messaging():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    current_user_id = session['user_id']
    recipient_id = request.args.get('recipient_id', type=int)

    # If a recipient is specified, load conversation with that user
    if recipient_id:
        # Load conversation between the logged-in user and selected recipient
        messages = Message.query.filter(
            ((Message.sender_id == current_user_id) & (Message.recipient_id == recipient_id)) |
            ((Message.sender_id == recipient_id) & (Message.recipient_id == current_user_id))
        ).order_by(Message.timestamp).all()

        recipient = User.query.get(recipient_id)
    else:
        messages = []
        recipient = None

    # Get all unique contacts the user has messaged with
    contacts = db.session.query(User).join(Message, db.or_(
        Message.sender_id == User.id,
        Message.recipient_id == User.id
    )).filter(
        (Message.sender_id == current_user_id) | (Message.recipient_id == current_user_id),
        User.id != current_user_id
    ).distinct().all()

    return render_template('messaging.html', messages=messages, recipient=recipient, contacts=contacts, current_user_id=current_user_id)


@app.route('/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    data = request.get_json()
    sender_id = session['user_id']
    recipient_id = data.get('recipient_id')
    content = data.get('message')

    if recipient_id and content:
        new_message = Message(sender_id=sender_id, recipient_id=recipient_id, content=content)
        db.session.add(new_message)
        db.session.commit()
        return {'status': 'success'}, 200
    else:
        return {'status': 'error', 'message': 'Invalid data'}, 400


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
    flash('Contract status has been updated', 'info')
    return render_template('contractManagement.html', contracts=contracts, user=user)

@app.route('/update_contract_status/<int:contract_id>', methods=['POST'])
def update_contract_status(contract_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authorized'}), 401

    data = request.get_json()
    new_status = data.get('status')

    contract = Contract.query.get(contract_id)
    if not contract:
        return jsonify({'error': 'Contract not found'}), 404

    # Ensure the logged-in user is either the employer or freelancer in the contract
    current_user_id = session['user_id']
    if contract.employer_id != current_user_id and contract.freelancer_id != current_user_id:
        return jsonify({'error': 'Not authorized to modify this contract'}), 403

    if new_status == 'withdrawn':
        # Delete the contract if the employer chooses to withdraw it
        db.session.delete(contract)
        flash('Contract has been Withdrawn', 'error')
    else:
        # Update the status of the contract
        contract.status = new_status
        flash('Contract status has been updated', 'info')

    flash('Contract status has been updated', 'info')
    db.session.commit()


    return jsonify({'success': True}), 200


@app.route('/rate_user/<int:contract_id>', methods=['POST'])
def rate_user(contract_id):
    try:
        data = request.get_json()

        if not data or 'rating' not in data:
            return jsonify({"error": "Invalid data"}), 400

        rating = int(data.get('rating'))

        if not (1 <= rating <= 5):
            return jsonify({"error": "Rating must be between 1 and 5"}), 400

        contract = Contract.query.get(contract_id)
        if not contract:
            return jsonify({"error": "Contract not found"}), 404

        # Ensure the logged-in user is eligible to provide a rating
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "User not logged in"}), 403

        # Determine if the user can rate (employer can rate freelancer after completion, and freelancer can rate employer after payment)
        if contract.employer_id == user_id and contract.status == 'completed':
            user_to_rate = contract.freelancer
        elif contract.freelancer_id == user_id and contract.status == 'Paid':
            user_to_rate = contract.employer
        else:
            return jsonify({"error": "You cannot rate this user"}), 403

        # Initialize rating and rating_count if they are None
        if user_to_rate.rating is None:
            user_to_rate.rating = 0.0
        if user_to_rate.rating_count is None:
            user_to_rate.rating_count = 0

        # Update or add the user's rating
        user_to_rate.rating = ((user_to_rate.rating * user_to_rate.rating_count) + rating) / (user_to_rate.rating_count + 1)
        user_to_rate.rating_count += 1

        db.session.commit()
        return jsonify({"success": "Rating submitted successfully"}), 200

    except Exception as e:
        return jsonify({"error": "An internal error occurred"}), 500


@app.route('/create-contract', methods=['GET', 'POST'])
def create_contract():
    if request.method == 'POST':
        # Process the form data to create a new contract
        return redirect(url_for('contract_management'))
    return render_template('create_contract.html') 


@app.route('/paymentDashboard')
def payment_dashboard():
    user_id = session.get('user_id')
    if not user_id:
        flash('You must be logged in to access the payment dashboard.', 'error')
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    payments = []
    total_earnings = 0.0

    if user:
        if user.jobs:
            payments = Payment.query.join(Contract).filter(Contract.employer_id == user_id).all()
            # Freelancer total earnings
            payments_query = Payment.query.filter(Payment.freelancer_id == user_id).all()
            app.logger.debug(f"Payments for user {user_id}: {payments_query}")

            total_earnings = db.session.query(db.func.sum(Payment.amount)) \
                .filter(Payment.freelancer_id == user_id).scalar() or 0.0

            app.logger.debug(f"Total Earnings for user {user_id}: {total_earnings}")

    completed_contracts_as_freelancer = Contract.query.filter_by(freelancer_id=user_id, status='completed').all()
    completed_contracts_as_employer = Contract.query.filter_by(employer_id=user_id, status='completed').all()

    payments = Payment.query.join(Contract).filter(Contract.employer_id == user_id).all()
    paid_contracts_as_employer = Contract.query.filter_by(employer_id = user_id, status='Paid').all()

    return render_template('paymentDashboard.html', 
                           completed_contracts_as_freelancer=completed_contracts_as_freelancer,
                           completed_contracts_as_employer=completed_contracts_as_employer,
                           paid_contracts_as_employer=paid_contracts_as_employer,
                           payments=payments,
                           total_earnings=total_earnings,
                           user=user)

@app.route('/initiate_payment/<int:contract_id>', methods=['GET'])
def initiate_payment(contract_id):
    # Get contract details from database (assuming you have a Contract model)
    contract = Contract.query.get(contract_id)
    if not contract:
        flash("Contract not found", "error")
        return redirect(url_for('contract_management'))
    
    # Create a new Stripe Checkout session
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[
            {
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': contract.job.title,
                        'description': f"Payment for job: {contract.job.title} with Freelancer: {contract.freelancer.name}",
                    },
                    'unit_amount': int(contract.job.budget) * 100,  # Amount in cents
                },
                'quantity': 1,
            },
        ],
        mode='payment',
        success_url=url_for('payment_success', contract_id=contract.id, _external=True),
        cancel_url=url_for('payment_cancel', contract_id=contract.id, _external=True),
    )

    # Redirect the user to the Stripe payment page
    return redirect(session.url, code=303)

@app.route('/payment_success/<int:contract_id>')
def payment_success(contract_id):
    # Handle what happens when payment is successful
    contract = Contract.query.get(contract_id)
    if contract:
        contract.status = 'Paid'
        db.session.commit()

        # Save payment details, including freelancer ID
        payment = Payment(
            contract_id=contract.id,
            freelancer_id=contract.freelancer_id,
            amount=float(contract.job.budget),  # Assuming the amount matches the job budget
            status='Completed'
        )
        db.session.add(payment)
        db.session.commit()

        # Add notification for freelancer
        notification = Notification(
            user_id=contract.freelancer_id,
            message=f"You have received a payment of ${payment.amount} for job '{contract.job.title}'."
        )
        db.session.add(notification)
        db.session.commit()

    return render_template('payment_success.html', contract=contract)


@app.route('/payment_cancel/<int:contract_id>')
def payment_cancel(contract_id):
    # Handle what happens when payment is canceled
    return render_template('payment_cancel.html', contract_id=contract_id)


@app.route('/helpcenter')
def helpcenter():
    return render_template('helpcenter.html') 

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
    
    app.run(debug=True, threaded=False)

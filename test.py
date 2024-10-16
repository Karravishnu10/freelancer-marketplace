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



def get_user_contracts(user_id):
    with app.app_context():
        try:
            contracts = Contract.query.filter(
                (Contract.freelancer_id == user_id) | (Contract.employer_id == user_id)
            ).all()
            for contract in contracts:
                print(f"Contract ID: {contract.id}, Freelancer ID: {contract.freelancer_id}, Employer ID: {contract.employer_id}")
        except Exception as e:
            current_app.logger.error(f"Failed to retrieve contracts: {e}")

# Example usage
if __name__ == '__main__':
    user_id = 1  # Example user ID
    get_user_contracts(user_id)

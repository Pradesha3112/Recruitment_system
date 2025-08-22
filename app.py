# app.py
import os
from flask import Flask, render_template, url_for, redirect, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Create and configure the Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)

# Set up Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    user = Candidate.query.get(int(user_id))
    if not user:
        user = Company.query.get(int(user_id))
    return user

# Database Models
class Candidate(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    applications = db.relationship('Application', backref='applicant', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"Candidate('{self.username}', '{self.email}')"

class Company(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    jobs = db.relationship('Job', backref='employer', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"Company('{self.company_name}', '{self.email}')"

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text)
    role_type = db.Column(db.String(50), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    applications = db.relationship('Application', backref='position', lazy=True)

    def __repr__(self):
        return f"Job('{self.title}', '{self.date_posted}')"

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    status = db.Column(db.String(50), default='Applied')
    aptitude_score = db.Column(db.Float)
    coding_score = db.Column(db.Float)
    project_score = db.Column(db.Float)
    date_applied = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"Application('{self.candidate_id}', '{self.job_id}', '{self.status}')"

# Create all database tables
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_type = request.form.get('user_type')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if user_type == 'candidate':
            user = Candidate.query.filter_by(email=email).first()
            dashboard_route = 'candidate_dashboard'
        else:
            user = Company.query.filter_by(email=email).first()
            dashboard_route = 'company_dashboard'
        
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for(dashboard_route))
        else:
            flash('Login failed. Please check your email and password.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/register/candidate', methods=['GET', 'POST'])
def register_candidate():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('register_candidate.html')
        
        existing_user = Candidate.query.filter((Candidate.username == username) | (Candidate.email == email)).first()
        if existing_user:
            flash('Username or email already exists!', 'error')
            return render_template('register_candidate.html')
        
        new_candidate = Candidate(username=username, email=email)
        new_candidate.set_password(password)
        
        try:
            db.session.add(new_candidate)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'error')
    
    return render_template('register_candidate.html')

@app.route('/register/company', methods=['GET', 'POST'])
def register_company():
    if request.method == 'POST':
        company_name = request.form.get('company_name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('register_company.html')
        
        existing_company = Company.query.filter((Company.company_name == company_name) | (Company.email == email)).first()
        if existing_company:
            flash('Company name or email already exists!', 'error')
            return render_template('register_company.html')
        
        new_company = Company(company_name=company_name, email=email)
        new_company.set_password(password)
        
        try:
            db.session.add(new_company)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'error')
    
    return render_template('register_company.html')

# UPDATED DASHBOARD ROUTES - REPLACE THE OLD ONES WITH THESE
@app.route('/dashboard/candidate')
@login_required
def candidate_dashboard():
    # Check if the current user is actually a candidate
    if not isinstance(current_user, Candidate):
        flash('Access denied. Please login as a candidate.', 'error')
        return redirect(url_for('login'))
    
    return render_template('candidate_dashboard.html', user=current_user)

@app.route('/dashboard/company')
@login_required
def company_dashboard():
    # Check if the current user is actually a company
    if not isinstance(current_user, Company):
        flash('Access denied. Please login as a company.', 'error')
        return redirect(url_for('login'))
    
    return render_template('company_dashboard.html', user=current_user)

if __name__ == '__main__':
    app.run(debug=True)
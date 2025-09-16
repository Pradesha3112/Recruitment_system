# app.py
import os
from flask import Flask, render_template, url_for, redirect, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import time
import random
# Create and configure the Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Needed for session management and security
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'  # Path to our SQLite database file
db = SQLAlchemy(app)  # Initialize the database
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
# Set up Flask-Login for user session management
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Route to redirect to if login is required

# Define Database Models (Tables)

# UserMixin provides default implementations for Flask-Login
class Candidate(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    # Relationship to applications made by this candidate
    applications = db.relationship('Application', backref='applicant', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        # Include class name in ID to avoid conflicts between Candidate and Company IDs
        return f"candidate_{self.id}"

    def __repr__(self):
        return f"Candidate('{self.username}', '{self.email}')"

class Company(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    # Relationship to jobs posted by this company
    jobs = db.relationship('Job', backref='employer', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        # Include class name in ID to avoid conflicts between Candidate and Company IDs
        return f"company_{self.id}"

    def __repr__(self):
        return f"Company('{self.company_name}', '{self.email}')"
# Add to your models section (after the Application model)
class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), nullable=False)
    resume_score = db.Column(db.Float)
    aptitude_score = db.Column(db.Float)
    coding_score = db.Column(db.Float)
    video_score = db.Column(db.Float)
    current_round = db.Column(db.String(50), default='resume_screening')  # resume_screening, aptitude, coding, video, completed
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    application = db.relationship('Application', backref=db.backref('assessment', uselist=False))
    
    def __repr__(self):
        return f"Assessment('{self.application_id}', '{self.current_round}')"
class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text)
    role_type = db.Column(db.String(50), nullable=False)  # e.g., 'Developer', 'UI/UX', 'Marketing'
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # Relationship to applications for this job
    applications = db.relationship('Application', backref='position', lazy=True)

    def __repr__(self):
        return f"Job('{self.title}', '{self.date_posted}')"

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job.id'), nullable=False)
    status = db.Column(db.String(50), default='Applied')  # e.g., Applied, Aptitude Test, Coding Test, Project, Rejected, Hired
    aptitude_score = db.Column(db.Float)
    coding_score = db.Column(db.Float)
    project_score = db.Column(db.Float)
    date_applied = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"Application('{self.candidate_id}', '{self.job_id}', '{self.status}')"

# Create all database tables within the application context
with app.app_context():
    db.create_all()

# This callback is used to reload the user object from the user ID stored in the session
@login_manager.user_loader
def load_user(user_id):
    print(f"Trying to load user with ID: {user_id}")
    
    if not user_id or '_' not in user_id:
        print("Invalid user ID format")
        return None
    
    try:
        user_type, id_num = user_id.split('_', 1)
        id_num = int(id_num)
        
        if user_type == 'candidate':
            user = Candidate.query.get(id_num)
            if user:
                print(f"Loaded candidate: {user.username}")
            return user
        elif user_type == 'company':
            user = Company.query.get(id_num)
            if user:
                print(f"Loaded company: {user.company_name}")
            return user
        else:
            print(f"Unknown user type: {user_type}")
            return None
            
    except ValueError:
        print(f"Invalid user ID format: {user_id}")
        return None

# Debug function to check user types
def debug_user_info():
    print("=== DEBUG: All Users in Database ===")
    candidates = Candidate.query.all()
    companies = Company.query.all()
    
    print("Candidates:")
    for candidate in candidates:
        print(f"  - ID: {candidate.id}, Email: {candidate.email}")
    
    print("Companies:")
    for company in companies:
        print(f"  - ID: {company.id}, Email: {company.email}")
    
    print("================================")

# Define Routes (Views)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_type = request.form.get('user_type')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validate login based on user type
        if user_type == 'candidate':
            user = Candidate.query.filter_by(email=email).first()
            dashboard_route = 'candidate_dashboard'
            user_type_name = 'candidate'
        else:  # company
            user = Company.query.filter_by(email=email).first()
            dashboard_route = 'company_dashboard'
            user_type_name = 'company'
        
        # Check if user exists
        if not user:
            flash(f'No {user_type_name} found with this email.', 'error')
            return render_template('login.html')
        
        # Check if password is correct
        if not user.check_password(password):
            flash('Invalid password. Please try again.', 'error')
            return render_template('login.html')
        
        # Login successful
        login_user(user)
        flash('Login successful!', 'success')
        
        # Debug output to check what type of user we found
        print(f"Logged in as: {type(user).__name__}")
        print(f"User ID: {user.get_id()}")
        print(f"Redirecting to: {dashboard_route}")
        
        return redirect(url_for(dashboard_route))
    
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
        
        # Basic validation
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('register_candidate.html')
        
        # Check if user already exists
        existing_user = Candidate.query.filter((Candidate.username == username) | (Candidate.email == email)).first()
        if existing_user:
            flash('Username or email already exists!', 'error')
            return render_template('register_candidate.html')
        
        # Create new candidate
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
        
        # Basic validation
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('register_company.html')
        
        # Check if company already exists
        existing_company = Company.query.filter((Company.company_name == company_name) | (Company.email == email)).first()
        if existing_company:
            flash('Company name or email already exists!', 'error')
            return render_template('register_company.html')
        
        # Create new company
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
    # Debug: Check what type of user we have
    print(f"Current user type: {type(current_user).__name__}")
    print(f"Current user is Company instance: {isinstance(current_user, Company)}")
    
    # Check if the current user is actually a company
    if not isinstance(current_user, Company):
        flash('Access denied. Please login as a company.', 'error')
        print("Redirecting to login because user is not a Company instance")
        return redirect(url_for('login'))
    
    # Calculate time 10 minutes ago for "new applications" detection
    from datetime import timedelta
    ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
    current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    
    return render_template('company_dashboard.html', 
                         user=current_user, 
                         current_time=current_time,
                         ten_minutes_ago=ten_minutes_ago)
@app.route('/post-job', methods=['GET', 'POST'])
@login_required
def post_job():
    # Check if the current user is actually a company
    if not isinstance(current_user, Company):
        flash('Access denied. Only companies can post jobs.', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        requirements = request.form.get('requirements')
        role_type = request.form.get('role_type')
        
        # Basic validation
        if not all([title, description, role_type]):
            flash('Please fill in all required fields.', 'error')
            return render_template('post_job.html', user=current_user)
        
        # Create new job
        new_job = Job(
            title=title,
            description=description,
            requirements=requirements,
            role_type=role_type,
            company_id=current_user.id
        )
        
        try:
            db.session.add(new_job)
            db.session.commit()
            flash('Job posted successfully!', 'success')
            return redirect(url_for('company_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while posting the job. Please try again.', 'error')
            print(f"Error: {e}")
    
    return render_template('post_job.html', user=current_user)

@app.route('/browse-jobs')
@login_required
def browse_jobs():
    # Check if the current user is actually a candidate
    if not isinstance(current_user, Candidate):
        flash('Access denied. Please login as a candidate.', 'error')
        return redirect(url_for('login'))
    
    # Get filter parameters
    search = request.args.get('search', '')
    role_type = request.args.get('role_type', '')
    
    # Build query
    query = Job.query
    
    if search:
        query = query.filter(Job.title.ilike(f'%{search}%'))
    
    if role_type:
        query = query.filter(Job.role_type == role_type)
    
    # Get jobs
    jobs = query.order_by(Job.date_posted.desc()).all()
    
    return render_template('browse_jobs.html', user=current_user, jobs=jobs)

@app.route('/job/<int:job_id>')
@login_required
def view_job(job_id):
    # Check if the current user is actually a candidate
    if not isinstance(current_user, Candidate):
        flash('Access denied. Please login as a candidate.', 'error')
        return redirect(url_for('login'))
    
    # Get the job
    job = Job.query.get_or_404(job_id)
    
    # Check if user has already applied and get the application
    application = Application.query.filter_by(
        candidate_id=current_user.id,
        job_id=job_id
    ).first()
    
    has_applied = application is not None
    
    # Get application status if applied
    application_status = None
    if has_applied:
        application_status = application.status
    
    return render_template('job_details.html', 
                         user=current_user, 
                         job=job, 
                         has_applied=has_applied,
                         application=application,  # Add this line
                         application_status=application_status)
# Replace the current apply_job route with this:
@app.route('/apply/<int:job_id>')
@login_required
def apply_job(job_id):
    # Check if the current user is actually a candidate
    if not isinstance(current_user, Candidate):
        flash('Access denied. Please login as a candidate.', 'error')
        return redirect(url_for('login'))
    
    # Get the job details
    job = Job.query.get_or_404(job_id)
    
    # Check if already applied
    existing_application = Application.query.filter_by(
        candidate_id=current_user.id,
        job_id=job_id
    ).first()
    
    if existing_application:
        flash('You have already applied for this position.', 'info')
        return redirect(url_for('view_job', job_id=job_id))
    
    return render_template('apply_confirmation.html', 
                         user=current_user, 
                         job=job)

# Add a new route to handle the actual application submission
@app.route('/submit-application/<int:job_id>', methods=['POST'])
@login_required
def submit_application(job_id):
    # Check if the current user is actually a candidate
    if not isinstance(current_user, Candidate):
        flash('Access denied. Please login as a candidate.', 'error')
        return redirect(url_for('login'))
    
    # Check if already applied
    existing_application = Application.query.filter_by(
        candidate_id=current_user.id,
        job_id=job_id
    ).first()
    
    if existing_application:
        flash('You have already applied for this position.', 'info')
        return redirect(url_for('view_job', job_id=job_id))
    
    # Handle file upload if present
    resume_filename = None
    if 'resume' in request.files:
        resume_file = request.files['resume']
        if resume_file and resume_file.filename != '':
            # Secure the filename and save it
            from werkzeug.utils import secure_filename
            import os
            import uuid
            
            # Create upload folder if it doesn't exist
            upload_folder = os.path.join(app.root_path, 'static', 'resumes')
            os.makedirs(upload_folder, exist_ok=True)
            
            # Generate a unique filename
            filename = secure_filename(resume_file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            resume_path = os.path.join(upload_folder, unique_filename)
            resume_file.save(resume_path)
            resume_filename = unique_filename
    
    # Create new application
    new_application = Application(
        candidate_id=current_user.id,
        job_id=job_id,
        status='Applied'
    )
    
    # You might want to add a resume_filename field to your Application model
    # if you want to store the resume filename
    
    try:
        db.session.add(new_application)
        db.session.commit()
        
        # Create assessment for this application
        new_assessment = Assessment(application_id=new_application.id)
        db.session.add(new_assessment)
        db.session.commit()
        
        flash('Application submitted successfully!', 'success')
        return redirect(url_for('assessment', application_id=new_application.id))
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while submitting your application.', 'error')
        print(f"Error: {e}")
        return redirect(url_for('view_job', job_id=job_id))# Placeholder routes for future implementation
@app.route('/applications')
@login_required
def view_applications():
    return "My applications page will be implemented here"

@app.route('/profile')
@login_required
def profile():
    return "Profile page will be implemented here"

# Debug routes (remove in production)
@app.route('/debug/users')
def debug_users():
    # This is just for debugging - remove in production
    debug_user_info()
    return "Check console for user debug information"

@app.route('/debug/reset-password/<email>/<new_password>')
def debug_reset_password(email, new_password):
    # TEMPORARY: For debugging only - remove in production
    user = Candidate.query.filter_by(email=email).first()
    if not user:
        user = Company.query.filter_by(email=email).first()
    
    if user:
        user.set_password(new_password)
        db.session.commit()
        return f"Password reset for {email} to '{new_password}'"
    else:
        return "User not found"

@app.route('/debug/session')
def debug_session():
    # Check what's in the session
    print("Session contents:")
    for key, value in session.items():
        print(f"  {key}: {value}")
    return "Check console for session info"

@app.route('/debug/clear-session')
def debug_clear_session():
    session.clear()
    flash('Session cleared', 'info')
    return redirect(url_for('login'))

@app.route('/company/jobs')
@login_required
def company_jobs():
    # Check if the current user is actually a company
    if not isinstance(current_user, Company):
        flash('Access denied. Please login as a company.', 'error')
        return redirect(url_for('login'))
    
    # Get all jobs posted by this company
    jobs = Job.query.filter_by(company_id=current_user.id).order_by(Job.date_posted.desc()).all()
    
    return render_template('company_jobs.html', user=current_user, jobs=jobs)
@app.route('/api/company/stats')
@login_required
def company_stats_api():
    if not isinstance(current_user, Company):
        return jsonify({'error': 'Access denied'}), 403
    
    stats = {
        'total_jobs': len(current_user.jobs),
        'total_applications': sum(len(job.applications) for job in current_user.jobs),
        'recent_applications': []
    }
    
    # Get recent applications (last 10)
    all_applications = []
    for job in current_user.jobs:
        for application in job.applications:
            all_applications.append({
                'job_title': job.title,
                'candidate_name': application.candidate_name if application.candidate_name else application.applicant.username,
                'date_applied': application.date_applied.strftime('%Y-%m-%d %H:%M'),
                'status': application.status
            })
    
    # Sort by date (newest first) and take top 10
    all_applications.sort(key=lambda x: x['date_applied'], reverse=True)
    stats['recent_applications'] = all_applications[:10]
    
    return jsonify(stats)

@app.route('/assessment')
@login_required
def assessment():
    # Check if the current user is actually a candidate
    if not isinstance(current_user, Candidate):
        flash('Access denied. Please login as a candidate.', 'error')
        return redirect(url_for('login'))
    
    return render_template('assessment.html', user=current_user)

            # Check if the current user is the applicant
    application = Application.query.get_or_404(application_id)
    
    if application.candidate_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('candidate_dashboard'))
    
    # Get or create assessment
    assessment = Assessment.query.filter_by(application_id=application_id).first()
    if not assessment:
        assessment = Assessment(application_id=application_id)
        db.session.add(assessment)
        db.session.commit()
    
    return render_template('assessment.html', 
                         application=application, 
                         assessment=assessment,

                         user=current_user)

@app.route('/application/<int:application_id>/aptitude_test')
def aptitude_test(application_id):
    application = Application.query.get_or_404(application_id)
    return render_template('aptitude_test.html', application=application)

@app.route('/application/<int:application_id>/coding_test')
def coding_test(application_id):
    application = Application.query.get_or_404(application_id)
    return render_template('coding_test.html', application=application)

@app.route('/application/<int:application_id>/project_round')
def project_round(application_id):
    application = Application.query.get_or_404(application_id)
    return render_template('project_round.html', application=application)


@app.route('/profile-page')
@login_required
def profile_page():
    # Assuming you're using Flask-Login and current_user is available
    return render_template('profile.html', user=current_user)


@app.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        try:
            # Get form data
            current_user.full_name = request.form.get('full_name', '')
            current_user.title = request.form.get('title', '')
            current_user.phone = request.form.get('phone', '')
            current_user.location = request.form.get('location', '')
            current_user.summary = request.form.get('summary', '')
            
            # Handle skills
            skills = request.form.getlist('skills')
            current_user.skills = skills
            
            # Handle experience
            experience = []
            companies = request.form.getlist('exp_company[]')
            positions = request.form.getlist('exp_position[]')
            start_dates = request.form.getlist('exp_start_date[]')
            end_dates = request.form.getlist('exp_end_date[]')
            descriptions = request.form.getlist('exp_description[]')
            
            for i in range(len(companies)):
                if companies[i]:  # Only add if company name is provided
                    experience.append({
                        'company': companies[i],
                        'position': positions[i],
                        'start_date': start_dates[i],
                        'end_date': end_dates[i],
                        'description': descriptions[i]
                    })
            
            current_user.experience = experience
            
            # Handle education
            education = []
            institutions = request.form.getlist('edu_institution[]')
            degrees = request.form.getlist('edu_degree[]')
            edu_start_dates = request.form.getlist('edu_start_date[]')
            edu_end_dates = request.form.getlist('edu_end_date[]')
            edu_descriptions = request.form.getlist('edu_description[]')
            
            for i in range(len(institutions)):
                if institutions[i]:  # Only add if institution name is provided
                    education.append({
                        'institution': institutions[i],
                        'degree': degrees[i],
                        'start_date': edu_start_dates[i],
                        'end_date': edu_end_dates[i],
                        'description': edu_descriptions[i]
                    })
            
            current_user.education = education
            
            # Handle certifications
            certifications = []
            cert_names = request.form.getlist('cert_name[]')
            cert_issuers = request.form.getlist('cert_issuer[]')
            cert_issue_dates = request.form.getlist('cert_issue_date[]')
            cert_expiry_dates = request.form.getlist('cert_expiry_date[]')
            
            for i in range(len(cert_names)):
                if cert_names[i]:  # Only add if certification name is provided
                    certifications.append({
                        'name': cert_names[i],
                        'issuer': cert_issuers[i],
                        'issue_date': cert_issue_dates[i],
                        'expiry_date': cert_expiry_dates[i]
                    })
            
            current_user.certifications = certifications
            
            # Handle profile picture upload
            if 'profile_picture' in request.files:
                file = request.files['profile_picture']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    current_user.profile_picture = filename
            
            # Save changes to database
            db.session.commit()
            
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile_page'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error updating profile: ' + str(e), 'error')
    
    return render_template('edit_profile.html', user=current_user)



@app.route('/resume')
@login_required
def resume():
    # Assuming you're using Flask-Login and current_user is available
    return render_template('resume.html', user=current_user)
@app.route('/apptitude')
@login_required
def apptitude():
    # Assuming you're using Flask-Login and current_user is available
    return render_template('apptitude.html', user=current_user)
@app.route('/coding')
@login_required
def coding():
    # Assuming you're using Flask-Login and current_user is available
    return render_template('coding.html', user=current_user)

@app.route('/project')
@login_required
def project():
    # Assuming you're using Flask-Login and current_user is available
    return render_template('project.html', user=current_user)

# Run the application
if __name__ == '__main__':
    app.run(debug=True)
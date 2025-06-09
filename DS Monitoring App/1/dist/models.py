from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    ds = db.Column(db.String(50))
    year = db.Column(db.Integer)
    project_no = db.Column(db.String(50), unique=True)
    client = db.Column(db.String(200))
    project_name = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float)
    status = db.Column(db.Float, nullable=False, default=0.0)
    remaining_amount = db.Column(db.Float)
    total_running_weeks = db.Column(db.Integer)
    po_date = db.Column(db.Date)
    po_no = db.Column(db.String(50))
    date_completed = db.Column(db.Date)
    pic = db.Column(db.String(100))
    address = db.Column(db.String(500))

    updates = db.relationship('ProjectUpdate', backref='project', lazy=True, cascade='all, delete-orphan')
    forecast_items = db.relationship('ForecastItem', backref='project', lazy=True, cascade='all, delete-orphan')
    tasks = db.relationship('ProjectTask', backref='project', lazy=True, cascade='all, delete-orphan')

class ProjectUpdate(db.Model):
    __tablename__ = 'project_updates'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    update_text = db.Column(db.Text, nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    completion_timestamp = db.Column(db.DateTime)
    due_date = db.Column(db.Date)

class ForecastItem(db.Model):
    __tablename__ = 'forecast_items'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    forecast_date = db.Column(db.Date)
    forecast_input_type = db.Column(db.String(20), nullable=False)
    forecast_input_value = db.Column(db.Float, nullable=False)
    is_forecast_completed = db.Column(db.Boolean, default=False)
    is_deduction = db.Column(db.Boolean, default=False)

class ProjectTask(db.Model):
    __tablename__ = 'project_tasks'
    task_id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    task_name = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    planned_weight = db.Column(db.Float)
    actual_start = db.Column(db.Date)
    actual_end = db.Column(db.Date)
    assigned_to = db.Column(db.String(100))
    parent_task_id = db.Column(db.Integer, db.ForeignKey('project_tasks.task_id', ondelete='SET NULL'))

class MRFHeader(db.Model):
    __tablename__ = 'mrf_headers'
    id = db.Column(db.Integer, primary_key=True)
    form_no = db.Column(db.String(50), unique=True, nullable=False)
    mrf_date = db.Column(db.Date)
    project_name = db.Column(db.String(200))
    project_number = db.Column(db.String(50), db.ForeignKey('projects.project_no', ondelete='SET NULL'))
    client = db.Column(db.String(200))
    site_location = db.Column(db.String(500))
    project_phase = db.Column(db.String(50))
    
    header_prepared_by_name = db.Column(db.String(100))
    header_prepared_by_designation = db.Column(db.String(100))
    header_approved_by_name = db.Column(db.String(100))
    header_approved_by_designation = db.Column(db.String(100))
    
    footer_prepared_by_name = db.Column(db.String(100))
    footer_prepared_by_designation = db.Column(db.String(100))
    footer_approved_by_name = db.Column(db.String(100))
    footer_approved_by_designation = db.Column(db.String(100))
    footer_noted_by_name = db.Column(db.String(100))
    footer_noted_by_designation = db.Column(db.String(100))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('MRFItem', backref='header', lazy=True, cascade='all, delete-orphan')

class MRFItem(db.Model):
    __tablename__ = 'mrf_items'
    id = db.Column(db.Integer, primary_key=True)
    mrf_header_id = db.Column(db.Integer, db.ForeignKey('mrf_headers.id', ondelete='CASCADE'), nullable=False)
    item_no = db.Column(db.String(50))
    part_no = db.Column(db.String(100))
    brand_name = db.Column(db.String(100))
    description = db.Column(db.Text)
    qty = db.Column(db.Float)
    uom = db.Column(db.String(50))
    install_date = db.Column(db.Date)
    remarks = db.Column(db.Text)
    status = db.Column(db.String(50), default='Processing')
    actual_delivery_date = db.Column(db.Date) 
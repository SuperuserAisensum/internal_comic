from flask import render_template, request, redirect, url_for, flash, current_app
from app.main import bp
from app.config import Config

@bp.route('/')
@bp.route('/index')
def index():
    """Main landing page"""
    return render_template('main/index.html', title='AiSensum Content Creator')

@bp.route('/about')
def about():
    """About page with company information"""
    company_info = current_app.config['COMPANY_INFO']
    return render_template('main/about.html', title='About AiSensum', 
                          company_info=company_info) 
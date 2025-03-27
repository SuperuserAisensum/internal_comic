from flask import render_template, request, redirect, url_for, flash, current_app, jsonify, Blueprint
from app.content import bp
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime
import requests
from ..utils.text_processor import process_text_content
from ..utils.file_processor import process_file
from ..utils.comic_generator import generate_comic_panels

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'msg', 'eml', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_size_mb(file):
    file.seek(0, os.SEEK_END)
    size_bytes = file.tell()
    file.seek(0)  # Reset file pointer
    return size_bytes / (1024 * 1024)  # Convert to MB

@bp.route('/')
def index():
    """Content generation dashboard"""
    content_toggles = current_app.config['CONTENT_TOGGLES']
    return render_template('content/index.html', title='Content Generation', 
                          toggles=content_toggles)

@bp.route('/upload', methods=['GET', 'POST'])
def upload():
    """Upload newsletter or PDF files"""
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Check file size based on type
            file_size = get_file_size_mb(file)
            extension = file.filename.rsplit('.', 1)[1].lower()
            
            if extension == 'pdf' and file_size > 10:
                flash('PDF file size must be less than 10MB', 'danger')
                return redirect(request.url)
            elif extension in ['msg', 'eml'] and file_size > 15:
                flash('Email file size must be less than 15MB', 'danger')
                return redirect(request.url)
            elif extension == 'txt' and file_size > 5:
                flash('Text file size must be less than 5MB', 'danger')
                return redirect(request.url)
            
            filename = secure_filename(file.filename)
            # Create uploads directory if it doesn't exist
            upload_dir = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            
            flash(f'File {filename} uploaded successfully', 'success')
            return redirect(url_for('content.process', filename=filename))
        else:
            flash('File type not allowed', 'danger')
            return redirect(request.url)
    
    return render_template('content/upload.html', title='Upload Files')

@bp.route('/process/<filename>')
def process(filename):
    """Process the uploaded file and generate content"""
    # In a real app, this would handle file processing
    # For this example, we'll just return a success message
    
    # Get content settings from config
    content_limits = current_app.config['CONTENT_LIMITS']
    content_toggles = current_app.config['CONTENT_TOGGLES']
    
    return render_template('content/process.html', 
                          title='Process Content',
                          filename=filename,
                          content_limits=content_limits,
                          content_toggles=content_toggles)

@bp.route('/status')
def status():
    """Return content processing status (for AJAX updates)"""
    # In a real app, this would return actual processing status
    # For this example, we'll simulate processing with a mock response
    status_data = {
        'progress': 75,
        'status': 'Processing content...',
        'completed_steps': [
            'File uploaded',
            'Content extraction',
            'Topic analysis'
        ],
        'pending_steps': [
            'Social media content generation',
            'Comic script creation'
        ]
    }
    
    return jsonify(status_data)

@bp.route('/results')
def results():
    """Display generated content results"""
    # For this example, we'll use mock data
    mock_results = {
        'linkedin_posts': [
            {
                'title': 'The Rise of AI Assistants',
                'content': 'AI assistants are transforming how we interact with technology. From simple tasks to complex operations, these tools are making our digital lives more efficient and intuitive.',
                'hashtags': ['#AI', '#TechTrends', '#Innovation']
            },
            {
                'title': 'Machine Learning Insights',
                'content': 'The latest advancements in machine learning are creating possibilities we could not imagine five years ago. Here is how these breakthroughs are changing industries.',
                'hashtags': ['#MachineLearning', '#AITechnology', '#FutureOfWork']
            }
        ],
        'instagram_posts': [
            {
                'caption': 'Innovation happens at the intersection of creativity and technology. #AITechnology',
                'image_suggestion': 'Abstract digital network with bright nodes representing connection points'
            }
        ],
        'topics': [
            'AI Ethics and Governance',
            'Natural Language Processing Trends',
            'Computer Vision Applications',
            'AI in Business Intelligence'
        ]
    }
    
    return render_template('content/results.html', 
                          title='Generated Content',
                          results=mock_results)

@bp.route('/generate-article', methods=['POST'])
def generate_article():
    try:
        data = request.get_json()
        topic = data.get('topic')
        
        if not topic:
            return jsonify({'error': 'Topic is required'}), 400
            
        # Generate article using AiSensum API
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {current_app.config["AISENSUM_API_KEY"]}'
        }
        
        # Request article generation
        article_response = requests.post(
            'https://api.aisensum.com/v1/generate/article',
            headers=headers,
            json={
                'topic': topic,
                'style': 'informative',
                'length': 'medium'
            }
        )
        
        if not article_response.ok:
            return jsonify({'error': 'Failed to generate article'}), 500
            
        article_data = article_response.json()
        
        # Generate comic panels using the article content
        comic_panels = generate_comic_panels(
            article_data['title'],
            article_data['content'],
            api_key=current_app.config["IDEOGRAM_API_KEY"]
        )
        
        # Prepare response
        response_data = {
            'title': article_data['title'],
            'content': article_data['content'],
            'comic_panels': comic_panels
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        current_app.logger.error(f'Error generating article: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500 
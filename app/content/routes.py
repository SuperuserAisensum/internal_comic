from flask import render_template, request, redirect, url_for, flash, current_app, jsonify, Blueprint
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime
import requests
from ..utils.text_processor import process_text_content, process_text_for_carousel, generate_comic_script
from ..utils.file_processor import process_file, extract_text_from_pdf, extract_text_from_txt
from ..utils.comic_generator import generate_comic_panels

# Define the blueprint WITHOUT url_prefix here
bp = Blueprint('content', __name__)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'msg', 'eml', 'txt'}

# Directory for storing results (within static folder)
RESULTS_DIR_NAME = 'results' 

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
    # Get content toggles from config, provide default empty dict if not found
    content_toggles = current_app.config.get('CONTENT_TOGGLES', {})
    return render_template('content/index.html', 
                          title='Content Generation', 
                          toggles=content_toggles) # Pass toggles to the template

@bp.route('/upload', methods=['GET', 'POST'])
def upload():
    """Upload newsletter or PDF files"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            file_size = get_file_size_mb(file)
            extension = file.filename.rsplit('.', 1)[1].lower()
            
            # Simplified size check example
            max_size = 10 # Default max size in MB
            if extension == 'pdf': max_size = 10
            elif extension in ['msg', 'eml']: max_size = 15
            elif extension == 'txt': max_size = 5

            if file_size > max_size:
                flash(f'{extension.upper()} file size must be less than {max_size}MB', 'danger')
                return redirect(request.url)
            
            filename = secure_filename(file.filename)
            upload_dir = os.path.join(current_app.static_folder, 'uploads') # Use static_folder
            os.makedirs(upload_dir, exist_ok=True)
            
            file_path = os.path.join(upload_dir, filename)
            
            try:
                file.save(file_path)
                # Redirect to the process route to handle processing and display results
                return redirect(url_for('content.process', filename=filename))
            except Exception as e:
                current_app.logger.error(f"Error saving file: {e}")
                flash('Error saving file.', 'danger')
                return redirect(request.url)
        else:
            flash('File type not allowed', 'danger')
            return redirect(request.url)
    
    return render_template('content/upload.html', title='Upload Files')

@bp.route('/process/<filename>')
def process(filename):
    """Process the uploaded file and display generated content results"""
    file_path = os.path.join(current_app.static_folder, 'uploads', filename)
    
    if not os.path.exists(file_path):
        flash(f'File {filename} not found.', 'danger')
        return redirect(url_for('content.upload'))
        
    try:
        # Process the file using the utility function
        results_data = process_file(file_path)
        
        # Render the results template with the generated data
        return render_template('content/results.html', 
                              title='Generated Content', 
                              results=results_data)
                              
    except ValueError as e:
        flash(f'Error processing file: {str(e)}', 'danger')
        current_app.logger.error(f"Value error processing {filename}: {e}")
        return redirect(url_for('content.upload'))
    except Exception as e:
        flash('An unexpected error occurred during processing.', 'danger')
        current_app.logger.error(f"Unexpected error processing {filename}: {e}")
        return redirect(url_for('content.upload'))

# The /status route can remain if you plan to implement AJAX polling later
@bp.route('/status')
def status():
    # Mock status or real status logic
    return jsonify({'progress': 100, 'status': 'Complete'}) 

@bp.route('/generate-article', methods=['POST'])
def generate_article():
    try:
        data = request.get_json()
        topic = data.get('topic')
        
        if not topic:
            return jsonify({'error': 'Topic is required'}), 400

        # Check if AISENSUM_API_KEY is configured
        aisensum_key = current_app.config.get("AISENSUM_API_KEY")
        if not aisensum_key:
             return jsonify({'error': 'AiSensum API Key not configured.'}), 500

        # Generate article using AiSensum API
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {aisensum_key}'
        }
        
        # Placeholder URL - replace with actual API endpoint if different
        aisensum_url = current_app.config.get("MODEL_BASE_URL", "https://api.aisensum.com/v1") + '/generate/article'

        article_response = requests.post(
            aisensum_url,
            headers=headers,
            json={
                'topic': topic,
                'style': 'informative', # Example parameters
                'length': 'medium'
            }
        )
        
        if not article_response.ok:
             error_message = article_response.text or f"Failed with status {article_response.status_code}"
             current_app.logger.error(f"AiSensum API Error: {error_message}")
             return jsonify({'error': f'Failed to generate article: {error_message}'}), 500
            
        article_data = article_response.json()

        # Check if IDEOGRAM_API_KEY is configured
        ideogram_key = current_app.config.get("IDEOGRAM_API_KEY")
        comic_panels = []
        if ideogram_key:
            # Generate comic panels using the article content
            comic_panels = generate_comic_panels(
                article_data.get('title', 'Untitled'),
                article_data.get('content', ''),
                api_key=ideogram_key
            )
        else:
            current_app.logger.warning("IDEOGRAM_API_KEY not configured. Skipping comic generation.")
        
        # Prepare response
        response_data = {
            'title': article_data.get('title', 'Untitled Article'),
            'content': article_data.get('content', 'No content generated.'),
            'comic_panels': comic_panels
        }
        
        return jsonify(response_data)
        
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f'API request error: {str(e)}')
        return jsonify({'error': f'API communication error: {str(e)}'}), 503 # Service Unavailable
    except Exception as e:
        current_app.logger.error(f'Error generating article: {str(e)}')
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500 

@bp.route('/history')
def history():
    """Display list of generated results history."""
    results_list = []
    results_dir_path = os.path.join(current_app.static_folder, RESULTS_DIR_NAME)
    
    if os.path.exists(results_dir_path):
        try:
            # List json files, sort by modification time descending (newest first)
            files = sorted(
                (os.path.join(results_dir_path, f) for f in os.listdir(results_dir_path) if f.endswith('.json')),
                key=os.path.getmtime,
                reverse=True
            )
            
            for file_path in files:
                filename = os.path.basename(file_path)
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        # Extract basic info for display
                        results_list.append({
                            'filename': filename,
                            'type': data.get('result_type', 'unknown').capitalize(),
                            'timestamp': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S'),
                            # Add a title or summary if available
                            'title_preview': data.get('linkedin_posts', [{}])[0].get('title', '') or 
                                           data.get('carousel_panels', [{}])[0].get('title', '') or 
                                           data.get('topics', ['N/A'])[0]
                        })
                except (json.JSONDecodeError, IOError) as e:
                    current_app.logger.warning(f"Could not read or parse history file {filename}: {e}")
                    # Optionally add an error entry to results_list
                    results_list.append({
                        'filename': filename,
                        'type': 'Error',
                        'timestamp': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S'),
                        'title_preview': f"Error reading file: {e}"
                    })

        except Exception as e:
            current_app.logger.error(f"Error listing history directory: {e}", exc_info=True)
            flash('Error retrieving results history.', 'danger')
            
    return render_template('content/history.html', 
                          title='Results History', 
                          history=results_list)

@bp.route('/history_item/<result_filename>')
def history_item(result_filename):
    """Display a specific historical result from its JSON file."""
    # Sanitize filename to prevent directory traversal
    safe_filename = secure_filename(result_filename) 
    if safe_filename != result_filename:
        flash('Invalid history filename.', 'danger')
        return redirect(url_for('content.history'))
        
    results_dir_path = os.path.join(current_app.static_folder, RESULTS_DIR_NAME)
    file_path = os.path.join(results_dir_path, safe_filename)
    
    if not os.path.exists(file_path):
        flash(f'History file {safe_filename} not found.', 'danger')
        return redirect(url_for('content.history'))
        
    try:
        with open(file_path, 'r') as f:
            results_data = json.load(f)
            
        result_type = results_data.get('result_type', 'unknown')
        
        if result_type == 'standard':
            template_name = 'content/results.html'
            title = 'View Standard Result'
        elif result_type == 'carousel':
            template_name = 'content/results_carousel.html'
            title = 'View Carousel Result'
        else:
            flash(f'Unknown result type in {safe_filename}.', 'warning')
            # Display raw JSON or a generic error template?
            # For now, redirect back to history list
            return redirect(url_for('content.history'))
            
        return render_template(template_name, 
                              title=title, 
                              results=results_data)
                              
    except (json.JSONDecodeError, IOError) as e:
        current_app.logger.error(f"Error reading or parsing history file {safe_filename}: {e}")
        flash(f'Error loading history item: {safe_filename}', 'danger')
        return redirect(url_for('content.history'))
    except Exception as e:
        current_app.logger.error(f"Unexpected error viewing history item {safe_filename}: {e}", exc_info=True)
        flash('An unexpected error occurred while viewing the history item.', 'danger')
        return redirect(url_for('content.history'))

# --- Carousel Content Routes --- 

@bp.route('/upload_carousel', methods=['GET', 'POST'])
def upload_carousel():
    """Upload text file or PDF for carousel generation."""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        num_panels_str = request.form.get('num_panels', '8') # Get number of panels from form
        
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
            
        # Validate num_panels
        try:
            num_panels = int(num_panels_str)
            if not 4 <= num_panels <= 12:
                 raise ValueError("Number of panels must be between 4 and 12.")
        except ValueError as e:
            flash(f'Invalid number of panels: {e}', 'danger')
            return redirect(request.url)

        # Define allowed extensions for carousel
        ALLOWED_EXTENSIONS_CAROUSEL = {'txt', 'pdf'}
        filename = file.filename
        is_allowed = '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS_CAROUSEL

        if file and is_allowed:
            file_size = get_file_size_mb(file)
            extension = filename.rsplit('.', 1)[1].lower()
            
            # Set size limits based on extension
            max_size = 10 if extension == 'pdf' else 5

            if file_size > max_size:
                flash(f'{extension.upper()} file size must be less than {max_size}MB', 'danger')
                return redirect(request.url)
            
            # Secure filename and save
            secure_filename_val = secure_filename(filename)
            upload_dir = os.path.join(current_app.static_folder, 'uploads') 
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, secure_filename_val)
            
            try:
                file.save(file_path)
                # Redirect to process_carousel, passing num_panels as query parameter
                return redirect(url_for('content.process_carousel', filename=secure_filename_val, num_panels=num_panels))
            except Exception as e:
                current_app.logger.error(f"Error saving carousel file: {e}")
                flash('Error saving file for carousel.', 'danger')
                return redirect(request.url)
        else:
            flash('Only .txt and .pdf files are allowed for carousel generation.', 'danger')
            return redirect(request.url)
    
    return render_template('content/upload_carousel.html', title='Upload Text or PDF for Carousel')

@bp.route('/process_carousel/<filename>')
def process_carousel(filename):
    """Process the uploaded text/pdf file for carousel and display results."""
    # Get num_panels from query parameters, default to 8
    try:
        num_panels = int(request.args.get('num_panels', 8))
        if not 4 <= num_panels <= 12:
             num_panels = 8 # Fallback to default if invalid range in URL
    except ValueError:
        num_panels = 8 # Fallback to default if not an integer
        
    file_path = os.path.join(current_app.static_folder, 'uploads', filename)
    
    if not os.path.exists(file_path):
        flash(f'File {filename} not found.', 'danger')
        return redirect(url_for('content.upload_carousel'))
        
    try:
        # Determine file type and extract text directly
        _, ext = os.path.splitext(filename)
        ext = ext.lower().lstrip('.')
        text_content = None

        if ext == 'txt':
            text_content = extract_text_from_txt(file_path)
        elif ext == 'pdf':
            text_content = extract_text_from_pdf(file_path)
        else:
            # Should not happen due to checks in upload_carousel, but good practice
            flash(f'Unsupported file type for carousel: {ext}', 'danger')
            return redirect(url_for('content.upload_carousel'))
            
        if text_content is None or not text_content.strip():
             flash(f'Could not extract text content from {filename} or the file is empty.', 'warning')
             current_app.logger.warning(f"Text extraction failed or empty for {filename} (type: {ext})")
             return redirect(url_for('content.upload_carousel'))

        # Process the extracted text using the carousel function, passing num_panels
        results_data = process_text_for_carousel(text_content, num_panels=num_panels)
        
        # Add metadata (including num_panels requested) and save results
        results_data['result_type'] = 'carousel'
        results_data['original_filename'] = filename
        results_data['num_panels_requested'] = num_panels # Store requested number
        results_data['timestamp'] = datetime.utcnow().isoformat()
        
        results_dir = os.path.join(current_app.static_folder, RESULTS_DIR_NAME)
        os.makedirs(results_dir, exist_ok=True)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_filename = f"{os.path.splitext(filename)[0]}_{timestamp_str}_carousel.json"
        result_file_path = os.path.join(results_dir, result_filename)
        
        with open(result_file_path, 'w') as f_json:
            json.dump(results_data, f_json, indent=4)
        current_app.logger.info(f"Carousel results saved to {result_filename}")

        # Render the carousel results template
        return render_template('content/results_carousel.html', 
                              title='Generated Carousel Content', 
                              results=results_data)
                              
    except FileNotFoundError:
         flash(f'File {filename} not found during processing.', 'danger')
         current_app.logger.error(f"File not found error processing carousel for {filename}")
         return redirect(url_for('content.upload_carousel'))
    except IOError as e:
        flash(f'Error reading file: {str(e)}', 'danger')
        current_app.logger.error(f"IOError reading {filename} for carousel: {e}")
        return redirect(url_for('content.upload_carousel'))
    except Exception as e:
        flash('An unexpected error occurred during carousel processing.', 'danger')
        current_app.logger.error(f"Unexpected error processing carousel for {filename}: {e}", exc_info=True)
        return redirect(url_for('content.upload_carousel'))

# --- NEW Combined Content + Comic Routes --- 

@bp.route('/upload_combined', methods=['GET', 'POST'])
def upload_combined():
    """Upload text or PDF for combined carousel and comic generation."""
    if request.method == 'POST':
        if 'file' not in request.files: flash('No file part', 'danger'); return redirect(request.url)
        file = request.files['file']
        if file.filename == '': flash('No selected file', 'danger'); return redirect(request.url)
        
        if file and allowed_file(file.filename):
            file_size = get_file_size_mb(file)
            extension = file.filename.rsplit('.', 1)[1].lower()
            max_size = 10 if extension == 'pdf' else 5
            
            if file_size > max_size:
                flash(f'{extension.upper()} file size must be less than {max_size}MB for combined generation.', 'danger')
                return redirect(request.url)
                
            filename = secure_filename(file.filename)
            upload_dir = os.path.join(current_app.static_folder, 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            file_path = os.path.join(upload_dir, filename)
            try:
                file.save(file_path)
                # Redirect to the new combined process route
                return redirect(url_for('content.process_combined', filename=filename))
            except Exception as e: 
                current_app.logger.error(f"Error saving file for combined generation: {e}")
                flash('Error saving file.', 'danger'); return redirect(request.url)
        else:
            flash('Only .txt and .pdf files are allowed for combined generation.', 'danger')
            return redirect(request.url)
            
    return render_template('content/upload_combined.html', title='Upload for Content + Comic')

@bp.route('/process_combined/<filename>')
def process_combined(filename):
    """Process uploaded file for both carousel content and comic strip."""
    file_path = os.path.join(current_app.static_folder, 'uploads', filename)
    if not os.path.exists(file_path): flash(f'File {filename} not found.', 'danger'); return redirect(url_for('content.upload_combined'))

    text_content = None
    carousel_results = None
    comic_script_data = None
    comic_panels = None
    final_results = { # Initialize results structure
        'result_type': 'combined',
        'original_filename': filename,
        'timestamp': datetime.utcnow().isoformat(),
        'carousel_panels': None,
        'comic_script': None,
        'comic_panels': None,
        'errors': []
    }

    try:
        # 1. Extract Text
        _, ext = os.path.splitext(filename)
        ext = ext.lower().lstrip('.')
        if ext == 'txt': text_content = extract_text_from_txt(file_path)
        elif ext == 'pdf': text_content = extract_text_from_pdf(file_path)
        
        if text_content is None or not text_content.strip():
            final_results['errors'].append('Could not extract text content or file is empty.')
            raise ValueError("Text extraction failed or empty.")

        # 2. Generate Carousel Content (Using Groq)
        try:
            carousel_results = process_text_for_carousel(text_content, num_panels=8) # Fixed 8 panels for combined
            if not carousel_results or 'carousel_panels' not in carousel_results or not carousel_results['carousel_panels'] or carousel_results['carousel_panels'][0].get('title') == 'Error':
                 final_results['errors'].append(f"Failed to generate carousel content. Details: {carousel_results.get('carousel_panels', [{}])[0].get('text', 'Unknown Groq Error')}")
                 final_results['carousel_panels'] = [] # Ensure it's a list even on error
            else:
                 final_results['carousel_panels'] = carousel_results['carousel_panels']
        except Exception as e:
             current_app.logger.error(f"Error calling process_text_for_carousel: {e}", exc_info=True)
             final_results['errors'].append(f"Error generating carousel content: {e}")
             final_results['carousel_panels'] = []

        # 3. Generate Comic Script (Using Groq)
        try:
            # Using fixed 4 panels for comic script for simplicity
            comic_script_data = generate_comic_script(text_content, num_comic_panels=4) 
            if not comic_script_data or 'comic_script' not in comic_script_data or not comic_script_data['comic_script'] or comic_script_data['comic_script'][0].get('description', '').startswith('Error:'):
                error_detail = comic_script_data.get('comic_script', [{}])[0].get('description', 'Unknown Groq Error')
                final_results['errors'].append(f"Failed to generate comic script. Details: {error_detail}")
                final_results['comic_script'] = []
            else:
                 final_results['comic_script'] = comic_script_data['comic_script']
        except Exception as e:
             current_app.logger.error(f"Error calling generate_comic_script: {e}", exc_info=True)
             final_results['errors'].append(f"Error generating comic script: {e}")
             final_results['comic_script'] = []

        # 4. Generate Comic Images (Using Ideogram, only if script exists)
        ideogram_key = current_app.config.get("IDEOGRAM_API_KEY")
        if final_results['comic_script'] and ideogram_key:
            try:
                comic_panels = generate_comic_panels(script=final_results['comic_script'], api_key=ideogram_key)
                if not comic_panels:
                     final_results['errors'].append("Comic image generation returned empty results.")
                     final_results['comic_panels'] = []
                else:
                     final_results['comic_panels'] = comic_panels
                     # Check for individual panel errors from generator
                     if any(p.get('description','').find('(Error:') != -1 for p in comic_panels):
                          final_results['errors'].append("Some comic images failed to generate (check panel descriptions).")
            except Exception as e:
                current_app.logger.error(f"Error calling generate_comic_panels: {e}", exc_info=True)
                final_results['errors'].append(f"Error generating comic images: {e}")
                final_results['comic_panels'] = [] # Ensure list on error
        elif not ideogram_key:
             final_results['errors'].append("Ideogram API Key not configured. Skipping comic image generation.")
             final_results['comic_panels'] = []
        elif not final_results['comic_script']:
             final_results['errors'].append("Comic script generation failed. Skipping comic image generation.")
             final_results['comic_panels'] = []
             
    except ValueError as e:
         # Error from text extraction
         flash(str(e), 'danger')
         current_app.logger.error(f"Value error during combined processing for {filename}: {e}")
         return redirect(url_for('content.upload_combined'))
    except Exception as e:
         # Catch any other unexpected errors during the sequence
         flash('An unexpected error occurred during combined processing.', 'danger')
         current_app.logger.error(f"Unexpected error in process_combined for {filename}: {e}", exc_info=True)
         final_results['errors'].append(f"Unexpected processing error: {e}")
         # Attempt to render results even with errors
         
    # 5. Save Combined Results to JSON
    try:
        results_dir = os.path.join(current_app.static_folder, RESULTS_DIR_NAME)
        os.makedirs(results_dir, exist_ok=True)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_filename = f"{os.path.splitext(filename)[0]}_{timestamp_str}_combined.json"
        result_file_path = os.path.join(results_dir, result_filename)
        with open(result_file_path, 'w') as f_json: json.dump(final_results, f_json, indent=4)
        current_app.logger.info(f"Combined results saved to {result_filename}")
    except Exception as e:
         current_app.logger.error(f"Failed to save combined results JSON for {filename}: {e}")
         final_results['errors'].append("Failed to save results file.")
         # Continue to render anyway

    # 6. Render the Combined Results Template
    # Need to create this template
    return render_template('content/results_combined.html', 
                          title='Generated Content + Comic', 
                          results=final_results)
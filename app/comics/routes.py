from flask import render_template, request, redirect, url_for, flash, current_app, jsonify, session, send_file
from app.comics import bp
from werkzeug.utils import secure_filename
import os
import json
import requests
from datetime import datetime
from PIL import Image
from io import BytesIO
import zipfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

@bp.route('/')
def index():
    """Comic generator dashboard"""
    comic_settings = current_app.config['COMIC_SETTINGS']
    return render_template('comics/index.html', title='Comic Generator', 
                          settings=comic_settings)

@bp.route('/create', methods=['GET', 'POST'])
def create():
    """Create a new comic"""
    if request.method == 'POST':
        # Check if the post request has data
        if not request.form.get('script'):
            flash('No script provided', 'danger')
            return redirect(request.url)
        
        script = request.form.get('script')
        title = request.form.get('title', 'New Comic')
        
        # Parse script into panels
        panels = parse_comic_script(script)
        
        # Generate images for each panel with sequential context
        panel_images = []
        previous_description = None
        
        for i, panel in enumerate(panels):
            try:
                # Pass panel index, total panels, and previous description for context
                image_path = generate_panel_image(
                    panel['description'],
                    panel_index=i,
                    total_panels=len(panels),
                    previous_panel_description=previous_description
                )
                
                if image_path:
                    panel_images.append(image_path)
                    # Store current description for next panel
                    previous_description = panel['description']
            except Exception as e:
                flash(f'Error generating panel image: {str(e)}', 'danger')
                return redirect(url_for('comics.create'))
        
        # Save data to session
        session['comic_script'] = script
        session['comic_title'] = title
        session['comic_panels'] = panels
        session['panel_images'] = panel_images
        
        flash('Comic generated successfully', 'success')
        return redirect(url_for('comics.preview'))
    
    return render_template('comics/create.html', title='Create Comic')

@bp.route('/preview')
def preview():
    """Preview the generated comic"""
    if not session.get('comic_script'):
        flash('No comic script found. Please create a comic first.', 'warning')
        return redirect(url_for('comics.create'))
    
    title = session.get('comic_title', 'New Comic')
    panels = session.get('comic_panels', [])
    panel_images = session.get('panel_images', [])
    
    # Debug logging
    current_app.logger.info(f"Preview - Title: {title}")
    current_app.logger.info(f"Preview - Number of panels: {len(panels)}")
    current_app.logger.info(f"Preview - Panel images: {panel_images}")
    
    # Verify image files exist
    for img_path in panel_images:
        # Convert URL to filesystem path
        rel_path = img_path.replace('/static/', '')
        abs_path = os.path.join(current_app.root_path, 'static', rel_path)
        current_app.logger.info(f"Checking image file: {abs_path}")
        if not os.path.exists(abs_path):
            current_app.logger.error(f"Image file not found: {abs_path}")
    
    return render_template('comics/preview.html', 
                          title=f'Preview: {title}',
                          comic_title=title,
                          panels=panels,
                          panel_images=panel_images)

@bp.route('/generate_panel', methods=['POST'])
def generate_panel():
    """API endpoint to generate a single panel image"""
    data = request.json
    if not data or not data.get('description'):
        return jsonify({'error': 'No panel description provided'}), 400
    
    panel_description = data.get('description')
    
    # In a real app, this would call the image generation API
    # For this example, we'll simulate a successful response
    response = {
        'success': True,
        'image_url': '/static/placeholders/generated_panel.jpg',
        'panel_description': panel_description
    }
    
    return jsonify(response)

@bp.route('/download/<comic_id>')
def download(comic_id):
    """Download the generated comic"""
    # In a real app, this would return the actual comic file
    # For this example, we'll just redirect to the preview page
    flash('Comic download feature would be implemented here in the real app.', 'info')
    return redirect(url_for('comics.preview'))

@bp.route('/download/pdf')
def download_pdf():
    """Download the comic as PDF with side-by-side panels"""
    if not session.get('comic_panels') or not session.get('panel_images'):
        flash('No comic data found. Please create a comic first.', 'warning')
        return redirect(url_for('comics.create'))
    
    try:
        # Create a temporary PDF file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"comic_{timestamp}.pdf"
        pdf_path = os.path.join(current_app.root_path, 'static', 'temp', pdf_filename)
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        
        # Load all panel images first to calculate dimensions
        panel_images = []
        total_width = 0
        max_height = 0
        
        for img_url in session['panel_images']:
            img_path = os.path.join(current_app.root_path, img_url.lstrip('/'))
            if os.path.exists(img_path):
                img = Image.open(img_path)
                panel_images.append(img)
                total_width += img.width
                max_height = max(max_height, img.height)
        
        # Create PDF with custom page size to fit all panels
        pagesize = (total_width + 100, max_height + 150)  # Add margins
        c = canvas.Canvas(pdf_path, pagesize=pagesize)
        
        # Add title at the top
        title = session.get('comic_title', 'Comic')
        c.setFont("Helvetica-Bold", 24)
        c.drawString(50, pagesize[1] - 50, title)
        
        # Add panels side by side
        x_offset = 50  # Start with left margin
        y_position = pagesize[1] - max_height - 100  # Position below title
        
        for i, img in enumerate(panel_images):
            # Add image
            img_path = os.path.join(current_app.root_path, session['panel_images'][i].lstrip('/'))
            c.drawImage(img_path, x_offset, y_position, width=img.width, height=img.height)
            x_offset += img.width
        
        c.save()
        
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=pdf_filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error generating PDF: {str(e)}")
        flash('Error generating PDF file', 'danger')
        return redirect(url_for('comics.preview'))

@bp.route('/download/images')
def download_images():
    """Download the comic panels as a single PNG image"""
    if not session.get('panel_images'):
        flash('No comic images found. Please create a comic first.', 'warning')
        return redirect(url_for('comics.create'))
    
    try:
        # Create a temporary combined image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_filename = f"comic_{timestamp}.png"
        image_path = os.path.join(current_app.root_path, 'static', 'temp', image_filename)
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        
        # Load all panel images
        panel_images = []
        total_width = 0
        max_height = 0
        
        for img_url in session['panel_images']:
            # Convert URL to filesystem path
            img_path = os.path.join(current_app.root_path, img_url.lstrip('/'))
            if os.path.exists(img_path):
                img = Image.open(img_path)
                panel_images.append(img)
                total_width += img.width
                max_height = max(max_height, img.height)
        
        # Create new image with combined width
        combined_image = Image.new('RGB', (total_width, max_height), (255, 255, 255))
        
        # Paste all images horizontally
        x_offset = 0
        for img in panel_images:
            combined_image.paste(img, (x_offset, 0))
            x_offset += img.width
        
        # Save combined image
        combined_image.save(image_path, quality=95)
        
        return send_file(
            image_path,
            as_attachment=True,
            download_name=image_filename,
            mimetype='image/png'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error creating combined image: {str(e)}")
        flash('Error creating combined image', 'danger')
        return redirect(url_for('comics.preview'))

@bp.route('/download/script')
def download_script():
    """Download the comic script"""
    if not session.get('comic_script'):
        flash('No comic script found. Please create a comic first.', 'warning')
        return redirect(url_for('comics.create'))
    
    try:
        # Create a temporary script file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        script_filename = f"comic_script_{timestamp}.txt"
        script_path = os.path.join(current_app.root_path, 'static', 'temp', script_filename)
        os.makedirs(os.path.dirname(script_path), exist_ok=True)
        
        # Format script with proper structure
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(f"### **Comic Script Title: \"{session.get('comic_title', 'Untitled Comic')}\"**\n\n")
            f.write("**Setting:** A modern setting with technology and innovation.\n\n")
            f.write("---\n\n")
            
            # Write each panel with proper formatting
            for i, panel in enumerate(session.get('comic_panels', []), 1):
                f.write(f"**Panel {i}:**\n")
                f.write(f"*Scene: {panel['description']}*\n\n")
                
                # Add dialogue if present
                if panel.get('dialogue'):
                    for dialogue in panel['dialogue']:
                        f.write(f"**{dialogue['character']}:** {dialogue['text']}\n")
                    f.write("\n")
                
                f.write("---\n\n")
            
            # Add end marker
            f.write("**End**\n\n")
            f.write("This comic script illustrates the story through detailed panel descriptions and character dialogue.")
        
        return send_file(
            script_path,
            as_attachment=True,
            download_name=script_filename,
            mimetype='text/plain'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error saving script file: {str(e)}")
        flash('Error saving script file', 'danger')
        return redirect(url_for('comics.preview'))

@bp.route('/regenerate_panels', methods=['POST'])
def regenerate_panels():
    """Regenerate all panels for the current comic"""
    if not session.get('comic_panels'):
        flash('No comic data found. Please create a comic first.', 'warning')
        return redirect(url_for('comics.create'))
    
    try:
        # Get existing panels data
        panels = session.get('comic_panels', [])
        new_panel_images = []
        previous_description = None
        
        # Regenerate each panel with sequential context
        for i, panel in enumerate(panels):
            try:
                # Pass panel index, total panels, and previous description for context
                image_path = generate_panel_image(
                    panel['description'],
                    panel_index=i,
                    total_panels=len(panels),
                    previous_panel_description=previous_description
                )
                
                if image_path:
                    new_panel_images.append(image_path)
                    # Store current description for next panel
                    previous_description = panel['description']
            except Exception as e:
                flash(f'Error regenerating panel image: {str(e)}', 'danger')
                return redirect(url_for('comics.preview'))
        
        # Update session with new images
        session['panel_images'] = new_panel_images
        
        flash('Panels regenerated successfully', 'success')
        return redirect(url_for('comics.preview'))
        
    except Exception as e:
        current_app.logger.error(f"Error regenerating panels: {str(e)}")
        flash('Error regenerating panels', 'danger')
        return redirect(url_for('comics.preview'))

def generate_panel_image(description, panel_index=0, total_panels=1, previous_panel_description=None):
    """Generate an image for a comic panel using Ideogram API with enhanced consistency"""
    try:
        # Get API configuration
        config = current_app.config
        api_key = config['COMIC_SETTINGS'].get('api_key')
        if not api_key:
            raise ValueError("Ideogram API key not configured")

        # Prepare API request
        headers = {
            'Api-Key': api_key,
            'Content-Type': 'application/json'
        }
        
        # Extract character names from dialogue
        character_names = []
        if 'comic_panels' in session and len(session['comic_panels']) > 0:
            # Get all unique character names across panels
            all_panels = session.get('comic_panels', [])
            for panel in all_panels:
                for dialogue in panel.get('dialogue', []):
                    character = dialogue.get('character', '').strip()
                    if character and character not in character_names:
                        character_names.append(character)
        
        # Build character consistency string
        character_string = ""
        if character_names:
            character_string = f"Characters: {', '.join(character_names)}. "
            character_string += "Maintain consistent character appearances throughout all panels. "
        
        # Add style consistency
        style_string = "Comic book style, clear lines, vibrant colors, dynamic composition. "
        
        # Add panel context for better sequence
        context_string = ""
        if panel_index > 0 and previous_panel_description:
            context_string = f"This follows the previous panel where: {previous_panel_description}. "
        
        sequence_string = f"This is panel {panel_index+1} of {total_panels}. "
        
        # Combine into enhanced prompt
        enhanced_prompt = (
            f"{style_string} {character_string} {context_string} {sequence_string} "
            f"Panel content: {description}"
        )
        
        # Add negative prompt to avoid inconsistency
        negative_prompt = "inconsistent characters, blurry, low quality, deformed faces, multiple styles"
        
        # Updated request payload structure according to Ideogram API docs
        data = {
            'image_request': {
                'prompt': enhanced_prompt,
                'negative_prompt': negative_prompt,
                'aspect_ratio': 'ASPECT_1_1',
                'model': 'V_2',
                'magic_prompt_option': 'AUTO',
                'style': 'ANIME'
            }
        }
        
        # Log the prompt for debugging
        current_app.logger.info(f"Enhanced prompt: {enhanced_prompt}")
        
        # Make API request
        response = requests.post(
            'https://api.ideogram.ai/generate',
            headers=headers,
            json=data
        )
        
        if response.status_code != 200:
            raise Exception(f"API Error: {response.status_code} - {response.text}")
        
        # Process the response
        result = response.json()
        if 'data' in result and len(result['data']) > 0:
            image_url = result['data'][0].get('url')
            if not image_url:
                raise ValueError("No image URL in response")
                
            # Download the image
            image_response = requests.get(image_url)
            image_response.raise_for_status()
            
            # Save the image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"panel_{timestamp}.png"
            
            # Use absolute path for saving the file
            static_folder = os.path.join(current_app.root_path, 'static', 'placeholders')
            os.makedirs(static_folder, exist_ok=True)
            
            filepath = os.path.join(static_folder, filename)
            
            # Save and process image
            image = Image.open(BytesIO(image_response.content))
            image = image.resize((1024, 1024), Image.Resampling.LANCZOS)
            image.save(filepath, quality=95)
            
            # Log the file path for debugging
            current_app.logger.info(f"Saved image to: {filepath}")
            
            # Return URL for the image using url_for
            return url_for('static', filename=f'placeholders/{filename}')
            
        raise ValueError("Invalid API response format")
        
    except Exception as e:
        current_app.logger.error(f"Error generating panel image: {str(e)}")
        raise

def parse_comic_script(script_text):
    """Parse a comic script into panels and dialogue"""
    panels = []
    
    # Split by panel indicators
    lines = script_text.strip().split('\n')
    current_panel = {"description": "", "dialogue": []}
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.lower().startswith(("panel", "scene", "frame")) and ":" in line:
            # Save previous panel if it exists
            if current_panel["description"]:
                panels.append(current_panel)
                current_panel = {"description": "", "dialogue": []}
            
            # Get new panel description
            parts = line.split(":", 1)
            if len(parts) > 1:
                current_panel["description"] = parts[1].strip()
        elif ":" in line and not line.startswith(("#", "//")):
            # This is likely dialogue
            parts = line.split(":", 1)
            if len(parts) > 1:
                character = parts[0].strip()
                dialogue = parts[1].strip()
                current_panel["dialogue"].append({"character": character, "text": dialogue})
        else:
            # Add to description
            if current_panel["description"]:
                current_panel["description"] += " " + line
            else:
                current_panel["description"] = line
    
    # Add the last panel
    if current_panel["description"]:
        panels.append(current_panel)
    
    return panels 
import requests
from typing import List, Dict
import json
import re
from flask import current_app # Added to log errors

def extract_scenes(title: str, content: str, num_panels: int = 4) -> List[str]:
    """
    Extract key scenes from article content for comic panels.
    """
    # Combine title and content
    full_text = f"{title}\n\n{content}"
    
    # Split into paragraphs
    paragraphs = [p.strip() for p in full_text.split('\n') if p.strip()]
    
    # If we have fewer paragraphs than needed panels, duplicate some
    while len(paragraphs) < num_panels:
        paragraphs.extend(paragraphs)
    
    # Take the first sentence from selected paragraphs
    scenes = []
    step = max(1, len(paragraphs) // num_panels)
    
    for i in range(0, len(paragraphs), step):
        if len(scenes) >= num_panels:
            break
            
        paragraph = paragraphs[i]
        # Split into sentences and take the first one
        sentences = re.split(r'[.!?]+', paragraph)
        if sentences:
            scene = sentences[0].strip()
            if scene:
                scenes.append(scene)
    
    return scenes[:num_panels]

# Modified function to accept a pre-generated script
def generate_comic_panels(script: List[Dict], api_key: str) -> List[Dict]:
    """
    Generate comic panels using Ideogram API based on a structured script.
    
    Args:
        script: A list of panel dictionaries, each containing 'panel', 
                'description', and 'dialogue'.
        api_key: Ideogram API key.
    
    Returns:
        List of dictionaries containing panel information including image_url:
        {
            'panel': int,         # Added panel number from script
            'image_url': str,
            'description': str,   # From script
            'dialogue': str      # From script
        }
    """
    if not api_key:
        current_app.logger.error("Ideogram API key is missing.")
        # Return script panels without image URLs if API key is missing
        return [
            {
                'panel': panel_data.get('panel', i + 1),
                'image_url': '', 
                'description': panel_data.get('description', 'Error: API Key Missing'),
                'dialogue': panel_data.get('dialogue', '')
            } for i, panel_data in enumerate(script)
        ]
        
    # Updated base URL and endpoint for Ideogram API
    ideogram_base_url = "https://api.ideogram.ai"
    image_endpoint = f"{ideogram_base_url}/generate"

    generated_panels = []
    job_ids = []

    # 1. Submit all generation jobs
    for panel_data in script:
        panel_num = panel_data.get('panel', 'N/A')
        description = panel_data.get('description', '').strip()
        dialogue = panel_data.get('dialogue', '').strip()
        
        if not description:
             current_app.logger.warning(f"Panel {panel_num} has empty description, skipping image generation.")
             generated_panels.append({
                 'panel': panel_num,
                 'image_url': '', # No image if description is empty
                 'description': 'Error: Empty description provided',
                 'dialogue': dialogue
             })
             job_ids.append(None) # Placeholder for skipped job
             continue
             
        prompt_text = f"Comic book style panel: {description}" # Add style context
        current_app.logger.info(f"Submitting image generation for Panel {panel_num} with prompt: {prompt_text}")
        
        try:
            # Updated request payload structure
            data = {
                "image_request": {
                    "prompt": prompt_text,
                    "negative_prompt": "inconsistent characters, blurry, low quality, deformed faces, multiple styles",
                    "model": "V_2",
                    "aspect_ratio": "ASPECT_1_1",
                    "magic_prompt_option": "AUTO"
                }
            }
            
            # Updated headers with Api-Key instead of Authorization
            response = requests.post(
                image_endpoint,
                headers={
                    'Api-Key': api_key,
                    'Content-Type': 'application/json'
                },
                json=data,
                timeout=30 # Timeout for the submission request
            )
            response.raise_for_status() # Raise HTTPError for bad responses
            
            # Updated response handling for synchronous API
            result = response.json()
            if 'data' in result and len(result['data']) > 0:
                image_url = result['data'][0].get('url')
                if image_url:
                    generated_panels.append({
                        'panel': panel_num,
                        'image_url': image_url,
                        'description': description,
                        'dialogue': dialogue
                    })
                    current_app.logger.info(f"Panel {panel_num} image generated successfully: {image_url}")
                else:
                    current_app.logger.error(f"No image URL in response for panel {panel_num}")
                    generated_panels.append({
                        'panel': panel_num,
                        'image_url': '',
                        'description': description,
                        'dialogue': dialogue,
                        'error': 'No image URL in response'
                    })
            else:
                current_app.logger.error(f"Invalid response format for panel {panel_num}")
                generated_panels.append({
                    'panel': panel_num,
                    'image_url': '',
                    'description': description,
                    'dialogue': dialogue,
                    'error': 'Invalid response format'
                })
                 
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Error submitting panel {panel_num} to Ideogram: {e}")
            generated_panels.append({'panel': panel_num, 'image_url': '', 'description': description, 'dialogue': dialogue, 'error': str(e)})
        except Exception as e:
             current_app.logger.error(f"Unexpected error submitting panel {panel_num}: {e}")
             generated_panels.append({'panel': panel_num, 'image_url': '', 'description': description, 'dialogue': dialogue, 'error': str(e)})
             
    # Clean up temporary keys from final result
    for panel in generated_panels:
        if panel.get('error') and not panel.get('image_url'):
             panel['description'] += f" (Error: {panel.pop('error')})"
        else:
             panel.pop('error', None)
             
    return generated_panels 
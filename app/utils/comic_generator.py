import requests
from typing import List, Dict
import json
import re

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

def generate_comic_panels(title: str, content: str, api_key: str) -> List[Dict]:
    """
    Generate comic panels using Ideogram API.
    
    Args:
        title: Article title
        content: Article content
        api_key: Ideogram API key
    
    Returns:
        List of dictionaries containing panel information:
        {
            'image_url': str,
            'description': str,
            'dialogue': str
        }
    """
    # Extract scenes for panels
    scenes = extract_scenes(title, content)
    
    # Generate images for each scene
    panels = []
    
    for scene in scenes:
        try:
            # Call Ideogram API to generate image
            response = requests.post(
                'https://api.ideogram.ai/api/v1/images',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'prompt': scene,
                    'style': 'comic',
                    'width': 512,
                    'height': 512
                }
            )
            
            if response.ok:
                data = response.json()
                image_url = data['images'][0]['url']  # Assuming API returns image URL
                
                panels.append({
                    'image_url': image_url,
                    'description': scene,
                    'dialogue': ''  # Optional: Could be generated with another API call
                })
            else:
                # If image generation fails, add panel without image
                panels.append({
                    'image_url': '',
                    'description': scene,
                    'dialogue': ''
                })
                
        except Exception as e:
            print(f"Error generating panel for scene: {scene}")
            print(f"Error: {str(e)}")
            # Add panel without image on error
            panels.append({
                'image_url': '',
                'description': scene,
                'dialogue': ''
            })
    
    return panels 
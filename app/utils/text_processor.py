from typing import Dict, List, Any
import re
import requests
import json
from flask import current_app

def process_text_content(text: str) -> Dict[str, Any]:
    """
    Process raw text content using the configured AI model (e.g., Grok)
    to extract insights and generate content suggestions.
    
    Args:
        text: The raw text content to process
        
    Returns:
        Dictionary containing processed content, matching the structure 
        expected by the results template.
    """
    # Get model configuration from .env (via app.config)
    api_key = current_app.config.get('AISENSUM_API_KEY') # Assuming this key is for the Grok endpoint
    base_url = current_app.config.get('MODEL_BASE_URL')
    model_name = current_app.config.get('MODEL_NAME')
    max_tokens = current_app.config.get('MODEL_MAX_TOKENS', 2000)
    temperature = current_app.config.get('MODEL_TEMPERATURE', 0.7)
    top_p = current_app.config.get('MODEL_TOP_P', 1.0)
    
    if not all([api_key, base_url, model_name]):
        current_app.logger.error("AI Model configuration (API Key, Base URL, Model Name) is missing.")
        # Return default structure on config error
        return { 
            'topics': ["Error: Model configuration missing."], 
            'linkedin_posts': [], 
            'instagram_posts': [] 
        }
        
    # Construct the prompt for the AI model
    # Ask for specific structured output (JSON format within the response)
    prompt_text_part1 = """Analyze the following text content and generate social media content suggestions. 
Format the output strictly as a JSON object with three keys: 
1. 'topics': A list of 5 relevant string topics based on the text.
2. 'linkedin_posts': A list of 2-3 JSON objects, each with 'title' (string), 'content' (string), and 'hashtags' (list of strings).
3. 'instagram_posts': A list of 1-2 JSON objects, each with 'caption' (string) and 'image_suggestion' (string).

Text content:
"""
    prompt_text_part2 = text[:max_tokens*2] # Limit input text size roughly
    prompt_text_part3 = """""" # Closing triple quotes
    prompt = f"{prompt_text_part1}{prompt_text_part2}{prompt_text_part3}"
    
    # Prepare API request
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p
        # Add other parameters compatible with the API if needed
    }
    
    api_endpoint = f"{base_url.rstrip('/')}/chat/completions" # Common endpoint for chat models

    try:
        current_app.logger.info(f"Sending request to AI model: {model_name} at {api_endpoint}")
        response = requests.post(api_endpoint, headers=headers, json=payload, timeout=120) # Increased timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        
        response_data = response.json()
        current_app.logger.debug(f"Raw AI response: {response_data}")
        
        # Extract the generated content (structure depends on the API)
        # Assuming a structure like OpenAI/Anthropic chat completion
        if response_data.get('choices') and len(response_data['choices']) > 0:
            ai_content_raw = response_data['choices'][0].get('message', {}).get('content', '')
            current_app.logger.info("AI content successfully generated.")
            
            # Attempt to parse the JSON string within the AI's response
            try:
                # Clean up potential markdown code fences if AI wrapped JSON in them
                ai_content_clean = re.sub(r'^```json\n?|```$', '', ai_content_raw.strip())
                parsed_content = json.loads(ai_content_clean)
                
                # Validate structure (basic check)
                if all(k in parsed_content for k in ['topics', 'linkedin_posts', 'instagram_posts']):
                    current_app.logger.info("Successfully parsed structured JSON from AI response.")
                    # Ensure lists are correctly typed, provide defaults if keys missing
                    return {
                        'topics': parsed_content.get('topics', [])[:5], # Limit topics
                        'linkedin_posts': parsed_content.get('linkedin_posts', [])[:3], # Limit posts
                        'instagram_posts': parsed_content.get('instagram_posts', [])[:2] # Limit captions
                    }
                else:
                    raise ValueError("Parsed JSON missing required keys.")
                    
            except (json.JSONDecodeError, ValueError) as json_err:
                current_app.logger.error(f"Failed to parse JSON from AI response: {json_err}\nRaw content: {ai_content_raw}")
                # Return raw content with an error message if parsing fails
                return { 
                    'topics': [f"Error: Could not parse AI response."], 
                    'linkedin_posts': [{'title': 'Raw AI Response', 'content': ai_content_raw, 'hashtags': []}], 
                    'instagram_posts': [] 
                }
        else:
            current_app.logger.error(f"AI response format unexpected: {response_data}")
            return { 'topics': ["Error: Unexpected AI response format."], 'linkedin_posts': [], 'instagram_posts': [] }

    except requests.exceptions.Timeout:
        current_app.logger.error(f"API request timed out after 120 seconds.")
        return { 'topics': ["Error: AI request timed out."], 'linkedin_posts': [], 'instagram_posts': [] }
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"AI API request failed: {e}")
        return { 'topics': [f"Error: AI API request failed: {e}"], 'linkedin_posts': [], 'instagram_posts': [] }
    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred in process_text_content: {e}", exc_info=True)
        return { 'topics': [f"Error: Unexpected processing error."], 'linkedin_posts': [], 'instagram_posts': [] }

def process_text_for_carousel(text: str, num_panels: int = 8) -> Dict[str, Any]:
    """
    Process text using the AI model to generate content for a carousel.
    Args: 
        text: The input summary/text content.
        num_panels: The desired number of carousel panels (default 8).
    Returns: 
        Dictionary containing carousel panels, e.g., {'carousel_panels': [...]}
    """
    # Validate num_panels input
    if not 4 <= num_panels <= 12:
        num_panels = 8 # Default to 8 if invalid
        current_app.logger.warning(f"Invalid num_panels requested, defaulting to 8.")
        
    api_key = current_app.config.get('AISENSUM_API_KEY')
    base_url = current_app.config.get('MODEL_BASE_URL')
    model_name = current_app.config.get('MODEL_NAME')
    max_tokens = current_app.config.get('MODEL_MAX_TOKENS', 2000) 
    temperature = current_app.config.get('MODEL_TEMPERATURE', 0.7)
    top_p = current_app.config.get('MODEL_TOP_P', 1.0)

    if not all([api_key, base_url, model_name]):
        current_app.logger.error("AI Model configuration missing for carousel.")
        return {'carousel_panels': [{"title": "Error", "text": "Model configuration missing."}]}

    # Update prompt to use num_panels and request image suggestions
    prompt = f"""Based on the following text, generate content for a {num_panels}-panel Facebook/Instagram carousel ad. 
Format the output strictly as a JSON object with a single key: 'carousel_panels'. 
The value of 'carousel_panels' should be a list containing exactly {num_panels} JSON objects. 
Each object in the list must have three keys: 
1. 'title': A very short, catchy headline/title for the panel (string, max 5 words).
2. 'text': A short, engaging sentence or two for the panel body (string, max 25 words).
3. 'image_suggestion': A brief suggestion for a relevant background image for this panel (string).
Ensure the panels tell a coherent story or flow logically based on the input text.

Input Text:
{text[:max_tokens*2]} 
"""

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens, 
        "temperature": temperature,
        "top_p": top_p
    }
    api_endpoint = f"{base_url.rstrip('/')}/chat/completions"

    try:
        current_app.logger.info(f"Sending carousel request for {num_panels} panels to AI model: {model_name}")
        response = requests.post(api_endpoint, headers=headers, json=payload, timeout=180) # Increased timeout slightly
        response.raise_for_status()
        response_data = response.json()
        current_app.logger.debug(f"Raw AI carousel response: {response_data}")

        if response_data.get('choices') and len(response_data['choices']) > 0:
            ai_content_raw = response_data['choices'][0].get('message', {}).get('content', '')
            current_app.logger.info(f"AI carousel content generated ({len(ai_content_raw)} chars).")
            
            try:
                ai_content_clean = re.sub(r'^```json\n?|```$', '', ai_content_raw.strip())
                parsed_content = json.loads(ai_content_clean)
                
                # Validate structure and panel content
                if ('carousel_panels' in parsed_content and 
                    isinstance(parsed_content['carousel_panels'], list) and
                    all('title' in p and 'text' in p and 'image_suggestion' in p for p in parsed_content['carousel_panels'])):
                    
                    # Limit the number of panels to the requested number
                    limited_panels = parsed_content['carousel_panels'][:num_panels]
                    current_app.logger.info(f"Successfully parsed {len(limited_panels)} structured carousel panels from AI response.")
                    return {'carousel_panels': limited_panels}
                else:
                    raise ValueError("Parsed JSON missing 'carousel_panels' key, is not a list, or panels missing required keys (title, text, image_suggestion).")

            except (json.JSONDecodeError, ValueError) as json_err:
                current_app.logger.error(f"Failed to parse JSON from AI carousel response: {json_err}\nRaw content: {ai_content_raw}")
                return {'carousel_panels': [{"title": "Error", "text": f"Could not parse AI response: {ai_content_raw}", "image_suggestion":"Error"}]}
        else:
             current_app.logger.error(f"AI carousel response format unexpected: {response_data}")
             return {'carousel_panels': [{"title": "Error", "text": "Unexpected AI response format.", "image_suggestion":"Error"}]}

    except requests.exceptions.Timeout:
        current_app.logger.error(f"AI carousel request timed out.")
        return {'carousel_panels': [{"title": "Error", "text": "AI request timed out.", "image_suggestion":"Error"}]}
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"AI API carousel request failed: {e}")
        return {'carousel_panels': [{"title": "Error", "text": f"AI API request failed: {e}", "image_suggestion":"Error"}]}
    except Exception as e:
        current_app.logger.error(f"Unexpected error in process_text_for_carousel: {e}", exc_info=True)
        return {'carousel_panels': [{"title": "Error", "text": "Unexpected processing error.", "image_suggestion":"Error"}]}

# --- New Function for Comic Script Generation --- 

def generate_comic_script(text: str, num_comic_panels: int = 4) -> Dict[str, Any]:
    """
    Generate a comic script from text using the AI model (Groq).
    
    Args:
        text: The input text/summary.
        num_comic_panels: The desired number of comic panels (e.g., 4).
        
    Returns:
        Dictionary containing the generated script, e.g., 
        {'comic_script': [{'panel': 1, 'description': '...', 'dialogue': '...'}, ...]}
        or an error structure.
    """
    if not 2 <= num_comic_panels <= 6: # Limit comic panels for brevity/cost
        num_comic_panels = 4 
        current_app.logger.warning(f"Invalid num_comic_panels requested, defaulting to 4.")
        
    api_key = current_app.config.get('AISENSUM_API_KEY') # Using the same key as others for Groq
    base_url = current_app.config.get('MODEL_BASE_URL')
    model_name = current_app.config.get('MODEL_NAME')
    max_tokens = current_app.config.get('MODEL_MAX_TOKENS', 1500) # Might need fewer tokens than content gen
    temperature = current_app.config.get('MODEL_TEMPERATURE', 0.6)
    top_p = current_app.config.get('MODEL_TOP_P', 1.0)

    if not all([api_key, base_url, model_name]):
        current_app.logger.error("AI Model configuration missing for comic script generation.")
        return {'comic_script': [{"panel": 1, "description": "Error: Model configuration missing.", "dialogue": ""}]}

    # Define the desired JSON structure for the script
    json_format_description = f"""A JSON object with a single key: 'comic_script'.
 The value of 'comic_script' must be a list containing exactly {num_comic_panels} JSON objects.
 Each object in the list represents a panel and must have three keys:
 1. 'panel': (Integer) The panel number, starting from 1.
 2. 'description': (String) A concise visual description of the scene and action for the image generator (max 30 words).
 3. 'dialogue': (String) Optional dialogue or caption for the panel (max 20 words), empty string if none."""

    # Construct the prompt for the AI model
    prompt = f"""Analyze the following text and generate a {num_comic_panels}-panel comic script summarizing the key points or telling a short story based on it.
 Format the output *strictly* as {json_format_description}
 Ensure the descriptions are vivid and suitable for an AI image generator.

 Input Text:
 {text[:max_tokens*2]} 
 """

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens, 
        "temperature": temperature,
        "top_p": top_p
    }
    api_endpoint = f"{base_url.rstrip('/')}/chat/completions"

    try:
        current_app.logger.info(f"Sending comic script request for {num_comic_panels} panels to AI model: {model_name}")
        response = requests.post(api_endpoint, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        response_data = response.json()
        current_app.logger.debug(f"Raw AI comic script response: {response_data}")

        if response_data.get('choices') and len(response_data['choices']) > 0:
            ai_content_raw = response_data['choices'][0].get('message', {}).get('content', '')
            current_app.logger.info(f"AI comic script generated ({len(ai_content_raw)} chars).")
            
            try:
                ai_content_clean = re.sub(r'^```json\n?|```$', '', ai_content_raw.strip())
                parsed_content = json.loads(ai_content_clean)
                
                # Validate structure and panel content
                if ('comic_script' in parsed_content and 
                    isinstance(parsed_content['comic_script'], list) and
                    len(parsed_content['comic_script']) > 0 and # Ensure list is not empty
                    all('panel' in p and 'description' in p and 'dialogue' in p for p in parsed_content['comic_script'])):
                    
                    # Limit the number of panels just in case AI gave more
                    limited_script = parsed_content['comic_script'][:num_comic_panels]
                    current_app.logger.info(f"Successfully parsed {len(limited_script)} structured comic script panels.")
                    return {'comic_script': limited_script}
                else:
                    raise ValueError("Parsed JSON missing 'comic_script' key, is not a list, list is empty, or panels missing required keys (panel, description, dialogue).")

            except (json.JSONDecodeError, ValueError) as json_err:
                current_app.logger.error(f"Failed to parse JSON from AI comic script response: {json_err}\nRaw content: {ai_content_raw}")
                return {'comic_script': [{"panel": 1, "description": f"Error: Could not parse AI script response: {ai_content_raw}", "dialogue": ""}]}
        else:
             current_app.logger.error(f"AI comic script response format unexpected: {response_data}")
             return {'comic_script': [{"panel": 1, "description": "Error: Unexpected AI script response format.", "dialogue": ""}]}

    except requests.exceptions.Timeout:
        current_app.logger.error(f"AI comic script request timed out.")
        return {'comic_script': [{"panel": 1, "description": "Error: AI script request timed out.", "dialogue": ""}]}
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"AI API comic script request failed: {e}")
        return {'comic_script': [{"panel": 1, "description": f"Error: AI API script request failed: {e}", "dialogue": ""}]}
    except Exception as e:
        current_app.logger.error(f"Unexpected error in generate_comic_script: {e}", exc_info=True)
        return {'comic_script': [{"panel": 1, "description": "Error: Unexpected script processing error.", "dialogue": ""}]}

# Keep the old simple functions commented out or remove if no longer needed
# def extract_topics(text: str) -> List[str]: ...
# def generate_linkedin_posts(text: str, topics: List[str]) -> List[Dict[str, Any]]: ...
# def generate_instagram_captions(text: str, topics: List[str]) -> List[Dict[str, Any]]: ... 
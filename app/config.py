import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base config class"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-dev-key')
    FLASK_APP = os.environ.get('FLASK_APP', 'run.py')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 't')
    
    # API Keys
    AISENSUM_API_KEY = os.environ.get('AISENSUM_API_KEY')
    IDEOGRAM_API_KEY = os.environ.get('IDEOGRAM_API_KEY')
    
    # Model Configuration
    MODEL_NAME = os.environ.get('MODEL_NAME', 'grok-beta')
    MODEL_BASE_URL = os.environ.get('MODEL_BASE_URL', 'https://api.x.ai/v1')
    MODEL_MAX_TOKENS = int(os.environ.get('MODEL_MAX_TOKENS', 2000))
    MODEL_TEMPERATURE = float(os.environ.get('MODEL_TEMPERATURE', 0.7))
    MODEL_TOP_P = float(os.environ.get('MODEL_TOP_P', 1.0))
    
    # Company information
    COMPANY_INFO = {
        "name": "AiSensum",
        "description": "AiSensum is at the forefront of AI innovation, pioneering advanced language models and AI solutions. We focus on developing cutting-edge AI technologies that transform how businesses understand and process information. Our expertise spans natural language processing, machine learning, and AI-driven content analysis, making us a trusted authority in the AI space.",
        "brand_voice": "Thoughtful, analytical, and forward-thinking. We share insights that demonstrate deep understanding of AI trends, challenges, and opportunities. Our communication style balances technical expertise with accessibility, making complex AI concepts understandable while maintaining intellectual rigor.",
        "tone": "Intellectual yet approachable, analytical but engaging, forward-thinking and solution-oriented. We focus on sharing knowledge and insights rather than selling products.",
        "target_audience": "AI professionals, technical decision-makers, industry analysts, and organizations interested in understanding AI trends and developments",
        "content_goals": [
            "Position AiSensum as an AI thought leader",
            "Share valuable insights about AI trends and developments",
            "Demonstrate expertise in AI technology and applications",
            "Foster meaningful discussions about AI's impact on business",
            "Provide analysis of industry trends and future directions"
        ]
    }

    # Content generation settings
    CONTENT_LIMITS = {
        "email_batch": {
            "linkedin": {
                "total_posts": 3,
                "max_length": 175
            },
            "instagram": {
                "total_posts": 2,
                "max_length": 80
            },
            "comics": {
                "total_scripts": 3
            },
            "topics": {
                "max_total": 5
            }
        },
        "pdf_batch": {
            "linkedin": {
                "total_posts": 2,
                "max_length": 175
            },
            "instagram": {
                "total_posts": 1,
                "max_length": 80
            },
            "topics": {
                "max_total": 3
            }
        }
    }
    
    # Content toggles
    CONTENT_TOGGLES = {
        "linkedin": True,
        "instagram": True,
        "comic_scripts": True,
        "comic_images": True
    }
    
    # Comic settings
    COMIC_SETTINGS = {
        "panel_width": 1024,
        "panel_height": 1024,
        "panel_padding": 30,
        "title_height": 80,
        "output_quality": 95,
        "api_key": "zshbRFLd-WJ_IYW0KdTRbBN_jbSUVRZF_yY64GMs6uTE-vwE24s6t59WWwIHaIMBU3unWOaSEhceSgc6q6kqvg",
        "font": {
            "title": {
                "size": 32,
                "path": "static/fonts/arialbd.ttf"
            },
            "dialogue": {
                "size": 16,
                "path": "static/fonts/arial.ttf"
            }
        },
        "bubble": {
            "padding": 12,
            "background": "white",
            "text_color": "black",
            "outline_color": "#404040",
            "corner_radius": 15,
            "outline_width": 2,
            "shadow": {
                "enabled": True,
                "color": "#404040",
                "offset": 1
            }
        },
        "panel_border": {
            "color": "#404040",
            "width": 2
        },
        "temp_dir": "temp",
        "cleanup": {
            "enabled": True,
            "max_age_hours": 24
        }
    } 
from typing import Dict, List, Any
import re

def process_text_content(text: str) -> Dict[str, Any]:
    """
    Process raw text content to extract insights and generate content suggestions.
    
    Args:
        text: The raw text content to process
        
    Returns:
        Dictionary containing processed content:
        {
            'topics': List of suggested topics,
            'linkedin_posts': List of LinkedIn post suggestions,
            'instagram_posts': List of Instagram caption suggestions
        }
    """
    # This is a simple implementation - in a real app, you would use 
    # NLP techniques or call an external API like AiSensum
    
    # Extract potential topics from text
    topics = extract_topics(text)
    
    # Generate LinkedIn post suggestions
    linkedin_posts = generate_linkedin_posts(text, topics)
    
    # Generate Instagram caption suggestions
    instagram_posts = generate_instagram_captions(text, topics)
    
    return {
        'topics': topics,
        'linkedin_posts': linkedin_posts,
        'instagram_posts': instagram_posts
    }

def extract_topics(text: str) -> List[str]:
    """Extract potential topics from text content."""
    # Simple implementation - in a real app you would use more advanced NLP
    
    # Split into paragraphs and extract potential topics
    paragraphs = text.split('\n')
    topics = []
    
    # Look for sentences with capital words that might indicate topics
    topic_pattern = re.compile(r'([A-Z][a-z]+ (?:[A-Z][a-z]+ )*(?:and|&)? ?[A-Z][a-z]+)')
    
    for paragraph in paragraphs:
        matches = topic_pattern.findall(paragraph)
        for match in matches:
            # Filter out common sentence starters
            if match not in ['The', 'A', 'An', 'This', 'That', 'These', 'Those']:
                topics.append(match)
    
    # If no topics found, create generic ones
    if not topics:
        topics = [
            "Industry Trends",
            "Technology Innovation",
            "Business Strategy",
            "Future Developments"
        ]
    
    # Remove duplicates and limit to 5 topics
    unique_topics = list(set(topics))
    return unique_topics[:5]

def generate_linkedin_posts(text: str, topics: List[str]) -> List[Dict[str, Any]]:
    """Generate LinkedIn post suggestions based on content."""
    posts = []
    
    # Generate a post for each topic (up to 3)
    for topic in topics[:3]:
        post = {
            'title': f"Insights on {topic}",
            'content': f"Looking at recent developments in {topic}, we're seeing impressive advancements that could transform how businesses operate. What are your thoughts on the future of {topic}?",
            'hashtags': [f"#{topic.replace(' ', '')}", "#Innovation", "#ProfessionalDevelopment"]
        }
        posts.append(post)
    
    return posts

def generate_instagram_captions(text: str, topics: List[str]) -> List[Dict[str, Any]]:
    """Generate Instagram caption suggestions based on content."""
    captions = []
    
    # Generate a caption for each topic (up to 2)
    for topic in topics[:2]:
        caption = {
            'caption': f"Exploring the world of {topic} today. Every day brings new opportunities and challenges. #{''.join(topic.split())} #Innovation",
            'image_suggestion': f"Visual representation of {topic} concept with modern, clean aesthetics"
        }
        captions.append(caption)
    
    return captions 
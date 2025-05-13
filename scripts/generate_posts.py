#!/usr/bin/env python3
"""
Generate WordPress blog posts from the fetched news articles.
"""

import os
import json
import time
import random
from datetime import datetime
import html2text
import requests
from bs4 import BeautifulSoup
import markdown

# Create directory for posts
os.makedirs('data/posts', exist_ok=True)

def get_article_content(url):
    """Fetch the full content of an article from its URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unwanted elements
        for element in soup.select('nav, header, footer, aside, .sidebar, .comments, .related-posts, .advertisement, script, style'):
            element.decompose()
        
        # Try to get the main content
        content = None
        for selector in ['article', '.post-content', '.entry-content', '.content', 'main', '.post-body']:
            content = soup.select_one(selector)
            if content:
                break
        
        if not content:
            # If no specific content area found, use the body
            content = soup.body
        
        # Convert HTML to plain text and then to Markdown
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.ignore_tables = False
        h.images_to_alt = False
        h.body_width = 0  # No wrapping
        
        markdown_text = h.handle(str(content))
        
        # Remove excess newlines and whitespace
        markdown_text = '\n'.join([line.rstrip() for line in markdown_text.splitlines() if line.strip()])
        
        return markdown_text
    except Exception as e:
        print(f"Error fetching article content from {url}: {e}")
        return None

def generate_post_content(article, category):
    """Generate a complete blog post content from an article."""
    # Try to get the full content if possible
    full_content = get_article_content(article['link'])
    
    if full_content:
        post_content = full_content
    else:
        # Use summary if we couldn't get the full content
        post_content = article['summary']
    
    # Add attribution and link back to source
    post_content += f"\n\n---\n\nSource: [{article['source']}]({article['link']})\n"
    
    # Add category and tags
    post_content += f"\n\nCategory: {category.capitalize()}\n"
    tags = [category, 'container', 'cloud-native']
    
    if category == 'docker':
        tags.extend(['containers', 'dockerhub', 'docker-compose'])
    elif category == 'kubernetes':
        tags.extend(['k8s', 'cncf', 'cloud-native'])
    
    post_content += f"Tags: {', '.join(tags)}\n"
    
    return post_content

def format_post_title(title, category):
    """Format the post title to make it suitable for a blog."""
    # Add category prefix if not already present
    if category.lower() not in title.lower():
        title = f"{category.capitalize()}: {title}"
    
    # Add date
    today = datetime.now().strftime('%b %d, %Y')
    title = f"{title} - {today}"
    
    return title

def create_post_from_article(article, category, index):
    """Create a complete blog post from an article."""
    # Format title
    title = format_post_title(article['title'], category)
    
    # Generate content
    content = generate_post_content(article, category)
    
    # Create a unique ID for the post
    post_id = f"{category}_{index}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Create post object
    post = {
        'id': post_id,
        'title': title,
        'content': content,
        'excerpt': article['summary'],
        'featured_image': article.get('local_image'),
        'featured_image_url': article.get('image_url'),
        'category': category,
        'tags': [category, 'container', 'cloud-native'],
        'original_url': article['link'],
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Save post to file
    with open(f"data/posts/{post_id}.json", 'w') as f:
        json.dump(post, f, indent=2)
    
    return post

def main():
    """Main function to generate blog posts from the fetched news."""
    all_posts = []
    
    # Define the categories to process
    categories = ['docker', 'kubernetes', 'container']
    
    for category in categories:
        try:
            # Load the news data
            with open(f'data/{category}_news.json', 'r') as f:
                articles = json.load(f)
            
            print(f"Generating posts for category: {category} ({len(articles)} articles)")
            
            # Generate posts for the top 3 articles from each category
            for i, article in enumerate(articles[:3]):
                # Add a small delay to avoid overloading resources
                time.sleep(random.uniform(0.5, 1.5))
                
                post = create_post_from_article(article, category, i)
                all_posts.append(post)
                
                print(f"Created post: {post['title']}")
        except Exception as e:
            print(f"Error processing category {category}: {e}")
    
    # Save all posts to a single file
    with open('data/posts.json', 'w') as f:
        json.dump(all_posts, f, indent=2)
    
    print(f"Generated {len(all_posts)} posts in total.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Publish generated blog posts to WordPress using the WordPress REST API.
"""

import os
import json
import base64
import time
import random
import requests
from datetime import datetime

def upload_image_to_wordpress(image_path, api_url, username, password):
    """Upload an image to WordPress and return the media ID."""
    if not os.path.exists(image_path):
        print(f"Image file not found: {image_path}")
        return None
    
    try:
        # Read image file
        with open(image_path, 'rb') as img_file:
            image_data = img_file.read()
        
        # Get filename
        filename = os.path.basename(image_path)
        
        # Create authorization header
        auth = base64.b64encode(f"{username}:{password}".encode()).decode()
        
        # Set headers
        headers = {
            'Authorization': f'Basic {auth}',
            'Content-Disposition': f'attachment; filename={filename}',
            'Content-Type': 'image/jpeg',  # Adjust if needed based on file type
        }
        
        # Upload image
        response = requests.post(
            f"{api_url}/wp/v2/media",
            headers=headers,
            data=image_data
        )
        
        if response.status_code in (201, 200):
            media_id = response.json().get('id')
            return media_id
        else:
            print(f"Failed to upload image: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error uploading image to WordPress: {e}")
        return None

def get_or_create_category(category_name, api_url, username, password):
    """Get or create a category in WordPress and return its ID."""
    try:
        # Authentication
        auth = base64.b64encode(f"{username}:{password}".encode()).decode()
        headers = {'Authorization': f'Basic {auth}'}
        
        # Check if category exists
        response = requests.get(
            f"{api_url}/wp/v2/categories?search={category_name}",
            headers=headers
        )
        
        if response.status_code == 200:
            categories = response.json()
            for cat in categories:
                if cat['name'].lower() == category_name.lower():
                    return cat['id']
        
        # Create category if not found
        response = requests.post(
            f"{api_url}/wp/v2/categories",
            headers=headers,
            json={'name': category_name.capitalize()}
        )
        
        if response.status_code in (201, 200):
            return response.json().get('id')
        else:
            print(f"Failed to create category: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error getting/creating category: {e}")
        return None

def get_or_create_tag(tag_name, api_url, username, password):
    """Get or create a tag in WordPress and return its ID."""
    try:
        # Authentication
        auth = base64.b64encode(f"{username}:{password}".encode()).decode()
        headers = {'Authorization': f'Basic {auth}'}
        
        # Check if tag exists
        response = requests.get(
            f"{api_url}/wp/v2/tags?search={tag_name}",
            headers=headers
        )
        
        if response.status_code == 200:
            tags = response.json()
            for tag in tags:
                if tag['name'].lower() == tag_name.lower():
                    return tag['id']
        
        # Create tag if not found
        response = requests.post(
            f"{api_url}/wp/v2/tags",
            headers=headers,
            json={'name': tag_name.lower()}
        )
        
        if response.status_code in (201, 200):
            return response.json().get('id')
        else:
            print(f"Failed to create tag: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error getting/creating tag: {e}")
        return None

def publish_post_to_wordpress(post, api_url, username, password):
    """Publish a post to WordPress."""
    try:
        # Authentication
        auth = base64.b64encode(f"{username}:{password}".encode()).decode()
        headers = {
            'Authorization': f'Basic {auth}',
            'Content-Type': 'application/json',
        }
        
        # Upload featured image if available
        featured_media_id = None
        if post.get('featured_image') and os.path.exists(post['featured_image']):
            featured_media_id = upload_image_to_wordpress(
                post['featured_image'], api_url, username, password
            )
            if featured_media_id:
                print(f"Uploaded featured image for post: {post['title']}")
        
        # Get category ID
        category_id = get_or_create_category(post['category'], api_url, username, password)
        
        # Get tag IDs
        tag_ids = []
        for tag in post.get('tags', []):
            tag_id = get_or_create_tag(tag, api_url, username, password)
            if tag_id:
                tag_ids.append(tag_id)
        
        # Prepare post data
        post_data = {
            'title': post['title'],
            'content': post['content'],
            'excerpt': post['excerpt'],
            'status': 'publish',
            'categories': [category_id] if category_id else [],
            'tags': tag_ids,
        }
        
        if featured_media_id:
            post_data['featured_media'] = featured_media_id
        
        # Create post
        response = requests.post(
            f"{api_url}/wp/v2/posts",
            headers=headers,
            json=post_data
        )
        
        if response.status_code in (201, 200):
            wp_post_id = response.json().get('id')
            wp_post_url = response.json().get('link')
            print(f"Published post: {post['title']} - {wp_post_url}")
            
            # Update our post with WordPress post ID and URL
            post['wordpress_id'] = wp_post_id
            post['wordpress_url'] = wp_post_url
            post['published_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Save updated post data
            with open(f"data/posts/{post['id']}.json", 'w') as f:
                json.dump(post, f, indent=2)
            
            return True
        else:
            print(f"Failed to publish post: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Error publishing post to WordPress: {e}")
        return False

def main():
    """Main function to publish posts to WordPress."""
    # Get WordPress credentials from environment variables
    wp_username = os.environ.get('WP_USERNAME')
    wp_password = os.environ.get('WP_PASSWORD')
    wp_api_url = os.environ.get('WP_API_URL')
    
    if not all([wp_username, wp_password, wp_api_url]):
        print("Error: WordPress credentials not provided in environment variables.")
        print("Please set WP_USERNAME, WP_PASSWORD, and WP_API_URL.")
        return
    
    # Ensure the API URL is formatted correctly
    if not wp_api_url.endswith('/wp-json'):
        wp_api_url = wp_api_url.rstrip('/') + '/wp-json'
    
    # Load all posts
    try:
        with open('data/posts.json', 'r') as f:
            all_posts = json.load(f)
    except Exception as e:
        print(f"Error loading posts: {e}")
        return
    
    print(f"Found {len(all_posts)} posts to publish")
    
    # Create a file to track published posts
    published_posts_file = 'data/published_posts.json'
    published_post_ids = set()
    
    # Load previously published posts if file exists
    if os.path.exists(published_posts_file):
        try:
            with open(published_posts_file, 'r') as f:
                published_posts = json.load(f)
                published_post_ids = set(post.get('id') for post in published_posts)
        except Exception as e:
            print(f"Error loading published posts: {e}")
    
    # Publish posts that haven't been published yet
    newly_published = []
    
    for post in all_posts:
        if post['id'] not in published_post_ids:
            # Add a delay between publishing posts
            time.sleep(random.uniform(2, 5))
            
            success = publish_post_to_wordpress(
                post, wp_api_url, wp_username, wp_password
            )
            
            if success:
                newly_published.append(post)
                published_post_ids.add(post['id'])
    
    # Update published posts file
    if newly_published:
        all_published_posts = newly_published
        
        if os.path.exists(published_posts_file):
            try:
                with open(published_posts_file, 'r') as f:
                    existing_published = json.load(f)
                all_published_posts.extend(existing_published)
            except Exception as e:
                print(f"Error reading existing published posts: {e}")
        
        with open(published_posts_file, 'w') as f:
            json.dump(all_published_posts, f, indent=2)
    
    print(f"Published {len(newly_published)} new posts")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Fetch Docker and Kubernetes news from various sources and save to JSON files.
"""

import os
import json
import time
import random
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Create directories if they don't exist
os.makedirs('data', exist_ok=True)
os.makedirs('data/images', exist_ok=True)

# List of Docker and Kubernetes news sources (RSS feeds and websites)
SOURCES = {
    'docker': [
        {'type': 'rss', 'url': 'https://www.docker.com/blog/feed/'},
        {'type': 'rss', 'url': 'https://docs.docker.com/release-notes/feed/'},
        {'type': 'url', 'url': 'https://www.docker.com/blog/'},
    ],
    'kubernetes': [
        {'type': 'rss', 'url': 'https://kubernetes.io/feed.xml'},
        {'type': 'rss', 'url': 'https://www.cncf.io/feed/'},
        {'type': 'url', 'url': 'https://kubernetes.io/blog/'},
    ],
    'container': [
        {'type': 'rss', 'url': 'https://www.linkedin.com/company/docker/rss'},
        {'type': 'rss', 'url': 'https://www.redhat.com/en/rss/blog/channel/kubernetes'},
    ]
}

def fetch_rss_feed(url):
    """Fetch and parse an RSS feed."""
    try:
        feed = feedparser.parse(url)
        articles = []
        
        for entry in feed.entries[:10]:  # Get the latest 10 entries
            # Extract image if available
            image_url = None
            if 'media_content' in entry:
                for media in entry.media_content:
                    if 'url' in media:
                        image_url = media['url']
                        break
            
            # Sometimes images are in the content
            if not image_url and 'content' in entry:
                for content in entry.content:
                    if 'value' in content:
                        soup = BeautifulSoup(content['value'], 'html.parser')
                        img_tag = soup.find('img')
                        if img_tag and 'src' in img_tag.attrs:
                            image_url = img_tag['src']
                            break
            
            # Try to get image from summary
            if not image_url and hasattr(entry, 'summary'):
                soup = BeautifulSoup(entry.summary, 'html.parser')
                img_tag = soup.find('img')
                if img_tag and 'src' in img_tag.attrs:
                    image_url = img_tag['src']
            
            article = {
                'title': entry.title,
                'link': entry.link,
                'published': entry.get('published', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                'summary': entry.get('summary', ''),
                'image_url': image_url,
                'source': url
            }
            articles.append(article)
        
        return articles
    except Exception as e:
        print(f"Error fetching RSS feed {url}: {e}")
        return []

def fetch_website(url):
    """Scrape a website for news articles."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = []
        
        # Look for article elements or blog posts
        # This is a generic approach; you might need to adjust based on the specific website structure
        for article in soup.select('article, .post, .blog-post, .entry')[:10]:
            title_elem = article.select_one('h1, h2, h3, .title, .entry-title')
            link_elem = article.select_one('a')
            summary_elem = article.select_one('p, .summary, .excerpt, .entry-summary')
            image_elem = article.select_one('img')
            
            if title_elem and link_elem:
                title = title_elem.get_text().strip()
                link = link_elem.get('href')
                
                # If link is relative, make it absolute
                if link and not link.startswith(('http://', 'https://')):
                    from urllib.parse import urljoin
                    link = urljoin(url, link)
                
                summary = summary_elem.get_text().strip() if summary_elem else ''
                image_url = None
                
                if image_elem and 'src' in image_elem.attrs:
                    image_url = image_elem['src']
                    # If image URL is relative, make it absolute
                    if image_url and not image_url.startswith(('http://', 'https://')):
                        from urllib.parse import urljoin
                        image_url = urljoin(url, image_url)
                
                article = {
                    'title': title,
                    'link': link,
                    'published': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'summary': summary,
                    'image_url': image_url,
                    'source': url
                }
                articles.append(article)
        
        return articles
    except Exception as e:
        print(f"Error fetching website {url}: {e}")
        return []

def download_image(url, category, title):
    """Download an image and return the local path."""
    if not url:
        return None
    
    try:
        # Create a filename from the title
        import hashlib
        from urllib.parse import unquote
        
        # Get file extension from URL
        file_ext = os.path.splitext(unquote(url.split('?')[0]))[-1]
        if not file_ext or len(file_ext) > 5:  # If no extension or too long (probably not an extension)
            file_ext = '.jpg'
        
        # Create a unique filename based on title and URL
        filename = hashlib.md5(f"{title}_{url}".encode()).hexdigest() + file_ext
        local_path = os.path.join('data', 'images', filename)
        
        # Download the image if it doesn't already exist
        if not os.path.exists(local_path):
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Add a small delay to avoid hitting rate limits
            time.sleep(0.5)
        
        return local_path
    except Exception as e:
        print(f"Error downloading image {url}: {e}")
        return None

def main():
    """Main function to fetch and save news articles."""
    all_articles = {}
    
    for category, sources in SOURCES.items():
        articles = []
        
        for source in sources:
            # Add a small delay between requests to avoid hitting rate limits
            time.sleep(random.uniform(1, 3))
            
            if source['type'] == 'rss':
                source_articles = fetch_rss_feed(source['url'])
            else:  # source['type'] == 'url'
                source_articles = fetch_website(source['url'])
            
            # Download images for each article
            for article in source_articles:
                if article.get('image_url'):
                    local_image = download_image(article['image_url'], category, article['title'])
                    if local_image:
                        article['local_image'] = local_image
            
            articles.extend(source_articles)
        
        # Save articles for this category
        all_articles[category] = articles
        
        # Save to a JSON file
        with open(f'data/{category}_news.json', 'w') as f:
            json.dump(articles, f, indent=2)
    
    # Save all articles to a single file
    with open('data/all_news.json', 'w') as f:
        json.dump(all_articles, f, indent=2)
    
    print(f"Fetched and saved news articles: {sum(len(articles) for articles in all_articles.values())} total articles")

if __name__ == "__main__":
    main()

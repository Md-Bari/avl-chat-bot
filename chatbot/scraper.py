import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import re
import time
import logging
import json
from openai import OpenAI
from django.conf import settings
from chatbot.models import ScrapedPage, PageChunk

logger = logging.getLogger(__name__)

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def chunk_text(text, max_chunk_size=1200):
    paragraphs = text.split('\n')
    chunks = []
    current_chunk = []
    current_len = 0
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        para_len = len(para)
        if para_len > max_chunk_size:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_len = 0
            
            # Split sentences
            sentences = re.split(r'(?<=[.!?])\s+', para)
            for sentence in sentences:
                sentence_len = len(sentence)
                if current_len + sentence_len > max_chunk_size:
                    if current_chunk:
                        chunks.append("\n".join(current_chunk))
                    current_chunk = [sentence]
                    current_len = sentence_len
                else:
                    current_chunk.append(sentence)
                    current_len += sentence_len + (1 if current_len > 0 else 0)
        else:
            if current_len + para_len > max_chunk_size:
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                current_chunk = [para]
                current_len = para_len
            else:
                current_chunk.append(para)
                current_len += para_len + (1 if current_len > 0 else 0)
                
    if current_chunk:
        chunks.append("\n".join(current_chunk))
        
    return chunks

def get_embedding(text, model="text-embedding-3-small"):
    api_key = getattr(settings, 'OPENAI_API_KEY', None)
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not configured in settings.")
    client = OpenAI(api_key=api_key)
    response = client.embeddings.create(input=[text], model=model)
    return response.data[0].embedding

def is_valid_url(url, base_domain):
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc != base_domain:
        return False
        
    path = parsed.path.lower()
    
    # Skip assets/files
    invalid_extensions = ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.pdf', '.zip', '.xml', '.txt', '.php', '.ico']
    if any(path.endswith(ext) for ext in invalid_extensions):
        return False
        
    # Skip WP-specific folders and feeds
    invalid_patterns = ['/wp-content/', '/wp-includes/', '/wp-json/', '/wp-admin/', 'xmlrpc.php', 'oembed', 'replytocom', 'feed', '/author/', '/category/']
    if any(pat in url.lower() for pat in invalid_patterns):
        return False
        
    return True

def scrape_avl_site(start_url="https://avl.com.bd", delay=0.5):
    """
    Crawls https://avl.com.bd recursively and stores the text content in the database.
    Also splits content into chunks and generates OpenAI vector embeddings.
    """
    parsed_start = urllib.parse.urlparse(start_url)
    base_domain = parsed_start.netloc
    
    to_visit = {start_url}
    visited = set()
    scraped_count = 0
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    while to_visit:
        url = to_visit.pop()
        
        # Normalize url by stripping fragment and trailing slash
        normalized_url = url.split('#')[0]
        if normalized_url.endswith('/'):
            normalized_url = normalized_url[:-1]
            
        if normalized_url in visited:
            continue
            
        visited.add(normalized_url)
        print(f"Scraping: {normalized_url}")
        
        try:
            req = urllib.request.Request(normalized_url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                content_type = response.info().get_content_type()
                if 'html' not in content_type:
                    continue
                    
                html_bytes = response.read()
                soup = BeautifulSoup(html_bytes, 'html.parser')
                
                # Decompose scripts and styles
                for el in soup(["script", "style", "noscript"]):
                    el.decompose()
                
                title = soup.title.string.strip() if soup.title else ""
                
                body = soup.find('body')
                if body:
                    text_blocks = []
                    # Extract structure-defining tags
                    for element in body.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'td', 'th']):
                        # Skip if part of header navigation/menu
                        parent_str = ""
                        p = element.parent
                        while p and p.name != 'body':
                            parent_str += f" {p.get('class', '')} {p.get('id', '')}"
                            p = p.parent
                        
                        parent_str = parent_str.lower()
                        if 'nav' in parent_str or 'menu' in parent_str:
                            continue
                            
                        txt = clean_text(element.get_text())
                        if txt:
                            if element.name.startswith('h'):
                                text_blocks.append(f"\n{element.name.upper()}: {txt}")
                            elif element.name == 'li':
                                text_blocks.append(f"- {txt}")
                            else:
                                text_blocks.append(txt)
                                
                    text_content = "\n".join(text_blocks)
                else:
                    text_content = clean_text(soup.get_text())
                
                # Save or update database entry
                page_obj, created = ScrapedPage.objects.update_or_create(
                    url=normalized_url,
                    defaults={
                        'title': title or normalized_url,
                        'content': text_content
                    }
                )
                scraped_count += 1
                
                # Chunk text and generate embeddings
                try:
                    PageChunk.objects.filter(page=page_obj).delete()
                    chunks = chunk_text(text_content)
                    print(f"Chunked into {len(chunks)} sections. Generating embeddings...")
                    for chunk in chunks:
                        emb = get_embedding(chunk)
                        PageChunk.objects.create(
                            page=page_obj,
                            chunk_text=chunk,
                            embedding_json=json.dumps(emb)
                        )
                except Exception as chunk_err:
                    print(f"Failed to generate embeddings for {normalized_url}: {chunk_err}")
                
                # Discover links
                for link in soup.find_all('a', href=True):
                    full_link = urllib.parse.urljoin(normalized_url, link['href'])
                    full_link = full_link.split('#')[0]
                    if full_link.endswith('/'):
                        full_link = full_link[:-1]
                        
                    if is_valid_url(full_link, base_domain) and full_link not in visited:
                        to_visit.add(full_link)
            
            time.sleep(delay)  # Respectful crawling
        except Exception as e:
            print(f"Failed to scrape {normalized_url}: {e}")
            logger.error(f"Failed to scrape {normalized_url}: {e}", exc_info=True)
            
    print(f"Scraping complete. Total pages saved: {scraped_count}")
    return scraped_count


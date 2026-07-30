import urllib.request
import urllib.parse
import os
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

def format_extracted_media_info(name, url):
    clean = name.replace('_', ' ').replace('-', ' ')
    clean = re.sub(r'page\s*\d+', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\bscaled\b', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\b\d+\b', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip(' .()')
    
    if not clean:
        return ""
        
    lower_clean = clean.lower()
    is_cert = 'cert' in url.lower() or any(k in lower_clean for k in ['gots', 'oeko', 'grs', 'ocs', 'rcs', 'bsci', 'sedex', 'compliance', 'audit', 'structural', 'report', 'standard', 'membership'])
    
    if is_cert:
        desc = clean
        if 'gots' in lower_clean and 'global' not in lower_clean:
            desc += " (Global Organic Textile Standard)"
        elif 'oeko' in lower_clean and 'tex' not in lower_clean:
            desc += " (OEKO-TEX Standard 100)"
        elif 'grs' in lower_clean and 'global' not in lower_clean:
            desc += " (Global Recycled Standard)"
        elif 'ocs' in lower_clean and 'organic' not in lower_clean:
            desc += " (Organic Content Standard)"
        elif 'rcs' in lower_clean and 'recycled' not in lower_clean:
            desc += " (Recycled Claim Standard)"
        elif 'bsci' in lower_clean and 'business' not in lower_clean:
            desc += " (Business Social Compliance Initiative)"
        elif 'sedex' in lower_clean and 'supplier' not in lower_clean:
            desc += " (Supplier Ethical Data Exchange)"
        return f"Apparels Village Limited (AVL) holds the certification / membership: {desc}."
    else:
        return f"Page illustration / Image: {clean}."

def chunk_text(text, max_chunk_size=1200):
    paragraphs = text.split('\n')
    chunks = []
    current_chunk = []
    current_len = 0
    
    heading_pattern = re.compile(r'^(H\d:|#+)\s+', re.IGNORECASE)
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        para_len = len(para)
        is_heading = bool(heading_pattern.match(para))
        
        # Split chunk if we encounter a new header and the current chunk has substantial content
        if (is_heading and current_len > 150) or (current_len + para_len > max_chunk_size):
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_len = 0
        
        if para_len > max_chunk_size:
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

def export_pages_to_markdown():
    """
    Reads all ScrapedPage entries from the database and writes them to scraped_content.md in the project root.
    """
    md_path = os.path.join(settings.BASE_DIR, 'scraped_content.md')
    pages = ScrapedPage.objects.all().order_by('url')
    
    print(f"Exporting {pages.count()} pages to {md_path}...")
    with open(md_path, 'w', encoding='utf-8') as f:
        for page in pages:
            f.write(f'<!-- PAGE_START url="{page.url}" title="{page.title}" -->\n')
            f.write(f'# {page.title}\n\n')
            f.write(f'{page.content}\n')
            f.write('<!-- PAGE_END -->\n\n')
    print("Export complete.")

def import_markdown_to_db():
    """
    Reads scraped_content.md, parses the pages, creates semantic chunks, generates vector embeddings,
    and stores them in the PostgreSQL PageChunk table.
    """
    md_path = os.path.join(settings.BASE_DIR, 'scraped_content.md')
    if not os.path.exists(md_path):
        print(f"Error: {md_path} does not exist.")
        return 0
        
    print(f"Importing and embedding pages from {md_path}...")
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    pattern = re.compile(
        r'<!--\s*PAGE_START\s+url="([^"]+)"\s+title="([^"]*)"\s*-->([\s\S]*?)<!--\s*PAGE_END\s*-->',
        re.IGNORECASE
    )
    
    pages_imported = 0
    matches = list(pattern.finditer(content))
    
    for match in matches:
        url = match.group(1)
        title = match.group(2)
        page_content = match.group(3).strip()
        
        # Save or update ScrapedPage model
        page_obj, created = ScrapedPage.objects.update_or_create(
            url=url,
            defaults={
                'title': title or url,
                'content': page_content
            }
        )
        
        # Generate new chunks and embeddings
        PageChunk.objects.filter(page=page_obj).delete()
        chunks = chunk_text(page_content)
        print(f"Generating embeddings for '{title or url}' ({len(chunks)} chunks)...")
        for chunk in chunks:
            try:
                emb = get_embedding(chunk)
                PageChunk.objects.create(
                    page=page_obj,
                    chunk_text=chunk,
                    embedding=emb
                )
            except Exception as e:
                print(f"Failed to generate embedding for chunk in {url}: {e}")
                
        pages_imported += 1
        
    print(f"Import complete. Embedded {pages_imported} pages.")
    return pages_imported

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
                    extra_info_extracted = set()

                    # Extract structure-defining tags
                    for element in body.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'td', 'th']):
                        # Skip if part of header navigation, menu, or footer
                        parent_str = ""
                        p = element.parent
                        while p and p.name != 'body':
                            parent_str += f" {p.get('class', '')} {p.get('id', '')}"
                            p = p.parent
                        
                        parent_str = parent_str.lower()
                        if 'nav' in parent_str or 'menu' in parent_str or 'footer' in parent_str:
                            continue
                            
                        # Get main text of this element
                        txt = element.get_text().strip()
                        
                        # Check for any lightbox title or img alt inside this element or on this element
                        extra_details = []
                        for sub_el in [element] + list(element.find_all(True)):
                            lb_title = sub_el.get('data-elementor-lightbox-title')
                            if lb_title and lb_title not in txt:
                                formatted = format_extracted_media_info(lb_title, normalized_url)
                                if formatted and formatted not in txt and formatted not in extra_details:
                                    extra_details.append(formatted)
                                    extra_info_extracted.add(sub_el)
                            
                            if sub_el.name == 'img':
                                alt = sub_el.get('alt')
                                img_title = sub_el.get('title')
                                if alt and alt not in txt:
                                    formatted = format_extracted_media_info(alt, normalized_url)
                                    if formatted and formatted not in txt and formatted not in extra_details:
                                        extra_details.append(formatted)
                                        extra_info_extracted.add(sub_el)
                                elif img_title and img_title not in txt:
                                    formatted = format_extracted_media_info(img_title, normalized_url)
                                    if formatted and formatted not in txt and formatted not in extra_details:
                                        extra_details.append(formatted)
                                        extra_info_extracted.add(sub_el)
                                    
                        if extra_details:
                            txt = f"{txt}\n" + "\n".join(extra_details)
                            
                        txt = clean_text(txt)
                        if txt:
                            if element.name.startswith('h'):
                                text_blocks.append(f"\n{element.name.upper()}: {txt}")
                            elif element.name == 'li':
                                text_blocks.append(f"- {txt}")
                            else:
                                text_blocks.append(txt)
                                
                    # Extract remaining elements with data-elementor-lightbox-title or images that weren't captured
                    for element in body.find_all(lambda tag: tag.get('data-elementor-lightbox-title') or tag.name == 'img'):
                        if element in extra_info_extracted:
                            continue
                            
                        # Skip if part of header navigation, menu, or footer
                        parent_str = ""
                        p = element.parent
                        while p and p.name != 'body':
                            parent_str += f" {p.get('class', '')} {p.get('id', '')}"
                            p = p.parent
                        
                        parent_str = parent_str.lower()
                        if 'nav' in parent_str or 'menu' in parent_str or 'footer' in parent_str:
                            continue
                            
                        txt = ""
                        if element.name == 'img':
                            alt = element.get('alt')
                            img_title = element.get('title')
                            if alt:
                                txt = format_extracted_media_info(alt, normalized_url)
                            elif img_title:
                                txt = format_extracted_media_info(img_title, normalized_url)
                        else:
                            lb_title = element.get('data-elementor-lightbox-title')
                            txt = format_extracted_media_info(lb_title, normalized_url)
                            
                        txt = clean_text(txt)
                        if txt:
                            text_blocks.append(txt)
                            extra_info_extracted.add(element)
                                
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
    
    # Step 1: Export all crawled text to scraped_content.md
    export_pages_to_markdown()
    
    # Step 2: Import from markdown file, chunk, embed, and store in PostgreSQL
    import_markdown_to_db()
    
    return scraped_count


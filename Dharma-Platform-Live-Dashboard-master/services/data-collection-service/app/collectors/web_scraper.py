"""
Web scraping engine with respectful rate limiting
"""
import asyncio
import time
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from urllib.parse import urljoin, urlparse, robots
from urllib.robotparser import RobotFileParser
import aiohttp
from bs4 import BeautifulSoup
import structlog

from app.models.requests import WebScrapingRequest
from app.core.kafka_producer import KafkaDataProducer

logger = structlog.get_logger()


class DomainRateLimiter:
    """Domain-specific rate limiting"""
    
    def __init__(self):
        self.domain_requests = {}
        self.default_delay = 1.0  # Default 1 second between requests
        self.domain_delays = {
            # Respectful delays for different domains
            'news.google.com': 2.0,
            'twitter.com': 3.0,
            'facebook.com': 3.0,
            'reddit.com': 2.0
        }
    
    async def wait_for_domain(self, domain: str):
        """Wait appropriate time for domain"""
        delay = self.domain_delays.get(domain, self.default_delay)
        
        if domain in self.domain_requests:
            last_request = self.domain_requests[domain]
            elapsed = time.time() - last_request
            if elapsed < delay:
                wait_time = delay - elapsed
                logger.info(f"Rate limiting for {domain}, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
        
        self.domain_requests[domain] = time.time()


class RobotsParser:
    """Robots.txt parser and compliance checker"""
    
    def __init__(self):
        self.robots_cache = {}
        self.user_agent = "DharmaBot/1.0 (+https://project-dharma.ai/bot)"
    
    async def can_fetch(self, url: str, session: aiohttp.ClientSession) -> bool:
        """Check if URL can be fetched according to robots.txt"""
        try:
            parsed_url = urlparse(url)
            domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
            robots_url = urljoin(domain, '/robots.txt')
            
            if domain not in self.robots_cache:
                try:
                    async with session.get(robots_url, timeout=10) as response:
                        if response.status == 200:
                            robots_content = await response.text()
                            rp = RobotFileParser()
                            rp.set_url(robots_url)
                            rp.read_from_lines(robots_content.splitlines())
                            self.robots_cache[domain] = rp
                        else:
                            # If robots.txt not found, assume allowed
                            self.robots_cache[domain] = None
                except Exception as e:
                    logger.warning(f"Failed to fetch robots.txt for {domain}: {e}")
                    self.robots_cache[domain] = None
            
            robots_parser = self.robots_cache[domain]
            if robots_parser:
                return robots_parser.can_fetch(self.user_agent, url)
            else:
                return True  # Allow if no robots.txt or error
                
        except Exception as e:
            logger.error(f"Error checking robots.txt for {url}: {e}")
            return True  # Allow on error


class ContentExtractor:
    """Content extraction using BeautifulSoup"""
    
    def __init__(self):
        self.article_selectors = [
            'article',
            '[role="main"]',
            '.content',
            '.article-content',
            '.post-content',
            '.entry-content',
            '#content',
            '.main-content'
        ]
        
        self.title_selectors = [
            'h1',
            '.title',
            '.headline',
            '.article-title',
            '.post-title'
        ]
    
    def extract_content(self, html: str, url: str) -> Dict[str, Any]:
        """Extract structured content from HTML"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "aside"]):
                script.decompose()
            
            # Extract title
            title = self._extract_title(soup)
            
            # Extract main content
            content = self._extract_main_content(soup)
            
            # Extract metadata
            metadata = self._extract_metadata(soup)
            
            # Extract links
            links = self._extract_links(soup, url)
            
            # Extract images
            images = self._extract_images(soup, url)
            
            return {
                "url": url,
                "title": title,
                "content": content,
                "metadata": metadata,
                "links": links,
                "images": images,
                "word_count": len(content.split()) if content else 0,
                "extracted_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to extract content from {url}: {e}")
            return {
                "url": url,
                "title": "",
                "content": "",
                "metadata": {},
                "links": [],
                "images": [],
                "word_count": 0,
                "error": str(e),
                "extracted_at": datetime.utcnow().isoformat()
            }
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title"""
        # Try meta title first
        meta_title = soup.find('meta', property='og:title')
        if meta_title and meta_title.get('content'):
            return meta_title['content'].strip()
        
        # Try title tag
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()
        
        # Try h1 or other title selectors
        for selector in self.title_selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text().strip()
        
        return ""
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main article content"""
        # Try article selectors
        for selector in self.article_selectors:
            elements = soup.select(selector)
            if elements:
                # Get the largest content block
                largest_element = max(elements, key=lambda x: len(x.get_text()))
                return largest_element.get_text(separator=' ', strip=True)
        
        # Fallback to body content
        body = soup.find('body')
        if body:
            return body.get_text(separator=' ', strip=True)
        
        return soup.get_text(separator=' ', strip=True)
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract page metadata"""
        metadata = {}
        
        # Meta tags
        meta_tags = soup.find_all('meta')
        for tag in meta_tags:
            if tag.get('name'):
                metadata[tag['name']] = tag.get('content', '')
            elif tag.get('property'):
                metadata[tag['property']] = tag.get('content', '')
        
        # Language
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            metadata['language'] = html_tag['lang']
        
        return metadata
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract all links from page"""
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(base_url, href)
            links.append({
                "url": absolute_url,
                "text": link.get_text(strip=True),
                "title": link.get('title', '')
            })
        return links
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract all images from page"""
        images = []
        for img in soup.find_all('img', src=True):
            src = img['src']
            absolute_url = urljoin(base_url, src)
            images.append({
                "url": absolute_url,
                "alt": img.get('alt', ''),
                "title": img.get('title', '')
            })
        return images


class WebScraper:
    """Web scraping engine with respectful rate limiting"""
    
    def __init__(self):
        self.rate_limiter = DomainRateLimiter()
        self.robots_parser = RobotsParser()
        self.content_extractor = ContentExtractor()
        self.visited_urls: Set[str] = set()
        
        # Default headers to appear as regular browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    async def start_scraping(self, request: WebScrapingRequest, 
                           kafka_producer: KafkaDataProducer):
        """Start web scraping based on request parameters"""
        try:
            logger.info(f"Starting web scraping for {len(request.urls)} URLs")
            
            # Create session with custom headers
            headers = self.headers.copy()
            if request.custom_headers:
                headers.update(request.custom_headers)
            
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=2)
            
            async with aiohttp.ClientSession(
                headers=headers,
                timeout=timeout,
                connector=connector
            ) as session:
                
                scraped_count = 0
                for url in request.urls:
                    if scraped_count >= (request.max_results or 1000):
                        break
                    
                    try:
                        # Scrape URL and follow links if requested
                        scraped_data = await self._scrape_url_recursive(
                            session, url, request, 0
                        )
                        
                        for data in scraped_data:
                            await kafka_producer.send_data("web", data, request.collection_id)
                            scraped_count += 1
                        
                        if scraped_count % 10 == 0:
                            logger.info(f"Scraped {scraped_count} pages")
                            
                    except Exception as e:
                        logger.error(f"Failed to scrape {url}: {e}")
                        continue
                
                logger.info(f"Web scraping completed. Total pages: {scraped_count}")
                
        except Exception as e:
            logger.error("Failed to start web scraping", error=str(e))
            raise
    
    async def _scrape_url_recursive(self, session: aiohttp.ClientSession, 
                                  url: str, request: WebScrapingRequest, 
                                  depth: int) -> List[Dict[str, Any]]:
        """Recursively scrape URL and follow links"""
        results = []
        
        if depth > request.max_depth or url in self.visited_urls:
            return results
        
        try:
            # Check robots.txt compliance
            if request.respect_robots_txt:
                if not await self.robots_parser.can_fetch(url, session):
                    logger.info(f"Robots.txt disallows scraping: {url}")
                    return results
            
            # Rate limiting
            domain = urlparse(url).netloc
            await self.rate_limiter.wait_for_domain(domain)
            
            # Mark as visited
            self.visited_urls.add(url)
            
            # Fetch page
            async with session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return results
                
                content_type = response.headers.get('content-type', '').lower()
                if 'text/html' not in content_type:
                    logger.info(f"Skipping non-HTML content: {url}")
                    return results
                
                html = await response.text()
            
            # Extract content
            extracted_data = self.content_extractor.extract_content(html, url)
            extracted_data['depth'] = depth
            extracted_data['content_type'] = 'webpage'
            results.append(extracted_data)
            
            # Follow links if requested and not at max depth
            if request.follow_links and depth < request.max_depth:
                links = extracted_data.get('links', [])
                
                # Filter links to same domain or allowed domains
                same_domain_links = [
                    link['url'] for link in links
                    if urlparse(link['url']).netloc == domain
                    and link['url'] not in self.visited_urls
                ]
                
                # Limit number of links to follow
                for link_url in same_domain_links[:5]:  # Max 5 links per page
                    try:
                        child_results = await self._scrape_url_recursive(
                            session, link_url, request, depth + 1
                        )
                        results.extend(child_results)
                    except Exception as e:
                        logger.error(f"Failed to scrape child URL {link_url}: {e}")
                        continue
            
            return results
            
        except asyncio.TimeoutError:
            logger.warning(f"Timeout scraping {url}")
            return results
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return results
    
    async def monitor_news_sites(self, news_urls: List[str]) -> List[Dict[str, Any]]:
        """Monitor news sites for new articles"""
        try:
            articles = []
            
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout
            ) as session:
                
                for url in news_urls:
                    try:
                        domain = urlparse(url).netloc
                        await self.rate_limiter.wait_for_domain(domain)
                        
                        async with session.get(url) as response:
                            if response.status == 200:
                                html = await response.text()
                                article_data = self.content_extractor.extract_content(html, url)
                                article_data['content_type'] = 'news_article'
                                article_data['source_domain'] = domain
                                articles.append(article_data)
                                
                    except Exception as e:
                        logger.error(f"Failed to monitor news site {url}: {e}")
                        continue
            
            return articles
            
        except Exception as e:
            logger.error("Failed to monitor news sites", error=str(e))
            return []
    
    async def monitor_blogs(self, blog_urls: List[str]) -> List[Dict[str, Any]]:
        """Monitor blog feeds for new content"""
        try:
            blog_posts = []
            
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout
            ) as session:
                
                for url in blog_urls:
                    try:
                        domain = urlparse(url).netloc
                        await self.rate_limiter.wait_for_domain(domain)
                        
                        # Check if it's an RSS feed
                        if url.endswith('.xml') or 'rss' in url.lower() or 'feed' in url.lower():
                            posts = await self._parse_rss_feed(session, url)
                            blog_posts.extend(posts)
                        else:
                            # Regular blog page
                            async with session.get(url) as response:
                                if response.status == 200:
                                    html = await response.text()
                                    post_data = self.content_extractor.extract_content(html, url)
                                    post_data['content_type'] = 'blog_post'
                                    post_data['source_domain'] = domain
                                    blog_posts.append(post_data)
                                    
                    except Exception as e:
                        logger.error(f"Failed to monitor blog {url}: {e}")
                        continue
            
            return blog_posts
            
        except Exception as e:
            logger.error("Failed to monitor blogs", error=str(e))
            return []
    
    async def _parse_rss_feed(self, session: aiohttp.ClientSession, 
                            feed_url: str) -> List[Dict[str, Any]]:
        """Parse RSS feed for blog posts"""
        try:
            async with session.get(feed_url) as response:
                if response.status != 200:
                    return []
                
                xml_content = await response.text()
                soup = BeautifulSoup(xml_content, 'xml')
                
                posts = []
                items = soup.find_all('item')
                
                for item in items[:10]:  # Limit to 10 most recent
                    title = item.find('title')
                    link = item.find('link')
                    description = item.find('description')
                    pub_date = item.find('pubDate')
                    
                    post_data = {
                        "url": link.text if link else feed_url,
                        "title": title.text if title else "",
                        "content": description.text if description else "",
                        "published_at": pub_date.text if pub_date else "",
                        "content_type": "rss_item",
                        "source_feed": feed_url,
                        "extracted_at": datetime.utcnow().isoformat()
                    }
                    posts.append(post_data)
                
                return posts
                
        except Exception as e:
            logger.error(f"Failed to parse RSS feed {feed_url}: {e}")
            return []
    
    def clear_visited_urls(self):
        """Clear visited URLs cache"""
        self.visited_urls.clear()
        logger.info("Cleared visited URLs cache")
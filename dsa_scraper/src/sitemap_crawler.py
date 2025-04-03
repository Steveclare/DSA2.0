import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
from typing import Dict, List, Set, Optional
import re
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import xml.etree.ElementTree as ET

@dataclass
class RegionInfo:
    name: str
    url: str
    parent_region: Optional[str] = None
    distance_from_san_diego: Optional[float] = None
    is_neighboring: bool = False

class SitemapCrawler:
    def __init__(self, base_url: str, max_workers: int = 5):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.visited_urls: Set[str] = set()
        self.regions: Dict[str, RegionInfo] = {}
        self.max_workers = max_workers
        self.logger = logging.getLogger(__name__)

    def _is_valid_url(self, url: str) -> bool:
        """Validate if URL belongs to the target domain."""
        try:
            parsed = urlparse(url)
            return parsed.netloc == urlparse(self.base_url).netloc
        except Exception as e:
            self.logger.error(f"Error validating URL {url}: {str(e)}")
            return False

    def _get_neighboring_regions(self) -> List[RegionInfo]:
        """
        Identify regions neighboring San Diego based on geographical data
        and site structure.
        """
        san_diego_neighbors = [
            "La Mesa", "El Cajon", "Chula Vista", "National City",
            "Coronado", "Imperial Beach", "Lemon Grove", "Santee",
            "Poway", "Del Mar", "Solana Beach", "Encinitas",
            "Carlsbad", "Oceanside", "Vista", "San Marcos",
            "Escondido", "Spring Valley", "Bonita", "Alpine"
        ]
        
        neighboring_regions = []
        for region in san_diego_neighbors:
            try:
                # Construct search URL for each region
                search_url = f"{self.base_url}/search?q={region.replace(' ', '+')}"
                response = self.session.get(search_url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    # Look for region-specific links or content
                    region_links = soup.find_all('a', href=re.compile(f".*{region.lower().replace(' ', '-')}.*"))
                    
                    if region_links:
                        region_url = urljoin(self.base_url, region_links[0]['href'])
                        region_info = RegionInfo(
                            name=region,
                            url=region_url,
                            is_neighboring=True
                        )
                        neighboring_regions.append(region_info)
                        self.regions[region] = region_info
            except Exception as e:
                self.logger.error(f"Error processing region {region}: {str(e)}")
                
        return neighboring_regions

    def extract_sitemap(self) -> Dict[str, List[str]]:
        """
        Extract and parse the website's sitemap, focusing on regional pages.
        Returns a dictionary mapping regions to their related URLs.
        """
        sitemap = {}
        try:
            # Try to fetch robots.txt first
            robots_txt = self.session.get(urljoin(self.base_url, '/robots.txt'))
            sitemap_url = None
            
            if robots_txt.status_code == 200:
                # Look for Sitemap directive in robots.txt
                for line in robots_txt.text.split('\n'):
                    if line.lower().startswith('sitemap:'):
                        sitemap_url = line.split(':', 1)[1].strip()
                        break
            
            if sitemap_url:
                response = self.session.get(sitemap_url)
                if response.status_code == 200:
                    # Parse XML sitemap
                    root = ET.fromstring(response.content)
                    for url in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                        loc = url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                        if loc is not None:
                            page_url = loc.text
                            # Categorize URLs by region
                            region_match = re.search(r'/region/([^/]+)', page_url)
                            if region_match:
                                region = region_match.group(1).replace('-', ' ').title()
                                if region not in sitemap:
                                    sitemap[region] = []
                                sitemap[region].append(page_url)
            
            # Fallback to crawling if no sitemap found
            if not sitemap:
                self._crawl_for_regions()
                
        except Exception as e:
            self.logger.error(f"Error extracting sitemap: {str(e)}")
        
        return sitemap

    def _crawl_for_regions(self):
        """
        Fallback method to crawl the website for region information
        when sitemap is not available.
        """
        try:
            response = self.session.get(self.base_url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Look for region navigation or links
                region_links = soup.find_all('a', href=re.compile(r'/region/|/area/|/location/'))
                
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    executor.map(self._process_region_link, region_links)
        except Exception as e:
            self.logger.error(f"Error during region crawling: {str(e)}")

    def _process_region_link(self, link):
        """Process individual region links found during crawling."""
        try:
            url = urljoin(self.base_url, link['href'])
            if url not in self.visited_urls and self._is_valid_url(url):
                self.visited_urls.add(url)
                region_name = link.text.strip()
                if region_name:
                    self.regions[region_name] = RegionInfo(
                        name=region_name,
                        url=url
                    )
        except Exception as e:
            self.logger.error(f"Error processing region link: {str(e)}")

    def get_region_data(self, region_info: RegionInfo) -> Dict:
        """
        Fetch and parse data for a specific region.
        """
        data = {
            'name': region_info.name,
            'url': region_info.url,
            'listings': [],
            'stats': {}
        }
        
        try:
            response = self.session.get(region_info.url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Extract listings
                listings = soup.find_all('div', class_=re.compile(r'listing|property|item'))
                for listing in listings:
                    listing_data = self._parse_listing(listing)
                    if listing_data:
                        data['listings'].append(listing_data)
                
                # Extract regional statistics
                stats_section = soup.find('div', class_=re.compile(r'stats|statistics|metrics'))
                if stats_section:
                    data['stats'] = self._parse_statistics(stats_section)
        except Exception as e:
            self.logger.error(f"Error fetching data for region {region_info.name}: {str(e)}")
        
        return data

    def _parse_listing(self, listing_element) -> Dict:
        """Parse individual listing data from HTML element."""
        try:
            return {
                'title': listing_element.find('h2').text.strip() if listing_element.find('h2') else '',
                'price': listing_element.find(text=re.compile(r'\$[\d,]+')) or '',
                'description': listing_element.find('p', class_=re.compile(r'description|details')).text.strip() if listing_element.find('p', class_=re.compile(r'description|details')) else '',
                'url': urljoin(self.base_url, listing_element.find('a')['href']) if listing_element.find('a') else ''
            }
        except Exception:
            return {}

    def _parse_statistics(self, stats_element) -> Dict:
        """Parse regional statistics from HTML element."""
        stats = {}
        try:
            # Look for common statistical patterns
            price_pattern = re.compile(r'\$[\d,]+')
            number_pattern = re.compile(r'\d+')
            
            stats_text = stats_element.get_text()
            
            # Extract median price
            median_price = price_pattern.search(stats_text)
            if median_price:
                stats['median_price'] = median_price.group()
            
            # Extract number of listings
            listings_count = number_pattern.search(stats_text)
            if listings_count:
                stats['total_listings'] = listings_count.group()
        except Exception:
            pass
        
        return stats 
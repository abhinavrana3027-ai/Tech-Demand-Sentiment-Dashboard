import requests
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import time
from urllib.parse import urlencode
import gzip
import json

logger = logging.getLogger(__name__)

class StackOverflowCollector:
    """
    Collector for Stack Overflow data using the Stack Exchange API.
    Fetches tags, questions, and aggregated statistics for technology demand analysis.
    """
    
    BASE_URL = "https://api.stackexchange.com/2.3"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Stack Overflow collector.
        
        Args:
            api_key: Optional Stack Exchange API key for higher rate limits
        """
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'TechDemandSentimentDashboard/1.0'
        })
        self.rate_limit_remaining = 300
        self.rate_limit_reset = None
        
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make API request with rate limiting and error handling.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            API response data
        """
        if self.api_key:
            params['key'] = self.api_key
            
        params['site'] = 'stackoverflow'
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            
            # Update rate limit info
            self.rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
            
            if response.status_code == 429:
                logger.warning("Rate limit exceeded, waiting...")
                time.sleep(60)
                return self._make_request(endpoint, params)
                
            response.raise_for_status()
            
            # Handle gzipped response
            if response.headers.get('Content-Encoding') == 'gzip':
                data = json.loads(gzip.decompress(response.content))
            else:
                data = response.json()
                
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return {'items': [], 'has_more': False}
            
    def get_top_tags(self, page_size: int = 100, min_count: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch top technology tags from Stack Overflow.
        
        Args:
            page_size: Number of tags to fetch
            min_count: Minimum tag count threshold
            
        Returns:
            List of tag dictionaries with statistics
        """
        logger.info(f"Fetching top {page_size} tags...")
        
        params = {
            'order': 'desc',
            'sort': 'popular',
            'pagesize': page_size,
            'min': min_count,
            'filter': 'default'
        }
        
        response = self._make_request('/tags', params)
        tags = response.get('items', [])
        
        logger.info(f"Retrieved {len(tags)} tags")
        return tags
        
    def get_tag_questions(self, tag: str, fromdate: Optional[datetime] = None,
                         todate: Optional[datetime] = None,
                         page_size: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch questions for a specific tag within date range.
        
        Args:
            tag: Technology tag name
            fromdate: Start date for filtering
            todate: End date for filtering
            page_size: Number of questions per page
            
        Returns:
            List of question dictionaries
        """
        if fromdate is None:
            fromdate = datetime.now() - timedelta(days=30)
        if todate is None:
            todate = datetime.now()
            
        params = {
            'order': 'desc',
            'sort': 'activity',
            'tagged': tag,
            'fromdate': int(fromdate.timestamp()),
            'todate': int(todate.timestamp()),
            'pagesize': page_size,
            'filter': 'withbody'
        }
        
        response = self._make_request('/questions', params)
        questions = response.get('items', [])
        
        logger.info(f"Retrieved {len(questions)} questions for tag '{tag}'")
        return questions
        
    def get_tag_stats_timeseries(self, tags: List[str],
                                 days_back: int = 90) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get time series statistics for multiple tags.
        
        Args:
            tags: List of tag names
            days_back: Number of days to look back
            
        Returns:
            Dictionary mapping tags to their time series data
        """
        logger.info(f"Fetching time series for {len(tags)} tags over {days_back} days")
        
        results = {}
        end_date = datetime.now()
        
        for tag in tags:
            tag_data = []
            
            # Sample weekly intervals
            for week in range(days_back // 7):
                week_end = end_date - timedelta(days=week*7)
                week_start = week_end - timedelta(days=7)
                
                params = {
                    'tagged': tag,
                    'fromdate': int(week_start.timestamp()),
                    'todate': int(week_end.timestamp()),
                    'filter': '!9Z(-wwYGT'
                }
                
                response = self._make_request('/questions', params)
                
                tag_data.append({
                    'date': week_start.isoformat(),
                    'count': response.get('total', 0),
                    'tag': tag
                })
                
                # Respect rate limits
                if self.rate_limit_remaining < 10:
                    logger.warning("Approaching rate limit, pausing...")
                    time.sleep(2)
                    
            results[tag] = tag_data
            
        return results
        
    def get_tag_synonyms(self, tag: str) -> List[str]:
        """
        Get synonym tags for a given tag.
        
        Args:
            tag: Tag name
            
        Returns:
            List of synonym tag names
        """
        params = {'filter': 'default'}
        response = self._make_request(f'/tags/{tag}/synonyms', params)
        
        synonyms = [item.get('to_tag', '') for item in response.get('items', [])]
        return synonyms
        
    def search_questions(self, query: str, tags: Optional[List[str]] = None,
                        fromdate: Optional[datetime] = None,
                        page_size: int = 100) -> List[Dict[str, Any]]:
        """
        Search questions by query string and optional tags.
        
        Args:
            query: Search query
            tags: Optional list of tags to filter by
            fromdate: Optional start date
            page_size: Results per page
            
        Returns:
            List of matching questions
        """
        if fromdate is None:
            fromdate = datetime.now() - timedelta(days=30)
            
        params = {
            'order': 'desc',
            'sort': 'relevance',
            'q': query,
            'fromdate': int(fromdate.timestamp()),
            'pagesize': page_size,
            'filter': 'withbody'
        }
        
        if tags:
            params['tagged'] = ';'.join(tags)
            
        response = self._make_request('/search', params)
        return response.get('items', [])
        
    def get_tech_demand_metrics(self, tech_list: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Calculate comprehensive demand metrics for list of technologies.
        
        Args:
            tech_list: List of technology names/tags
            
        Returns:
            Dictionary mapping technologies to their metrics
        """
        logger.info(f"Calculating demand metrics for {len(tech_list)} technologies")
        
        metrics = {}
        
        for tech in tech_list:
            try:
                # Get recent questions
                recent_questions = self.get_tag_questions(
                    tech,
                    fromdate=datetime.now() - timedelta(days=7)
                )
                
                # Get tag info
                tag_info_response = self._make_request(f'/tags/{tech}/info', params={})
                tag_info = tag_info_response.get('items', [{}])[0]
                
                metrics[tech] = {
                    'total_questions': tag_info.get('count', 0),
                    'recent_questions': len(recent_questions),
                    'avg_score': sum(q.get('score', 0) for q in recent_questions) / max(len(recent_questions), 1),
                    'avg_answers': sum(q.get('answer_count', 0) for q in recent_questions) / max(len(recent_questions), 1),
                    'avg_views': sum(q.get('view_count', 0) for q in recent_questions) / max(len(recent_questions), 1),
                    'last_activity': tag_info.get('last_activity_date'),
                    'timestamp': datetime.now().isoformat()
                }
                
                logger.info(f"Metrics calculated for {tech}")
                
                # Rate limit management
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error calculating metrics for {tech}: {e}")
                metrics[tech] = None
                
        return metrics

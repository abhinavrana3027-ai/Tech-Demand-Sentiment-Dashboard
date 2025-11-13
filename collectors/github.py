import requests
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)

class GitHubCollector:
    """
    Collector for GitHub data using the GitHub REST API.
    Fetches repository statistics, trending repos, and language popularity.
    """
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub collector.
        
        Args:
            token: Optional GitHub personal access token for higher rate limits
        """
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'TechDemandSentimentDashboard/1.0'
        })
        
        if self.token:
            self.session.headers['Authorization'] = f'token {self.token}'
            
        self.rate_limit_remaining = 60
        self.rate_limit_reset = None
        
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make API request with rate limiting and error handling.
        
        Args:
            endpoint: API endpoint path
            params: Optional query parameters
            
        Returns:
            API response data
        """
        if params is None:
            params = {}
            
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            
            # Update rate limit info
            self.rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
            reset_timestamp = response.headers.get('X-RateLimit-Reset')
            if reset_timestamp:
                self.rate_limit_reset = datetime.fromtimestamp(int(reset_timestamp))
                
            if response.status_code == 403:
                logger.warning("Rate limit exceeded, waiting...")
                if self.rate_limit_reset:
                    wait_time = (self.rate_limit_reset - datetime.now()).total_seconds()
                    time.sleep(max(wait_time, 60))
                else:
                    time.sleep(60)
                return self._make_request(endpoint, params)
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return {}
            
    def search_repositories(self, language: str, min_stars: int = 100,
                           created_after: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Search repositories by language and stars.
        
        Args:
            language: Programming language
            min_stars: Minimum star count
            created_after: Filter repos created after this date
            
        Returns:
            List of repository data
        """
        query_parts = [f'language:{language}', f'stars:>={min_stars}']
        
        if created_after:
            date_str = created_after.strftime('%Y-%m-%d')
            query_parts.append(f'created:>={date_str}')
            
        query = ' '.join(query_parts)
        params = {
            'q': query,
            'sort': 'stars',
            'order': 'desc',
            'per_page': 100
        }
        
        response = self._make_request('/search/repositories', params)
        repos = response.get('items', [])
        
        logger.info(f"Found {len(repos)} repositories for {language}")
        return repos
        
    def get_language_stats(self, languages: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for multiple programming languages.
        
        Args:
            languages: List of programming language names
            
        Returns:
            Dictionary mapping languages to their statistics
        """
        logger.info(f"Fetching stats for {len(languages)} languages")
        
        stats = {}
        
        for language in languages:
            try:
                # Search for repos with language
                repos = self.search_repositories(language, min_stars=10)
                
                if repos:
                    total_stars = sum(repo.get('stargazers_count', 0) for repo in repos)
                    total_forks = sum(repo.get('forks_count', 0) for repo in repos)
                    total_watchers = sum(repo.get('watchers_count', 0) for repo in repos)
                    avg_stars = total_stars / len(repos)
                    
                    # Get recent activity (repos created in last 30 days)
                    recent_date = datetime.now() - timedelta(days=30)
                    recent_repos = [r for r in repos if datetime.strptime(
                        r.get('created_at', ''), '%Y-%m-%dT%H:%M:%SZ'
                    ) > recent_date] if repos else []
                    
                    stats[language] = {
                        'total_repos': len(repos),
                        'total_stars': total_stars,
                        'total_forks': total_forks,
                        'total_watchers': total_watchers,
                        'avg_stars': avg_stars,
                        'recent_repos': len(recent_repos),
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    logger.info(f"Stats calculated for {language}")
                else:
                    stats[language] = None
                    
                # Rate limit management
                if self.rate_limit_remaining < 10:
                    logger.warning("Approaching rate limit, pausing...")
                    time.sleep(5)
                    
            except Exception as e:
                logger.error(f"Error calculating stats for {language}: {e}")
                stats[language] = None
                
        return stats
        
    def get_trending_repos(self, language: Optional[str] = None,
                          since: str = 'daily') -> List[Dict[str, Any]]:
        """
        Get trending repositories.
        
        Args:
            language: Optional language filter
            since: Time period ('daily', 'weekly', 'monthly')
            
        Returns:
            List of trending repositories
        """
        # Calculate date range based on 'since' parameter
        days_map = {'daily': 1, 'weekly': 7, 'monthly': 30}
        days_back = days_map.get(since, 7)
        
        created_after = datetime.now() - timedelta(days=days_back)
        query_parts = [f'created:>={created_after.strftime("%Y-%m-%d")}']
        
        if language:
            query_parts.append(f'language:{language}')
            
        query = ' '.join(query_parts)
        params = {
            'q': query,
            'sort': 'stars',
            'order': 'desc',
            'per_page': 50
        }
        
        response = self._make_request('/search/repositories', params)
        return response.get('items', [])
        
    def get_repository_details(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Repository details
        """
        endpoint = f'/repos/{owner}/{repo}'
        return self._make_request(endpoint)
        
    def get_repository_languages(self, owner: str, repo: str) -> Dict[str, int]:
        """
        Get language breakdown for a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Dictionary mapping languages to bytes of code
        """
        endpoint = f'/repos/{owner}/{repo}/languages'
        return self._make_request(endpoint)
        
    def get_tech_popularity_metrics(self, tech_list: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Calculate comprehensive popularity metrics for technologies.
        
        Args:
            tech_list: List of technology names
            
        Returns:
            Dictionary mapping technologies to metrics
        """
        logger.info(f"Calculating popularity metrics for {len(tech_list)} technologies")
        
        metrics = {}
        
        for tech in tech_list:
            try:
                # Search repos mentioning the technology
                params = {
                    'q': tech,
                    'sort': 'stars',
                    'per_page': 100
                }
                
                response = self._make_request('/search/repositories', params)
                repos = response.get('items', [])
                
                if repos:
                    # Calculate metrics
                    total_stars = sum(r.get('stargazers_count', 0) for r in repos)
                    total_forks = sum(r.get('forks_count', 0) for r in repos)
                    open_issues = sum(r.get('open_issues_count', 0) for r in repos)
                    
                    # Count recent updates (last 7 days)
                    cutoff = datetime.now() - timedelta(days=7)
                    recent_updates = sum(1 for r in repos if datetime.strptime(
                        r.get('updated_at', ''), '%Y-%m-%dT%H:%M:%SZ'
                    ) > cutoff)
                    
                    metrics[tech] = {
                        'repo_count': len(repos),
                        'total_stars': total_stars,
                        'total_forks': total_forks,
                        'avg_stars': total_stars / len(repos),
                        'avg_forks': total_forks / len(repos),
                        'open_issues': open_issues,
                        'recent_activity': recent_updates,
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    logger.info(f"Metrics calculated for {tech}")
                else:
                    metrics[tech] = None
                    
                # Rate limit respect
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error calculating metrics for {tech}: {e}")
                metrics[tech] = None
                
        return metrics

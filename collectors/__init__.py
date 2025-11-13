"""
Data collectors package for technology demand analysis.

Provides collectors for:
- Stack Overflow: Questions, tags, and developer activity
- GitHub: Repositories, stars, and code statistics  
- Google Trends: Search interest and trending data
"""

from .stackoverflow import StackOverflowCollector
from .github import GitHubCollector
from .trends import GoogleTrendsCollector

__all__ = [
    'StackOverflowCollector',
    'GitHubCollector',
    'GoogleTrendsCollector'
]

__version__ = '1.0.0'

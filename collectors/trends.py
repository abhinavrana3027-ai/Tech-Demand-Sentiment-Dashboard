from pytrends.request import TrendReq
import pandas as pd
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)

class GoogleTrendsCollector:
    """
    Collector for Google Trends data using pytrends library.
    Fetches search interest over time, related queries, and geographic data.
    """
    
    def __init__(self, hl: str = 'en-US', tz: int = 360):
        """
        Initialize Google Trends collector.
        
        Args:
            hl: Language (default: 'en-US')
            tz: Timezone offset (default: 360 for US)
        """
        self.pytrends = TrendReq(hl=hl, tz=tz)
        self.hl = hl
        self.tz = tz
        
    def get_interest_over_time(self, keywords: List[str],
                               timeframe: str = 'today 12-m',
                               geo: str = '') -> pd.DataFrame:
        """
        Get search interest over time for keywords.
        
        Args:
            keywords: List of search terms (max 5)
            timeframe: Time period (e.g., 'today 12-m', 'today 3-m')
            geo: Geographic location (e.g., 'US', 'DE')
            
        Returns:
            DataFrame with interest over time
        """
        try:
            # Build payload
            self.pytrends.build_payload(
                kw_list=keywords[:5],  # Max 5 keywords
                cat=0,
                timeframe=timeframe,
                geo=geo,
                gprop=''
            )
            
            # Get interest over time
            interest_df = self.pytrends.interest_over_time()
            
            if not interest_df.empty:
                # Remove 'isPartial' column if exists
                if 'isPartial' in interest_df.columns:
                    interest_df = interest_df.drop(columns=['isPartial'])
                    
            logger.info(f"Retrieved interest over time for {len(keywords)} keywords")
            return interest_df
            
        except Exception as e:
            logger.error(f"Error fetching interest over time: {e}")
            return pd.DataFrame()
            
    def get_interest_by_region(self, keywords: List[str],
                              resolution: str = 'COUNTRY',
                              timeframe: str = 'today 12-m') -> pd.DataFrame:
        """
        Get search interest by geographic region.
        
        Args:
            keywords: List of search terms (max 5)
            resolution: Geographic resolution ('COUNTRY', 'REGION', 'CITY', 'DMA')
            timeframe: Time period
            
        Returns:
            DataFrame with regional interest
        """
        try:
            self.pytrends.build_payload(
                kw_list=keywords[:5],
                timeframe=timeframe
            )
            
            region_df = self.pytrends.interest_by_region(
                resolution=resolution,
                inc_low_vol=True,
                inc_geo_code=True
            )
            
            logger.info(f"Retrieved regional interest for {len(keywords)} keywords")
            return region_df
            
        except Exception as e:
            logger.error(f"Error fetching regional interest: {e}")
            return pd.DataFrame()
            
    def get_related_queries(self, keyword: str,
                           timeframe: str = 'today 12-m',
                           geo: str = '') -> Dict[str, pd.DataFrame]:
        """
        Get related queries for a keyword.
        
        Args:
            keyword: Search term
            timeframe: Time period
            geo: Geographic location
            
        Returns:
            Dictionary with 'top' and 'rising' related queries
        """
        try:
            self.pytrends.build_payload(
                kw_list=[keyword],
                timeframe=timeframe,
                geo=geo
            )
            
            related_queries = self.pytrends.related_queries()
            
            logger.info(f"Retrieved related queries for '{keyword}'")
            return related_queries
            
        except Exception as e:
            logger.error(f"Error fetching related queries: {e}")
            return {'top': pd.DataFrame(), 'rising': pd.DataFrame()}
            
    def get_trending_searches(self, country: str = 'united_states') -> pd.DataFrame:
        """
        Get currently trending searches.
        
        Args:
            country: Country code (e.g., 'united_states', 'germany')
            
        Returns:
            DataFrame with trending searches
        """
        try:
            trending_df = self.pytrends.trending_searches(pn=country)
            logger.info(f"Retrieved trending searches for {country}")
            return trending_df
            
        except Exception as e:
            logger.error(f"Error fetching trending searches: {e}")
            return pd.DataFrame()
            
    def compare_technologies(self, tech_list: List[str],
                            timeframe: str = 'today 12-m',
                            geo: str = '') -> Dict[str, Any]:
        """
        Compare search interest for multiple technologies.
        
        Args:
            tech_list: List of technology names
            timeframe: Time period
            geo: Geographic location
            
        Returns:
            Dictionary with comparison data and metrics
        """
        logger.info(f"Comparing {len(tech_list)} technologies")
        
        results = {
            'timeframe': timeframe,
            'geo': geo,
            'timestamp': datetime.now().isoformat(),
            'technologies': {}
        }
        
        # Process in batches of 5 (Google Trends limit)
        for i in range(0, len(tech_list), 5):
            batch = tech_list[i:i+5]
            
            try:
                # Get interest over time
                interest_df = self.get_interest_over_time(
                    keywords=batch,
                    timeframe=timeframe,
                    geo=geo
                )
                
                if not interest_df.empty:
                    for tech in batch:
                        if tech in interest_df.columns:
                            series = interest_df[tech]
                            
                            results['technologies'][tech] = {
                                'avg_interest': float(series.mean()),
                                'max_interest': float(series.max()),
                                'min_interest': float(series.min()),
                                'current_interest': float(series.iloc[-1]),
                                'trend': 'rising' if series.iloc[-1] > series.mean() else 'declining',
                                'volatility': float(series.std()),
                                'data_points': len(series)
                            }
                            
                # Respect rate limits
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing batch {batch}: {e}")
                
        return results
        
    def get_tech_demand_trends(self, tech_list: List[str],
                               periods: List[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get comprehensive demand trends for technologies across multiple time periods.
        
        Args:
            tech_list: List of technology names
            periods: List of timeframes (default: ['today 3-m', 'today 12-m'])
            
        Returns:
            Dictionary mapping technologies to their trend data
        """
        if periods is None:
            periods = ['today 3-m', 'today 12-m']
            
        logger.info(f"Fetching demand trends for {len(tech_list)} technologies")
        
        trends = {}
        
        for tech in tech_list:
            try:
                tech_data = {
                    'name': tech,
                    'periods': {},
                    'timestamp': datetime.now().isoformat()
                }
                
                for period in periods:
                    interest_df = self.get_interest_over_time(
                        keywords=[tech],
                        timeframe=period
                    )
                    
                    if not interest_df.empty and tech in interest_df.columns:
                        series = interest_df[tech]
                        
                        # Calculate growth rate
                        first_half = series[:len(series)//2].mean()
                        second_half = series[len(series)//2:].mean()
                        growth_rate = ((second_half - first_half) / first_half * 100) if first_half > 0 else 0
                        
                        tech_data['periods'][period] = {
                            'avg_interest': float(series.mean()),
                            'current': float(series.iloc[-1]),
                            'peak': float(series.max()),
                            'growth_rate': float(growth_rate),
                            'consistency': float(1 - (series.std() / series.mean())) if series.mean() > 0 else 0
                        }
                        
                    # Rate limiting
                    time.sleep(1)
                    
                trends[tech] = tech_data
                logger.info(f"Trends calculated for {tech}")
                
            except Exception as e:
                logger.error(f"Error calculating trends for {tech}: {e}")
                trends[tech] = None
                
        return trends
        
    def get_suggestions(self, keyword: str) -> List[str]:
        """
        Get keyword suggestions.
        
        Args:
            keyword: Base keyword
            
        Returns:
            List of suggested keywords
        """
        try:
            suggestions = self.pytrends.suggestions(keyword=keyword)
            return [s['title'] for s in suggestions]
            
        except Exception as e:
            logger.error(f"Error fetching suggestions: {e}")
            return []

from bertopic import BERTopic
from sklearn.feature_extraction.text import CountVectorizer
import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Tuple, Optional, Any

logger = logging.getLogger(__name__)

class TopicModel:
    """
    Topic modeling using BERTopic for discovering themes in technology discussions.
    """
    
    def __init__(self, language: str = 'english', min_topic_size: int = 10):
        """
        Initialize topic modeling.
        
        Args:
            language: Language for stopwords
            min_topic_size: Minimum number of documents per topic
        """
        self.language = language
        self.min_topic_size = min_topic_size
        self.model = None
        self.topics = None
        self.probabilities = None
        
    def fit(self, documents: List[str]) -> None:
        """
        Fit BERTopic model on documents.
        
        Args:
            documents: List of text documents
        """
        logger.info(f"Fitting BERTopic model on {len(documents)} documents")
        
        # Initialize vectorizer
        vectorizer = CountVectorizer(
            stop_words=self.language,
            min_df=2,
            max_df=0.95
        )
        
        # Initialize and fit BERTopic
        self.model = BERTopic(
            vectorizer_model=vectorizer,
            min_topic_size=self.min_topic_size,
            nr_topics='auto'
        )
        
        self.topics, self.probabilities = self.model.fit_transform(documents)
        
        logger.info(f"Discovered {len(set(self.topics))} topics")
        
    def get_topics(self) -> List[Tuple[int, List[Tuple[str, float]]]]:
        """
        Get discovered topics and their top words.
        
        Returns:
            List of (topic_id, [(word, score), ...]) tuples
        """
        if self.model is None:
            raise ValueError("Model must be fitted first")
            
        return self.model.get_topics()
        
    def get_topic_info(self) -> pd.DataFrame:
        """
        Get information about discovered topics.
        
        Returns:
            DataFrame with topic information
        """
        if self.model is None:
            raise ValueError("Model must be fitted first")
            
        return self.model.get_topic_info()
        
    def get_document_topics(self, documents: List[str]) -> Tuple[List[int], np.ndarray]:
        """
        Get topic assignments for new documents.
        
        Args:
            documents: List of documents
            
        Returns:
            Tuple of (topic assignments, probabilities)
        """
        if self.model is None:
            raise ValueError("Model must be fitted first")
            
        topics, probs = self.model.transform(documents)
        return topics, probs
        
    def get_representative_docs(self, topic_id: int) -> List[str]:
        """
        Get representative documents for a topic.
        
        Args:
            topic_id: Topic identifier
            
        Returns:
            List of representative documents
        """
        if self.model is None:
            raise ValueError("Model must be fitted first")
            
        return self.model.get_representative_docs(topic_id)
        
    def analyze_tech_discussions(self, discussions: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Analyze technology discussions to discover themes.
        
        Args:
            discussions: Dict mapping tech names to discussion texts
            
        Returns:
            Analysis results with topics and insights
        """
        logger.info(f"Analyzing discussions for {len(discussions)} technologies")
        
        results = {}
        
        for tech, texts in discussions.items():
            try:
                if len(texts) < self.min_topic_size:
                    logger.warning(f"Skipping {tech}: insufficient documents ({len(texts)})")
                    continue
                    
                # Fit model
                self.fit(texts)
                
                # Get topics
                topic_info = self.get_topic_info()
                
                # Extract insights
                results[tech] = {
                    'num_topics': len(set(self.topics)) - 1,  # Exclude outlier topic
                    'topics': topic_info.to_dict('records'),
                    'top_topic': topic_info.iloc[1] if len(topic_info) > 1 else None,
                    'distribution': pd.Series(self.topics).value_counts().to_dict()
                }
                
                logger.info(f"Analyzed {tech}: found {results[tech]['num_topics']} topics")
                
            except Exception as e:
                logger.error(f"Error analyzing {tech}: {e}")
                results[tech] = None
                
        return results

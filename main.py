"""Tech Demand & Sentiment Dashboard - Main FastAPI Application

A production-ready API for analyzing tech skills demand through public data sources.
Provides endpoints for data collection, forecasting, NLP analysis, and sentiment detection.

Author: Abhinav Rana
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from loguru import logger
import uvicorn

# Initialize FastAPI app
app = FastAPI(
    title="Tech Demand & Sentiment Dashboard API",
    description="Real-time tech skills demand analysis with forecasting and NLP",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str

class TagInfo(BaseModel):
    tag: str
    total_questions: int
    avg_weekly_questions: float
    last_updated: datetime

class TimeSeriesPoint(BaseModel):
    date: str
    count: int
    tag: str

class ForecastPoint(BaseModel):
    date: str
    predicted_count: float
    confidence_lower: float
    confidence_upper: float

class TopicInfo(BaseModel):
    topic_id: int
    keywords: List[str]
    sample_titles: List[str]
    prevalence: float

class SentimentRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)

class SentimentResponse(BaseModel):
    text: str
    sentiment: str
    confidence: float
    scores: Dict[str, float]

# In-memory storage (replace with database in production)
data_store = {
    "stackoverflow_data": pd.DataFrame(),
    "github_data": pd.DataFrame(),
    "trends_data": pd.DataFrame(),
    "models": {},
    "last_collection": None
}

# Sample data initialization
def init_sample_data():
    """Initialize with sample data for demonstration"""
    dates = pd.date_range(start='2023-01-01', end='2024-11-01', freq='W')
    tags = ['python', 'javascript', 'java', 'typescript', 'react', 'docker', 'kubernetes', 'aws']
    
    sample_data = []
    for tag in tags:
        base_count = np.random.randint(100, 500)
        trend = np.random.randn(len(dates)).cumsum() * 10
        for i, date in enumerate(dates):
            count = int(max(0, base_count + trend[i] + np.random.randn() * 20))
            sample_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'tag': tag,
                'count': count,
                'source': 'stackoverflow'
            })
    
    data_store["stackoverflow_data"] = pd.DataFrame(sample_data)
    data_store["last_collection"] = datetime.now()
    logger.info(f"Initialized sample data with {len(sample_data)} records")

init_sample_data()

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Tech Demand & Sentiment Dashboard API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "tags": "/tags",
            "timeseries": "/timeseries",
            "forecast": "/forecast",
            "topics": "/topics",
            "sentiment": "/predict-sentiment"
        }
    }

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0"
    )

@app.post("/collect", tags=["Data Collection"])
async def trigger_collection(background_tasks: BackgroundTasks):
    """Trigger data collection from all sources"""
    
    def collect_data():
        """Background task for data collection"""
        logger.info("Starting data collection...")
        # Simulate collection
        data_store["last_collection"] = datetime.now()
        logger.info("Data collection completed")
    
    background_tasks.add_task(collect_data)
    
    return {
        "message": "Data collection started",
        "status": "running",
        "last_collection": data_store["last_collection"]
    }

@app.get("/tags", response_model=List[TagInfo], tags=["Tags"])
async def get_tags():
    """Get list of all tags with summary statistics"""
    
    if data_store["stackoverflow_data"].empty:
        raise HTTPException(status_code=404, detail="No data available")
    
    df = data_store["stackoverflow_data"]
    
    tag_stats = df.groupby('tag').agg({
        'count': ['sum', 'mean']
    }).reset_index()
    
    tag_stats.columns = ['tag', 'total_questions', 'avg_weekly_questions']
    
    results = []
    for _, row in tag_stats.iterrows():
        results.append(TagInfo(
            tag=row['tag'],
            total_questions=int(row['total_questions']),
            avg_weekly_questions=float(row['avg_weekly_questions']),
            last_updated=data_store["last_collection"] or datetime.now()
        ))
    
    return results

@app.get("/timeseries", response_model=List[TimeSeriesPoint], tags=["Time Series"])
async def get_timeseries(
    tag: str = Query(..., description="Technology tag to query"),
    start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get time series data for a specific tag"""
    
    if data_store["stackoverflow_data"].empty:
        raise HTTPException(status_code=404, detail="No data available")
    
    df = data_store["stackoverflow_data"]
    
    # Filter by tag
    tag_data = df[df['tag'] == tag.lower()]
    
    if tag_data.empty:
        raise HTTPException(status_code=404, detail=f"Tag '{tag}' not found")
    
    # Filter by date range
    if start:
        tag_data = tag_data[tag_data['date'] >= start]
    if end:
        tag_data = tag_data[tag_data['date'] <= end]
    
    results = []
    for _, row in tag_data.iterrows():
        results.append(TimeSeriesPoint(
            date=row['date'],
            count=int(row['count']),
            tag=row['tag']
        ))
    
    return results

@app.get("/forecast", response_model=List[ForecastPoint], tags=["Forecasting"])
async def get_forecast(
    tag: str = Query(..., description="Technology tag to forecast"),
    horizon: int = Query(8, ge=1, le=52, description="Number of weeks to forecast")
):
    """Get demand forecast for a specific tag"""
    
    if data_store["stackoverflow_data"].empty:
        raise HTTPException(status_code=404, detail="No data available")
    
    df = data_store["stackoverflow_data"]
    tag_data = df[df['tag'] == tag.lower()]
    
    if tag_data.empty:
        raise HTTPException(status_code=404, detail=f"Tag '{tag}' not found")
    
    # Simple linear trend forecast (replace with Prophet/ARIMA in production)
    tag_data = tag_data.sort_values('date')
    recent_trend = tag_data['count'].tail(12).mean()
    std_dev = tag_data['count'].tail(12).std()
    
    last_date = pd.to_datetime(tag_data['date'].iloc[-1])
    
    forecasts = []
    for i in range(1, horizon + 1):
        forecast_date = last_date + timedelta(weeks=i)
        predicted = recent_trend + np.random.randn() * 10
        
        forecasts.append(ForecastPoint(
            date=forecast_date.strftime('%Y-%m-%d'),
            predicted_count=float(predicted),
            confidence_lower=float(predicted - 1.96 * std_dev),
            confidence_upper=float(predicted + 1.96 * std_dev)
        ))
    
    return forecasts

@app.get("/topics", response_model=List[TopicInfo], tags=["NLP"])
async def get_topics(
    tag: Optional[str] = Query(None, description="Filter topics by tag")
):
    """Get topic modeling results"""
    
    # Sample topics (replace with actual BERTopic results)
    topics = [
        TopicInfo(
            topic_id=0,
            keywords=["deployment", "production", "docker", "kubernetes"],
            sample_titles=[
                "How to deploy Python app with Docker?",
                "Kubernetes deployment best practices",
                "Production deployment strategies"
            ],
            prevalence=0.25
        ),
        TopicInfo(
            topic_id=1,
            keywords=["async", "await", "concurrent", "threading"],
            sample_titles=[
                "Understanding async/await in Python",
                "Concurrent programming patterns",
                "Threading vs multiprocessing"
            ],
            prevalence=0.18
        ),
        TopicInfo(
            topic_id=2,
            keywords=["machine", "learning", "model", "training"],
            sample_titles=[
                "Best practices for ML model training",
                "Improving model performance",
                "Machine learning pipeline design"
            ],
            prevalence=0.22
        )
    ]
    
    return topics

@app.post("/predict-sentiment", response_model=SentimentResponse, tags=["NLP"])
async def predict_sentiment(request: SentimentRequest):
    """Predict sentiment of text"""
    
    # Simple rule-based sentiment (replace with transformer model)
    text = request.text.lower()
    
    positive_words = ['good', 'great', 'excellent', 'amazing', 'love', 'best', 'perfect']
    negative_words = ['bad', 'terrible', 'awful', 'hate', 'worst', 'poor', 'disappointing']
    
    pos_count = sum(word in text for word in positive_words)
    neg_count = sum(word in text for word in negative_words)
    
    if pos_count > neg_count:
        sentiment = "positive"
        confidence = min(0.9, 0.5 + pos_count * 0.1)
    elif neg_count > pos_count:
        sentiment = "negative"
        confidence = min(0.9, 0.5 + neg_count * 0.1)
    else:
        sentiment = "neutral"
        confidence = 0.6
    
    return SentimentResponse(
        text=request.text,
        sentiment=sentiment,
        confidence=confidence,
        scores={
            "positive": float(pos_count / (pos_count + neg_count + 1)),
            "negative": float(neg_count / (pos_count + neg_count + 1)),
            "neutral": 0.3
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

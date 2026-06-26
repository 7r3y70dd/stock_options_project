"""Sentiment analysis for news articles using FinBERT or DistilBERT.

Provides local sentiment scoring with fallback to provider sentiment.
"""

import logging
from typing import Optional, Tuple

from app.core.config import config

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Analyzes sentiment of news articles using transformer models.
    
    Uses FinBERT (fine-tuned BERT for financial sentiment) or DistilBERT as fallback.
    Provides normalized sentiment scores from -1.0 (bearish) to 1.0 (bullish).
    """

    def __init__(self, model_name: str = "finbert", use_gpu: bool = False):
        """Initialize sentiment analyzer.
        
        Args:
            model_name: Model to use ("finbert" or "distilbert")
            use_gpu: Whether to use GPU if available
        """
        self.model_name = model_name
        self.use_gpu = use_gpu
        self.pipeline = None
        self._initialize_model()

    def _initialize_model(self) -> None:
        """Initialize the sentiment analysis pipeline.
        
        Attempts to load FinBERT, falls back to DistilBERT if not available.
        """
        if not config.SENTIMENT_ANALYSIS_ENABLED:
            logger.info("Sentiment analysis disabled in config")
            return
        
        try:
            from transformers import pipeline
            
            device = 0 if self.use_gpu else -1  # -1 for CPU
            
            if self.model_name == "finbert":
                try:
                    logger.info("Loading FinBERT model for sentiment analysis...")
                    self.pipeline = pipeline(
                        "sentiment-analysis",
                        model="ProsusAI/finbert",
                        device=device,
                    )
                    logger.info("FinBERT model loaded successfully")
                except Exception as e:
                    logger.warning(f"Failed to load FinBERT: {e}. Falling back to DistilBERT.")
                    self._load_distilbert(device)
            else:
                self._load_distilbert(device)
                
        except ImportError:
            logger.warning(
                "transformers library not installed. "
                "Install with: pip install transformers torch"
            )
            self.pipeline = None

    def _load_distilbert(self, device: int) -> None:
        """Load DistilBERT as fallback model.
        
        Args:
            device: Device to use (0 for GPU, -1 for CPU)
        """
        try:
            from transformers import pipeline
            
            logger.info("Loading DistilBERT model for sentiment analysis...")
            self.pipeline = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
                device=device,
            )
            logger.info("DistilBERT model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load DistilBERT: {e}")
            self.pipeline = None

    def analyze(
        self,
        text: str,
        provider_sentiment: Optional[str] = None,
    ) -> Tuple[float, float]:
        """Analyze sentiment of text.
        
        Args:
            text: Text to analyze (typically article title + description)
            provider_sentiment: Optional sentiment from data provider ("positive", "negative", "neutral")
            
        Returns:
            Tuple of (sentiment_score, confidence_score)
            - sentiment_score: -1.0 (bearish) to 1.0 (bullish), 0.0 (neutral)
            - confidence_score: 0.0 to 1.0 (confidence in the prediction)
        """
        if not text or not isinstance(text, str):
            logger.warning("Invalid text for sentiment analysis")
            return self._provider_sentiment_to_score(provider_sentiment)
        
        # If model is not available, use provider sentiment
        if self.pipeline is None:
            logger.debug("Sentiment analysis model not available, using provider sentiment")
            return self._provider_sentiment_to_score(provider_sentiment)
        
        try:
            # Truncate text to avoid token limit issues
            text = text[:512]
            
            # Run sentiment analysis
            result = self.pipeline(text)
            
            if not result or len(result) == 0:
                logger.warning("Empty result from sentiment analysis")
                return self._provider_sentiment_to_score(provider_sentiment)
            
            prediction = result[0]
            label = prediction.get("label", "").lower()
            score = prediction.get("score", 0.0)
            
            # Convert to normalized sentiment score
            if label == "positive":
                sentiment_score = score  # 0.0 to 1.0
            elif label == "negative":
                sentiment_score = -score  # -1.0 to 0.0
            else:  # neutral or unknown
                sentiment_score = 0.0
            
            # Confidence is the model's confidence in its prediction
            confidence_score = score
            
            logger.debug(
                f"Sentiment analysis: label={label}, score={score:.3f}, "
                f"normalized={sentiment_score:.3f}, confidence={confidence_score:.3f}"
            )
            
            return sentiment_score, confidence_score
            
        except Exception as e:
            logger.error(f"Error during sentiment analysis: {e}", exc_info=True)
            return self._provider_sentiment_to_score(provider_sentiment)

    def _provider_sentiment_to_score(
        self,
        provider_sentiment: Optional[str],
    ) -> Tuple[float, float]:
        """Convert provider sentiment label to normalized score.
        
        Args:
            provider_sentiment: Provider sentiment ("positive", "negative", "neutral")
            
        Returns:
            Tuple of (sentiment_score, confidence_score)
        """
        if not provider_sentiment:
            return 0.0, 0.0  # Neutral with no confidence
        
        provider_sentiment = provider_sentiment.lower().strip()
        
        if provider_sentiment == "positive":
            return 0.5, 0.7  # Moderate bullish with moderate confidence
        elif provider_sentiment == "negative":
            return -0.5, 0.7  # Moderate bearish with moderate confidence
        else:  # neutral or unknown
            return 0.0, 0.5  # Neutral with low confidence

    def batch_analyze(
        self,
        texts: list,
        provider_sentiments: Optional[list] = None,
    ) -> list:
        """Analyze sentiment of multiple texts.
        
        Args:
            texts: List of texts to analyze
            provider_sentiments: Optional list of provider sentiments
            
        Returns:
            List of (sentiment_score, confidence_score) tuples
        """
        if provider_sentiments is None:
            provider_sentiments = [None] * len(texts)
        
        results = []
        for text, provider_sentiment in zip(texts, provider_sentiments):
            result = self.analyze(text, provider_sentiment)
            results.append(result)
        
        return results

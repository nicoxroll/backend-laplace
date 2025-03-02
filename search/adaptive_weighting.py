import re
from typing import Dict, Any, List, Optional
import numpy as np
from collections import Counter

class AdaptiveWeighting:
    """
    Adaptively determines the optimal weighting (alpha) between 
    vector search and keyword search based on query characteristics.
    """
    
    def __init__(self):
        # Base parameters that influence weighting
        self.min_alpha = 0.2  # Minimum vector search weight
        self.max_alpha = 0.95  # Maximum vector search weight
        self.default_alpha = 0.5  # Default balanced weight
        
        # Feature importance weights
        self.weights = {
            "length": 0.3,       # Query length influence
            "specificity": 0.4,  # Term specificity influence
            "structure": 0.3     # Query structural influence
        }
    
    def compute_alpha(self, query: str, collection_stats: Optional[Dict[str, Any]] = None) -> float:
        """
        Compute the adaptive alpha value for hybrid search based on query characteristics.
        
        Args:
            query: The search query text
            collection_stats: Optional dictionary with corpus statistics like term frequencies
            
        Returns:
            float: Alpha value between min_alpha and max_alpha
        """
        features = self._extract_features(query, collection_stats)
        
        # Calculate normalized score (0-1) based on features
        score = 0
        score += features["length_score"] * self.weights["length"]
        score += features["specificity_score"] * self.weights["specificity"]
        score += features["structure_score"] * self.weights["structure"]
        
        # Map score to alpha range
        alpha = self.min_alpha + score * (self.max_alpha - self.min_alpha)
        return alpha
    
    def _extract_features(self, query: str, collection_stats: Optional[Dict[str, Any]]) -> Dict[str, float]:
        """Extract features from the query that influence the optimal alpha"""
        words = re.findall(r'\w+', query.lower())
        
        features = {}
        
        # 1. Length feature - longer queries favor keyword search
        query_len = len(words)
        # Logistic function mapping query length to score
        length_score = 1 - (1 / (1 + np.exp(-0.2 * (query_len - 7))))
        features["length_score"] = length_score
        
        # 2. Specificity feature - technical/specific terms favor vector search
        if collection_stats and "term_frequencies" in collection_stats:
            # Calculate average term rarity
            term_frequencies = collection_stats["term_frequencies"]
            total_docs = collection_stats.get("total_docs", 1)
            
            specificities = []
            for word in words:
                if word in term_frequencies:
                    # Inverse document frequency
                    specificity = np.log(total_docs / (1 + term_frequencies[word]))
                    specificities.append(specificity)
            
            if specificities:
                avg_specificity = np.mean(specificities)
                # Normalize to 0-1 range (assuming max IDF around 10)
                specificity_score = min(1.0, avg_specificity / 10)
            else:
                specificity_score = 0.5
        else:
            # Fallback: estimate specificity from word length (crude approximation)
            avg_word_len = np.mean([len(word) for word in words]) if words else 0
            specificity_score = min(1.0, avg_word_len / 10)
        
        features["specificity_score"] = specificity_score
        
        # 3. Query structure feature - questions, quotes, special operators
        structure_score = 0.5  # Default balanced
        
        # Questions tend to work better with vector search
        if '?' in query:
            structure_score += 0.2
            
        # Quoted phrases better with exact keyword matching
        if '"' in query:
            structure_score -= 0.3
            
        # Boolean operators better with keyword search
        if any(op in query.lower() for op in ['and', 'or', 'not', '+', '-']):
            structure_score -= 0.2
            
        # Clamp to 0-1 range
        features["structure_score"] = max(0, min(1, structure_score))
        
        return features
    
    def optimize_from_feedback(self, query: str, feedback: Dict[str, Any]) -> None:
        """
        Update the weighting parameters based on user feedback
        
        Args:
            query: The original query
            feedback: Dictionary with user feedback information
        """
        # Implementation would adjust self.weights based on feedback
        pass

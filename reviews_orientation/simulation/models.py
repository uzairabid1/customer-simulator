# models.py
from dataclasses import dataclass
from typing import List, Dict
import uuid
from datetime import datetime

@dataclass
class Customer:
    customer_id: str
    name: str
    role_desc: Dict[str, str]

@dataclass 
class Review:
    review_id: str
    user_id: str
    business_id: str
    stars: float
    text: str
    date: str
    ordered_item: str = ""
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)

class Restaurant:
    def __init__(self, restaurant_id: str, review_policy: str):
        self.restaurant_id = restaurant_id
        self.review_policy = review_policy
        # Use menu from config
        from config import Config
        self.menu = Config.RESTAURANT_MENU.copy()
        self.reviews: List[Review] = []
        self.revenue = 0
        self.initial_reviews: List[Review] = [] 
    
    def get_sorted_reviews(self) -> List[Review]:
        if self.review_policy == "highest_rating":
            return sorted(self.reviews, key=lambda x: x.stars, reverse=True)[:10]
        elif self.review_policy == "latest":
            return sorted(self.reviews, key=lambda x: x.date, reverse=True)[:10]
        elif self.review_policy == "recent_quality_boost":
            return self._get_recent_quality_boost_reviews()[:10]
        else:
            return sorted(self.reviews, key=lambda x: x.date, reverse=True)[:10]
    
    def get_overall_rating(self) -> float:
        all_reviews = self.get_all_reviews()
        if not all_reviews:
            return 0.0
        return sum(r.stars for r in all_reviews) / len(all_reviews)

    def get_review_count(self) -> int:
        return len(self.get_all_reviews())

    def get_reviews_by_rating(self, stars: int, limit: int = 5) -> List[Review]:
        return sorted(
            [r for r in self.reviews if r.stars == stars],
            key=lambda x: x.date,
            reverse=True
        )[:limit]

    def get_recent_reviews(self, limit: int = 5) -> List[Review]:
        return sorted(self.reviews, key=lambda x: x.date, reverse=True)[:limit]
    
    def get_all_reviews(self) -> List[Review]:
        """Returns combined list of initial and new reviews"""
        return self.initial_reviews + self.reviews
    
    def get_review_bias_analysis(self) -> Dict:
        """
        Analyze the difference between what customers see (first 10 reviews) vs reality (all reviews).
        This tracks the bias between partial review exposure and the complete review picture.
        """
        all_reviews = self.get_all_reviews()
        if not all_reviews:
            return {
                "total_reviews": 0,
                "partial_reviews_count": 0,
                "all_reviews_avg": 0.0,
                "partial_reviews_avg": 0.0,
                "bias_difference": 0.0,
                "bias_type": "none",
                "bias_magnitude": "none"
            }
        
        # Get what customers actually see (first 10 reviews after sorting by policy)
        if self.review_policy == "highest_rating":
            sorted_reviews = sorted(all_reviews, key=lambda x: x.stars, reverse=True)
        elif self.review_policy == "latest":
            sorted_reviews = sorted(all_reviews, key=lambda x: x.date, reverse=True)
        elif self.review_policy == "recent_quality_boost":
            sorted_reviews = self._get_recent_quality_boost_all_reviews()
        else:
            sorted_reviews = sorted(all_reviews, key=lambda x: x.date, reverse=True)
            
        partial_reviews = sorted_reviews[:10]  # What customers see
        
        # Calculate averages
        all_reviews_avg = sum(r.stars for r in all_reviews) / len(all_reviews)
        partial_reviews_avg = sum(r.stars for r in partial_reviews) / len(partial_reviews)
        
        # Calculate bias
        bias_difference = partial_reviews_avg - all_reviews_avg
        
        # Classify bias type and magnitude
        if abs(bias_difference) < 0.1:
            bias_type = "minimal"
            bias_magnitude = "negligible"
        elif bias_difference > 0:
            bias_type = "positive_bias"  # Customers see better reviews than reality
            if bias_difference > 0.5:
                bias_magnitude = "high"
            elif bias_difference > 0.2:
                bias_magnitude = "moderate" 
            else:
                bias_magnitude = "low"
        else:
            bias_type = "negative_bias"  # Customers see worse reviews than reality
            if abs(bias_difference) > 0.5:
                bias_magnitude = "high"
            elif abs(bias_difference) > 0.2:
                bias_magnitude = "moderate"
            else:
                bias_magnitude = "low"
        
        return {
            "total_reviews": len(all_reviews),
            "partial_reviews_count": len(partial_reviews),
            "all_reviews_avg": round(all_reviews_avg, 2),
            "partial_reviews_avg": round(partial_reviews_avg, 2),
            "bias_difference": round(bias_difference, 2),
            "bias_type": bias_type,
            "bias_magnitude": bias_magnitude,
            "review_policy": self.review_policy,
            "customers_see_all": len(all_reviews) <= 10  # True if customers see complete picture
        }
    
    def _get_recent_quality_boost_all_reviews(self) -> List[Review]:
        """Apply recent quality boost to all reviews (for bias analysis)"""
        from datetime import datetime, timedelta
        
        current_date = datetime.now()
        thirty_days_ago = current_date - timedelta(days=30)
        ninety_days_ago = current_date - timedelta(days=90)
        
        all_reviews = self.get_all_reviews()
        boosted_reviews = []
        
        for review in all_reviews:
            try:
                review_date = datetime.strptime(review.date, "%Y-%m-%d %H:%M:%S")
                boosted_rating = review.stars
                
                # Apply boost based on recency
                if review_date >= thirty_days_ago:
                    boosted_rating += 0.5  # Recent reviews get +0.5 boost
                elif review_date >= ninety_days_ago:
                    boosted_rating += 0.25  # Semi-recent reviews get +0.25 boost
                
                # Cap at 5 stars maximum
                boosted_rating = min(boosted_rating, 5.0)
                
                boosted_reviews.append((review, boosted_rating))
            except ValueError:
                boosted_reviews.append((review, review.stars))
        
        # Sort by boosted rating (descending), then by date (descending) for ties
        boosted_reviews.sort(key=lambda x: (x[1], x[0].date), reverse=True)
        
        return [review for review, _ in boosted_reviews]

    def _get_recent_quality_boost_reviews(self) -> List[Review]:
        """
        Recent Quality Boost Algorithm:
        - Reviews from last 30 days: +0.5 star boost
        - Reviews from last 90 days: +0.25 star boost  
        - Reviews older than 90 days: no boost
        - Sort by boosted rating (descending)
        """
        from datetime import datetime, timedelta
        
        current_date = datetime.now()
        thirty_days_ago = current_date - timedelta(days=30)
        ninety_days_ago = current_date - timedelta(days=90)
        
        boosted_reviews = []
        for review in self.reviews:
            try:
                review_date = datetime.strptime(review.date, "%Y-%m-%d %H:%M:%S")
                boosted_rating = review.stars
                
                # Apply boost based on recency
                if review_date >= thirty_days_ago:
                    boosted_rating += 0.5  # Recent reviews get +0.5 boost
                elif review_date >= ninety_days_ago:
                    boosted_rating += 0.25  # Semi-recent reviews get +0.25 boost
                # Older reviews get no boost
                
                # Cap at 5 stars maximum
                boosted_rating = min(boosted_rating, 5.0)
                
                boosted_reviews.append((review, boosted_rating))
            except ValueError:
                # If date parsing fails, treat as old review (no boost)
                boosted_reviews.append((review, review.stars))
        
        # Sort by boosted rating (descending), then by date (descending) for ties
        boosted_reviews.sort(key=lambda x: (x[1], x[0].date), reverse=True)
        
        return [review for review, _ in boosted_reviews]
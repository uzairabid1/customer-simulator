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
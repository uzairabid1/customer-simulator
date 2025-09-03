# models.py
from dataclasses import dataclass
from typing import List, Dict
import uuid
from datetime import datetime
from config import Config

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
    def __init__(self, restaurant_id: str):
        self.restaurant_id = restaurant_id
        self.quality_rating = Config.RESTAURANT_A_RATING if restaurant_id == "A" else Config.RESTAURANT_B_RATING
        self.review_policy = Config.RESTAURANT_A_REVIEW_POLICY if restaurant_id == "A" else Config.RESTAURANT_B_REVIEW_POLICY
        # Use menus from config
        if restaurant_id == "A":
            self.menu = Config.RESTAURANT_A_MENU.copy()
        else:
            self.menu = Config.RESTAURANT_B_MENU.copy()
        self.reviews: List[Review] = []
        self.revenue = 0
        self.initial_reviews: List[Review] = [] 
    
    def get_sorted_reviews(self) -> List[Review]:
        if self.review_policy == "highest_rating":
            return sorted(self.reviews, key=lambda x: x.stars, reverse=True)[:10]
        else:  # "latest"
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
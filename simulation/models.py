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
        self.menu = {
            "Burger": 10,
            "Pizza": 12,
            "Salad": 8,
            "Pasta": 11,
            "Steak": 18,
            "Sushi Platter": 22,
            "Chicken Wings": 9,
            "Vegetable Stir Fry": 13,
            "Ramen": 14,
            "Tacos": 10,
            "Caesar Salad": 9,
            "Grilled Salmon": 20,
            "Margherita Pizza": 15,
            "Cheesecake": 7,
            "Ice Cream Sundae": 6,
            "Club Sandwich": 11,
            "French Fries": 5,
            "Onion Rings": 6,
            "Mushroom Risotto": 16,
            "Chocolate Cake": 8,
            "Fish and Chips": 14,
            "Vegetable Curry": 12
        }
        self.reviews: List[Review] = []
        self.revenue = 0
    
    def get_sorted_reviews(self) -> List[Review]:
        if self.review_policy == "highest_rating":
            return sorted(self.reviews, key=lambda x: x.stars, reverse=True)[:10]
        return sorted(self.reviews, key=lambda x: x.date, reverse=True)[:10]
    
    def get_overall_rating(self) -> float:
        if not self.reviews:
            return 0.0
        return sum(r.stars for r in self.reviews) / len(self.reviews)

    def get_review_count(self) -> int:
        return len(self.reviews)

    def get_reviews_by_rating(self, stars: int, limit: int = 5) -> List[Review]:
        return sorted(
            [r for r in self.reviews if r.stars == stars],
            key=lambda x: x.date,
            reverse=True
        )[:limit]

    def get_recent_reviews(self, limit: int = 5) -> List[Review]:
        return sorted(self.reviews, key=lambda x: x.date, reverse=True)[:limit]
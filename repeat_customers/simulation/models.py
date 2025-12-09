# models.py - Repeat Customer Simulation
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import uuid
import random
import numpy as np
from datetime import datetime
from config import Config

@dataclass
class CustomerExperience:
    """Stores a customer's experience at a restaurant"""
    restaurant_id: str
    date: str
    ordered_item: str
    stars_given: float
    price_paid: float
    was_satisfied: bool
    review_text: str = ""
    experience_quality: float = 0.5  # Quality score from 0.0 to 1.0 for review generation
    
@dataclass
class Customer:
    customer_id: str
    name: str
    role_desc: Dict[str, str]
    # CoNF experiment fields
    theta: Optional[float] = None  # Idiosyncratic valuation for CoNF
    alpha: Optional[float] = None  # Beta prior parameter
    beta: Optional[float] = None   # Beta prior parameter
    
    # Memory system for repeat customers - simple list of experiences
    experiences: List[CustomerExperience] = field(default_factory=list)
    
    def add_experience(self, experience: CustomerExperience):
        """Add a new experience to customer's memory"""
        self.experiences.append(experience)
    
    def get_restaurant_preference(self, restaurant_id: str) -> float:
        """Get customer's preference for a restaurant based on past experiences"""
        restaurant_experiences = [exp for exp in self.experiences if exp.restaurant_id == restaurant_id]
        if not restaurant_experiences:
            return 0.0
        
        # Simple average of satisfaction (1.0 for satisfied, -0.5 for disappointed)
        total_score = sum(1.0 if exp.was_satisfied else -0.5 for exp in restaurant_experiences)
        return total_score / len(restaurant_experiences)
    
    def get_experience_count(self, restaurant_id: str) -> int:
        """Get number of times customer visited a restaurant"""
        return len([exp for exp in self.experiences if exp.restaurant_id == restaurant_id])
    
    def get_last_experience(self, restaurant_id: str) -> Optional[CustomerExperience]:
        """Get customer's most recent experience at a restaurant"""
        restaurant_experiences = [exp for exp in self.experiences if exp.restaurant_id == restaurant_id]
        return restaurant_experiences[-1] if restaurant_experiences else None
    
    def update_belief_beta_bernoulli(self, reviews: List['Review']) -> float:
        """
        Beta-Bernoulli belief update for CoNF experiment.
        Returns posterior mean estimate of mu (product quality)
        """
        if self.alpha is None or self.beta is None:
            return 0.5  # Default if not CoNF experiment
            
        # Convert 1-5 star reviews to binary (4-5 stars = positive, 1-3 stars = negative)
        positive_reviews = sum(1 for r in reviews if r.stars >= 4.0)
        total_reviews = len(reviews)
        negative_reviews = total_reviews - positive_reviews
        
        # Posterior Beta(alpha + positive, beta + negative)
        posterior_alpha = self.alpha + positive_reviews
        posterior_beta = self.beta + negative_reviews
        
        # Return posterior mean
        return posterior_alpha / (posterior_alpha + posterior_beta)
    
    def get_valuation_estimate(self, mu_estimate: float, restaurant_id: str = None) -> float:
        """
        Customer's estimated valuation = theta + mu_estimate * quality_scale
        Keep it simple - same as original research_implementation
        """
        if self.theta is None:
            return mu_estimate * 120  # Default scaling
        return self.theta + mu_estimate * 80  # Scale mu to have significant impact on valuation

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
        self.review_policy = Config.RESTAURANT_A_REVIEW_POLICY if restaurant_id == "A" else Config.RESTAURANT_B_REVIEW_POLICY
        
        # Set restaurant information from config
        if restaurant_id == "A":
            self.name = Config.RESTAURANT_A_NAME
            self.description = Config.RESTAURANT_A_DESCRIPTION
            self.cuisine_type = Config.RESTAURANT_A_CUISINE_TYPE
            self.price_range = Config.RESTAURANT_A_PRICE_RANGE
            self.menu = Config.RESTAURANT_A_MENU.copy()
        else:
            self.name = Config.RESTAURANT_B_NAME
            self.description = Config.RESTAURANT_B_DESCRIPTION
            self.cuisine_type = Config.RESTAURANT_B_CUISINE_TYPE
            self.price_range = Config.RESTAURANT_B_PRICE_RANGE
            self.menu = Config.RESTAURANT_B_MENU.copy()
            
        self.reviews: List[Review] = []
        self.revenue = 0
        self.initial_reviews: List[Review] = []
        
        # Repeat customer tracking
        self.daily_customers: Dict[int, List[str]] = {}  # day -> list of customer_ids who visited
        self.customer_visit_count: Dict[str, int] = {}  # customer_id -> visit count
    
    def add_daily_customer(self, day: int, customer_id: str):
        """Track which customers visited on which days"""
        if day not in self.daily_customers:
            self.daily_customers[day] = []
        self.daily_customers[day].append(customer_id)
        
        # Update visit count
        if customer_id not in self.customer_visit_count:
            self.customer_visit_count[customer_id] = 0
        self.customer_visit_count[customer_id] += 1
    
    def get_sorted_reviews(self, limit: int = 10) -> List[Review]:
        all_reviews = self.get_all_reviews()
        
        if self.review_policy == "highest_rating":
            return sorted(all_reviews, key=lambda x: x.stars, reverse=True)[:limit]
        elif self.review_policy == "latest" or self.review_policy == "newest_first":
            return sorted(all_reviews, key=lambda x: x.date, reverse=True)[:limit]
        elif self.review_policy == "recent_quality_boost":
            return self._get_recent_quality_boost_reviews()[:limit]
        elif self.review_policy == "random":
            # CoNF experiment: random sampling (exogenous process)
            if len(all_reviews) <= limit:
                return all_reviews.copy()
            return random.sample(all_reviews, limit)
        else:
            return sorted(all_reviews, key=lambda x: x.date, reverse=True)[:limit]
    
    def get_overall_rating(self) -> float:
        all_reviews = self.get_all_reviews()
        if not all_reviews:
            return 0.0
        return sum(r.stars for r in all_reviews) / len(all_reviews)

    def get_review_count(self) -> int:
        return len(self.get_all_reviews())

    def get_all_reviews(self) -> List[Review]:
        """Returns combined list of initial and new reviews"""
        return self.initial_reviews + self.reviews
    
    def add_conf_review(self, customer_id: str, experience_quality: float, true_quality: float, ordered_item: str = None, simulation_date: datetime = None) -> Review:
        """
        Add a new review for CoNF experiment based on experience quality.
        experience_quality: A value from 0.0 to 1.0 representing the specific experience quality
        true_quality: The restaurant's true quality parameter (mu)
        """
        # Use the specific item the customer ordered (passed as parameter)
        if not ordered_item:
            menu_items = list(self.menu.keys())
            ordered_item = random.choice(menu_items) if menu_items else "Special"
        
        # Use LLM to generate realistic review
        from .llm import LLMInterface
        llm = LLMInterface()
        
        try:
            # Generate review using LLM with experience quality
            llm_review = llm.generate_conf_review(
                customer_id=customer_id,
                business_id=self.restaurant_id,
                ordered_item=ordered_item,
                experience_quality=experience_quality,
                true_quality=true_quality
            )
            
            # Create Review object from LLM response with proper simulation date
            review_date = simulation_date.strftime("%Y-%m-%d %H:%M:%S") if simulation_date else llm_review["date"]
            review = Review(
                review_id=llm_review["review_id"],
                user_id=llm_review["user_id"],
                business_id=llm_review["business_id"],
                stars=float(llm_review["stars"]),
                text=llm_review["text"],
                date=review_date,
                ordered_item=llm_review["ordered_item"]
            )
            
        except Exception as e:
            print(f"Warning: LLM review generation failed ({str(e)}), using fallback")
            # Fallback to simple review generation if LLM fails
            # Map experience_quality to rating
            if experience_quality <= 0.1:
                stars = 1.0
            elif experience_quality <= 0.3:
                stars = 2.0
            elif experience_quality <= 0.5:
                stars = 3.0
            elif experience_quality <= 0.8:
                stars = 4.0
            else:
                stars = 5.0
            text = f"{'Great' if experience_quality > 0.5 else 'Poor'} experience with the {ordered_item}."
            
            review_date = simulation_date.strftime("%Y-%m-%d %H:%M:%S") if simulation_date else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            review = Review(
                review_id=str(uuid.uuid4()),
                user_id=customer_id,
                business_id=self.restaurant_id,
                stars=stars,
                text=text,
                date=review_date,
                ordered_item=ordered_item
            )
        
        self.reviews.append(review)
        return review
    
    def get_repeat_customer_stats(self) -> Dict:
        """Get statistics about repeat customers"""
        total_visits = sum(self.customer_visit_count.values())
        unique_customers = len(self.customer_visit_count)
        repeat_customers = len([count for count in self.customer_visit_count.values() if count > 1])
        
        return {
            "total_visits": total_visits,
            "unique_customers": unique_customers,
            "repeat_customers": repeat_customers,
            "repeat_rate": repeat_customers / unique_customers if unique_customers > 0 else 0,
            "avg_visits_per_customer": total_visits / unique_customers if unique_customers > 0 else 0,
            "daily_breakdown": dict(self.daily_customers)
        }
    
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

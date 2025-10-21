# models.py
from dataclasses import dataclass
from typing import List, Dict, Optional
import uuid
import random
import numpy as np
from datetime import datetime
from config import Config

@dataclass
class Customer:
    customer_id: str
    name: str
    role_desc: Dict[str, str]
    # CoNF experiment fields
    theta: Optional[float] = None  # Idiosyncratic valuation for CoNF
    alpha: Optional[float] = None  # Beta prior parameter
    beta: Optional[float] = None   # Beta prior parameter
    
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
    
    def get_valuation_estimate(self, mu_estimate: float) -> float:
        """
        Customer's estimated valuation = theta + mu_estimate * quality_scale
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
        # Remove static quality rating - will be calculated dynamically
        self.review_policy = Config.RESTAURANT_A_REVIEW_POLICY if restaurant_id == "A" else Config.RESTAURANT_B_REVIEW_POLICY
        # Use menus from config
        if restaurant_id == "A":
            self.menu = Config.RESTAURANT_A_MENU.copy()
        else:
            self.menu = Config.RESTAURANT_B_MENU.copy()
        self.reviews: List[Review] = []
        self.revenue = 0
        self.initial_reviews: List[Review] = [] 
    
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
    
    def get_quality_rating(self) -> float:
        """
        Calculate quality rating based on average of all reviews.
        Dynamic quality rating: Use average rating of all reviews instead of fixed values.
        Scale: 1-5 star reviews → 20-100 quality rating
        """
        all_reviews = self.get_all_reviews()
        if not all_reviews:
            # Fallback to original static values if no reviews exist
            return Config.RESTAURANT_A_RATING if self.restaurant_id == "A" else Config.RESTAURANT_B_RATING
        
        average_stars = sum(r.stars for r in all_reviews) / len(all_reviews)
        # Convert 1-5 star scale to 20-100 quality scale
        quality_rating = average_stars * 20
        return round(quality_rating, 1)
    
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
    
    def add_conf_review(self, customer_id: str, true_quality: float, ordered_item: str = None) -> Review:
        """
        Add a new review for CoNF experiment based on true quality.
        X_t ~ Bernoulli(mu) where mu is true quality
        
        As per Baek et al. paper: each customer's experience X_t is drawn
        independently from Bernoulli(μ) where μ is the true product quality.
        """
        # Generate binary outcome based on true quality (Bernoulli distribution)
        is_positive = random.random() < true_quality
        
        # Use the specific item the customer ordered (passed as parameter)
        # If no specific item provided, select randomly
        if not ordered_item:
            menu_items = list(self.menu.keys())
            ordered_item = random.choice(menu_items) if menu_items else "Special"
        
        # Use LLM to generate realistic review
        from .llm import LLMInterface
        llm = LLMInterface()
        
        try:
            # Generate review using LLM
            llm_review = llm.generate_conf_review(
                customer_id=customer_id,
                business_id=self.restaurant_id,
                ordered_item=ordered_item,
                is_positive=is_positive,
                true_quality=true_quality
            )
            
            # Create Review object from LLM response
            review = Review(
                review_id=llm_review["review_id"],
                user_id=llm_review["user_id"],
                business_id=llm_review["business_id"],
                stars=float(llm_review["stars"]),
                text=llm_review["text"],
                date=llm_review["date"],
                ordered_item=llm_review["ordered_item"]
            )
            
        except Exception as e:
            print(f"Warning: LLM review generation failed ({str(e)}), using fallback")
            # Fallback to simple review generation if LLM fails
            stars = random.choice([4.0, 5.0]) if is_positive else random.choice([1.0, 2.0, 3.0])
            text = f"{'Great' if is_positive else 'Poor'} experience with the {ordered_item}."
            
            review = Review(
                review_id=str(uuid.uuid4()),
                user_id=customer_id,
                business_id=self.restaurant_id,
                stars=stars,
                text=text,
                date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ordered_item=ordered_item
            )
        
        self.reviews.append(review)
        return review
    
    def get_conf_reviews_for_customer(self, c: int = 3) -> List[Review]:
        """
        Get c reviews for CoNF experiment according to restaurant's policy
        """
        return self.get_sorted_reviews(limit=c)
    
    def calculate_conf_metrics(self) -> Dict:
        """
        Calculate CoNF-specific metrics for analysis
        """
        all_reviews = self.get_all_reviews()
        if not all_reviews:
            return {"total_reviews": 0, "positive_ratio": 0.0, "persistence_score": 0.0}
        
        # Calculate positive ratio
        positive_count = sum(1 for r in all_reviews if r.stars >= 4.0)
        positive_ratio = positive_count / len(all_reviews)
        
        # Calculate persistence score (how long negative reviews stay at top)
        recent_reviews = self.get_sorted_reviews(limit=5)
        negative_in_recent = sum(1 for r in recent_reviews if r.stars < 4.0)
        persistence_score = negative_in_recent / len(recent_reviews) if recent_reviews else 0.0
        
        return {
            "total_reviews": len(all_reviews),
            "positive_ratio": positive_ratio,
            "persistence_score": persistence_score,
            "recent_negative_count": negative_in_recent,
            "policy": self.review_policy
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
    
    def add_conf_review(self, customer_id: str, true_quality: float, ordered_item: str = None) -> Review:
        """
        Add a new review for CoNF experiment based on true quality.
        X_t ~ Bernoulli(mu) where mu is true quality
        
        As per Baek et al. paper: each customer's experience X_t is drawn
        independently from Bernoulli(μ) where μ is the true product quality.
        """
        # Generate binary outcome based on true quality (Bernoulli distribution)
        is_positive = random.random() < true_quality
        
        # Use the specific item the customer ordered (passed as parameter)
        # If no specific item provided, select randomly
        if not ordered_item:
            menu_items = list(self.menu.keys())
            ordered_item = random.choice(menu_items) if menu_items else "Special"
        
        # Use LLM to generate realistic review
        from .llm import LLMInterface
        llm = LLMInterface()
        
        try:
            # Generate review using LLM
            llm_review = llm.generate_conf_review(
                customer_id=customer_id,
                business_id=self.restaurant_id,
                ordered_item=ordered_item,
                is_positive=is_positive,
                true_quality=true_quality
            )
            
            # Create Review object from LLM response
            review = Review(
                review_id=llm_review["review_id"],
                user_id=llm_review["user_id"],
                business_id=llm_review["business_id"],
                stars=float(llm_review["stars"]),
                text=llm_review["text"],
                date=llm_review["date"],
                ordered_item=llm_review["ordered_item"]
            )
            
        except Exception as e:
            print(f"Warning: LLM review generation failed ({str(e)}), using fallback")
            # Fallback to simple review generation if LLM fails
            stars = random.choice([4.0, 5.0]) if is_positive else random.choice([1.0, 2.0, 3.0])
            text = f"{'Great' if is_positive else 'Poor'} experience with the {ordered_item}."
            
            review = Review(
                review_id=str(uuid.uuid4()),
                user_id=customer_id,
                business_id=self.restaurant_id,
                stars=stars,
                text=text,
                date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ordered_item=ordered_item
            )
        
        self.reviews.append(review)
        return review
    
    def get_conf_reviews_for_customer(self, c: int = 3) -> List[Review]:
        """
        Get c reviews for CoNF experiment according to restaurant's policy
        """
        return self.get_sorted_reviews(limit=c)
    
    def calculate_conf_metrics(self) -> Dict:
        """
        Calculate CoNF-specific metrics for analysis
        """
        all_reviews = self.get_all_reviews()
        if not all_reviews:
            return {"total_reviews": 0, "positive_ratio": 0.0, "persistence_score": 0.0}
        
        # Calculate positive ratio
        positive_count = sum(1 for r in all_reviews if r.stars >= 4.0)
        positive_ratio = positive_count / len(all_reviews)
        
        # Calculate persistence score (how long negative reviews stay at top)
        recent_reviews = self.get_sorted_reviews(limit=5)
        negative_in_recent = sum(1 for r in recent_reviews if r.stars < 4.0)
        persistence_score = negative_in_recent / len(recent_reviews) if recent_reviews else 0.0
        
        return {
            "total_reviews": len(all_reviews),
            "positive_ratio": positive_ratio,
            "persistence_score": persistence_score,
            "recent_negative_count": negative_in_recent,
            "policy": self.review_policy
        }
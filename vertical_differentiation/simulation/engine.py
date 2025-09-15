# engine.py
import json
import uuid
import random
from datetime import datetime
from typing import List, Dict
from config import Config
from .models import Customer, Review, Restaurant
from .llm import LLMInterface
from .logger import SimulationLogger

class RestaurantSimulation:
    def _should_investigate_further(self, reviews: List[Dict]) -> bool:
        """Determine if reviews appear too positive or outdated"""
        if not reviews:
            return False
        
        # Check if mostly 5-star reviews (more than 80%)
        five_star_count = sum(1 for r in reviews if r['stars'] == 5)
        if five_star_count / len(reviews) > 0.8:
            return True
        
        # Check if reviews are outdated (all older than 1 year)
        current_date = datetime.now()
        one_year_ago = current_date.replace(year=current_date.year-1)
        most_recent_date = max(datetime.strptime(r['date'], "%Y-%m-%d %H:%M:%S") for r in reviews)
        if most_recent_date < one_year_ago:
            return True
        
        return False

    def _get_additional_reviews(self, restaurant: Restaurant) -> List[Dict]:
        """Get additional reviews if initial set seems biased"""
        additional = []
        
        # Get some recent reviews (2-3)
        additional.extend(r.__dict__ for r in restaurant.get_recent_reviews(3))
        
        # Get some low-rated reviews (1-2 star, 2-3 reviews)
        for stars in [1, 2]:
            additional.extend(r.__dict__ for r in restaurant.get_reviews_by_rating(stars, 2))
        
        # Remove duplicates and limit total
        unique_reviews = {r['review_id']: r for r in additional}
        return list(unique_reviews.values())[:5]  # Return up to 5 additional reviews

    def _get_combined_reviews(self, restaurant: Restaurant) -> List[Dict]:
        all_reviews = restaurant.initial_reviews + restaurant.reviews
        if restaurant.review_policy == "highest_rating":
            sorted_reviews = sorted(all_reviews, key=lambda x: x.stars, reverse=True)
        elif restaurant.review_policy == "latest":
            sorted_reviews = sorted(all_reviews, key=lambda x: x.date, reverse=True)
        elif restaurant.review_policy == "recent_quality_boost":
            sorted_reviews = self._get_recent_quality_boost_combined_reviews(all_reviews)
        else:
            sorted_reviews = sorted(all_reviews, key=lambda x: x.date, reverse=True)
        return [r.__dict__ for r in sorted_reviews]

    def _get_recent_quality_boost_combined_reviews(self, all_reviews: List) -> List:
        """Apply recent quality boost algorithm to combined reviews (initial + new)"""
        from datetime import datetime, timedelta
        
        current_date = datetime.now()
        thirty_days_ago = current_date - timedelta(days=30)
        ninety_days_ago = current_date - timedelta(days=90)
        
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

    def __init__(self, output_folder=None):
        # Set up output directory
        if output_folder:
            self.output_dir = f"data/outputs/{output_folder}"
        else:
            self.output_dir = "data/outputs"
        
        self.llm = LLMInterface()
        self.logger = SimulationLogger(f"{self.output_dir}/logs")
        # Remove review_policy parameter since both use same sorting
        self.restaurant_a = Restaurant("A")
        self.restaurant_b = Restaurant("B")
        # Give logger access to restaurants
        self.logger.restaurant_a = self.restaurant_a
        self.logger.restaurant_b = self.restaurant_b
        self.shared_reviews = self._load_shared_reviews()
        self.current_day = 0
        self.customers = []

    def _load_shared_reviews(self) -> List[Review]:
        try:
            # Load Restaurant A reviews
            with open("data/inputs/initial_reviews_a.json") as f:
                a_data = json.load(f)
                a_reviews = [
                    Review(
                        review_id=r["review_id"],
                        user_id=r["user_id"],
                        business_id="A",
                        stars=r["stars"],
                        text=r["text"],
                        date=r["date"],
                        ordered_item="(initial)"
                    ) 
                    for r in a_data
                ]
                self.restaurant_a.initial_reviews = a_reviews.copy()
                
            # Load Restaurant B reviews
            with open("data/inputs/initial_reviews_b.json") as f:
                b_data = json.load(f)
                b_reviews = [
                    Review(
                        review_id=r["review_id"],
                        user_id=r["user_id"],
                        business_id="B",
                        stars=r["stars"],
                        text=r["text"],
                        date=r["date"],
                        ordered_item="(initial)"
                    ) 
                    for r in b_data
                ]
                self.restaurant_b.initial_reviews = b_reviews.copy()
                
            return a_reviews + b_reviews
        except FileNotFoundError:
            # Initialize empty lists if files not found
            self.restaurant_a.initial_reviews = []
            self.restaurant_b.initial_reviews = []
            return []

    def _generate_customer(self) -> Customer:
        customer_data = self.llm.generate_customer()
        customer_id=f"cust_{uuid.uuid4().hex[:8]}"
        customer = Customer(
            customer_id=customer_id,
            name=customer_data["name"],
            role_desc={
                "income": customer_data["income"],
                "taste": customer_data["taste"],
                "health": customer_data["health"],
                "dietary_restriction": customer_data["dietary_restriction"],
                "personality": customer_data["personality"]
            }
        )
        self.logger.log_customer_arrival({
            "customer_id": customer_id,
            "name": customer_data["name"],
            **customer_data
        })
        return customer

    def run_day(self):
        self.current_day += 1
        print(f"Day {self.current_day}/{Config.DAYS}")
        
        for _ in range(Config.CUSTOMERS_PER_DAY):
            try:
                customer = self._generate_customer()
                self.customers.append(customer)
                
                # Get base reviews and restaurant info
                a_reviews = self._get_combined_reviews(self.restaurant_a)
                b_reviews = self._get_combined_reviews(self.restaurant_b)
                
                # Prepare initial review sets (5 each)
                a_reviews_shown = a_reviews[:5]
                b_reviews_shown = b_reviews[:5]

                # Get TOTAL ratings and counts (initial + new)
                a_total_rating = self.restaurant_a.get_overall_rating()
                a_total_count = self.restaurant_a.get_review_count()
                b_total_rating = self.restaurant_b.get_overall_rating()
                b_total_count = self.restaurant_b.get_review_count()
                
                # Log initial reviews seen
                self.logger.log_reviews_seen(
                    customer.customer_id, customer.name, self.current_day,
                    "A", a_reviews_shown
                )
                self.logger.log_reviews_seen(
                    customer.customer_id, customer.name, self.current_day,
                    "B", b_reviews_shown
                )
                
                # Check if we need additional reviews
                a_additional_reviews = []
                b_additional_reviews = []
                
                if self._should_investigate_further(a_reviews_shown):
                    a_additional_reviews = self._get_additional_reviews(self.restaurant_a)
                    a_reviews_shown.extend(a_additional_reviews)
                    a_reviews_shown = a_reviews_shown[:10]  # Limit to 10 total
                    
                    # Log additional reviews seen
                    self.logger.log_reviews_seen(
                        customer.customer_id, customer.name, self.current_day,
                        "A", a_additional_reviews, is_additional=True
                    )
                
                if self._should_investigate_further(b_reviews_shown):
                    b_additional_reviews = self._get_additional_reviews(self.restaurant_b)
                    b_reviews_shown.extend(b_additional_reviews)
                    b_reviews_shown = b_reviews_shown[:10]  # Limit to 10 total
                    
                    # Log additional reviews seen
                    self.logger.log_reviews_seen(
                        customer.customer_id, customer.name, self.current_day,
                        "B", b_additional_reviews, is_additional=True
                    )
                
                decision = self.llm.make_decision(
                    {
                        "name": customer.name,
                        "income": customer.role_desc["income"],
                        "taste": customer.role_desc["taste"],
                        "health": customer.role_desc["health"],
                        "dietary_restriction": customer.role_desc["dietary_restriction"],
                        "personality": customer.role_desc["personality"],
                        "customer_id": customer.customer_id
                    },
                    a_reviews_shown,
                    b_reviews_shown,
                    self.restaurant_a.menu,
                    self.restaurant_b.menu,
                    a_total_rating,  # Using total rating
                    a_total_count,   # Using total count
                    b_total_rating,  # Using total rating
                    b_total_count 
                )

                self.logger.log_decision_details(
                    customer.customer_id,
                    customer.name,
                    a_reviews_shown,
                    b_reviews_shown,
                    decision["decision"],
                    decision["reason"],
                    self.current_day)
                
                restaurant = self.restaurant_a if decision["decision"] == "A" else self.restaurant_b
                
                # Let customer choose menu item based on their profile
                menu_choice = self.llm.choose_menu_item(
                    {
                        "name": customer.name,
                        "income": customer.role_desc["income"],
                        "taste": customer.role_desc["taste"],
                        "health": customer.role_desc["health"],
                        "dietary_restriction": customer.role_desc["dietary_restriction"],
                        "personality": customer.role_desc["personality"],
                        "customer_id": customer.customer_id
                    },
                    restaurant.restaurant_id,
                    restaurant.menu
                )
                
                # Validate the chosen item exists in menu, fallback to random if not
                ordered_item = menu_choice.get("chosen_item", "")
                if ordered_item not in restaurant.menu:
                    print(f"Warning: Customer chose '{ordered_item}' which is not on menu. Falling back to random selection.")
                    ordered_item = random.choice(list(restaurant.menu.keys()))
                    menu_reason = "Fallback to random selection due to invalid choice"
                else:
                    menu_reason = menu_choice.get("reason", "No reason provided")
                
                price = restaurant.menu[ordered_item]
                restaurant.revenue += price
                
                self.logger.log_decision(
                    customer.customer_id,
                    customer.name,
                    decision["decision"],
                    decision["reason"],
                    self.current_day
                )
                
                self.logger.log_order(
                    customer.customer_id,
                    customer.name,
                    restaurant.restaurant_id,
                    ordered_item,
                    price,
                    self.current_day,
                    menu_reason  # Add menu selection reason to logging
                )
                
                review_data = self.llm.generate_review(
                    {
                        "customer_id": customer.customer_id,
                        "name": customer.name,
                        "income": customer.role_desc["income"],
                        "taste": customer.role_desc["taste"],
                        "health": customer.role_desc["health"],
                        "dietary_restriction": customer.role_desc["dietary_restriction"],
                        "personality": customer.role_desc["personality"]
                    },
                    restaurant.restaurant_id,
                    ordered_item
                )
                
                rating_reason = review_data.get("rating_reason")
                
                review = Review(
                    review_id=review_data["review_id"],
                    user_id=customer.customer_id,
                    business_id=restaurant.restaurant_id,
                    stars=float(review_data["stars"]),
                    text=review_data["text"],
                    date=review_data["date"],
                    ordered_item=ordered_item
                )

                
                
                self.logger.log_review(review.__dict__, rating_reason)
                restaurant.reviews.append(review)
                
            except Exception as e:
                print(f"Error processing customer: {str(e)}")
                continue

    def run_simulation(self):
        print(f"Starting simulation for {Config.DAYS} days")
        for _ in range(Config.DAYS):
            self.run_day()
        self._save_results()
        print("Simulation complete!")

    def _save_results(self):
        # Ensure output directory exists
        import os
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.logger.save_logs()
        
        # Save simulation metadata
        self._save_metadata()
        
        with open(f"{self.output_dir}/customers.json", "w") as f:
            json.dump([
                {
                    "customer_id": c.customer_id,
                    "name": c.name,
                    "role_desc": c.role_desc
                }
                for c in self.customers
            ], f, indent=2)
        
        with open(f"{self.output_dir}/restaurants.json", "w") as f:
            json.dump({
                "A": {
                    "reviews": [r.__dict__ for r in self.restaurant_a.reviews],
                    "revenue": self.restaurant_a.revenue
                },
                "B": {
                    "reviews": [r.__dict__ for r in self.restaurant_b.reviews],
                    "revenue": self.restaurant_b.revenue
                }
            }, f, indent=2)

    def _save_metadata(self):
        """Save simulation metadata including configurations and setup details"""
        metadata = {
            "simulation_info": {
                "simulation_type": "vertical_differentiation",
                "timestamp": datetime.now().isoformat(),
                "output_folder": self.output_dir.split('/')[-1]
            },
            "configuration": {
                "days": Config.DAYS,
                "customers_per_day": Config.CUSTOMERS_PER_DAY,
                "model": Config.MODEL,
                "log_dir": Config.LOG_DIR,
                "restaurant_a_rating": Config.RESTAURANT_A_RATING,
                "restaurant_b_rating": Config.RESTAURANT_B_RATING,
                "restaurant_a_review_policy": Config.RESTAURANT_A_REVIEW_POLICY,
                "restaurant_b_review_policy": Config.RESTAURANT_B_REVIEW_POLICY
            },
            "restaurant_setup": {
                "restaurant_a": {
                    "id": "A",
                    "type": "High-end restaurant",
                    "quality_rating": Config.RESTAURANT_A_RATING,
                    "review_policy": self.restaurant_a.review_policy,
                    "menu": self.restaurant_a.menu,
                    "average_price": sum(self.restaurant_a.menu.values()) / len(self.restaurant_a.menu),
                    "initial_reviews_count": len(self.restaurant_a.initial_reviews),
                    "initial_avg_rating": sum(r.stars for r in self.restaurant_a.initial_reviews) / len(self.restaurant_a.initial_reviews) if self.restaurant_a.initial_reviews else 0
                },
                "restaurant_b": {
                    "id": "B",
                    "type": "Basic diner",
                    "quality_rating": Config.RESTAURANT_B_RATING,
                    "review_policy": self.restaurant_b.review_policy,
                    "menu": self.restaurant_b.menu,
                    "average_price": sum(self.restaurant_b.menu.values()) / len(self.restaurant_b.menu),
                    "initial_reviews_count": len(self.restaurant_b.initial_reviews),
                    "initial_avg_rating": sum(r.stars for r in self.restaurant_b.initial_reviews) / len(self.restaurant_b.initial_reviews) if self.restaurant_b.initial_reviews else 0
                }
            },
            "simulation_results": {
                "total_customers": len(self.customers),
                "final_ratings": {
                    "restaurant_a": self.restaurant_a.get_overall_rating(),
                    "restaurant_b": self.restaurant_b.get_overall_rating()
                },
                "final_review_counts": {
                    "restaurant_a": self.restaurant_a.get_review_count(),
                    "restaurant_b": self.restaurant_b.get_review_count()
                },
                "total_revenue": {
                    "restaurant_a": self.restaurant_a.revenue,
                    "restaurant_b": self.restaurant_b.revenue
                }
            }
        }
        
        with open(f"{self.output_dir}/simulation_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
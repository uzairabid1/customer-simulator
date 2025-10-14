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
    def _assess_skepticism(self, customer: Customer, reviews: List[Dict], restaurant_id: str) -> Dict:
        """
        Dynamic skepticism assessment based on customer personality and review patterns.
        Returns skepticism level and specific concerns.
        """
        if not reviews:
            return {"level": "none", "concerns": [], "will_investigate": False, "confidence_impact": 0}
        
        concerns = []
        skepticism_score = 0
        
        # 1. Pattern Analysis
        five_star_count = sum(1 for r in reviews if r['stars'] == 5)
        five_star_ratio = five_star_count / len(reviews)
        if five_star_ratio > 0.8:
            concerns.append("too_many_perfect_ratings")
            skepticism_score += 2
        elif five_star_ratio > 0.9:
            concerns.append("suspiciously_perfect_ratings")
            skepticism_score += 3
            
        # 2. Recency Analysis
        current_date = datetime.now()
        six_months_ago = current_date.replace(month=current_date.month-6 if current_date.month > 6 else current_date.month+6, year=current_date.year-1 if current_date.month <= 6 else current_date.year)
        one_year_ago = current_date.replace(year=current_date.year-1)
        
        try:
            most_recent_date = max(datetime.strptime(r['date'], "%Y-%m-%d %H:%M:%S") for r in reviews)
            if most_recent_date < one_year_ago:
                concerns.append("very_outdated_reviews")
                skepticism_score += 3
            elif most_recent_date < six_months_ago:
                concerns.append("outdated_reviews")
                skepticism_score += 1
        except ValueError:
            concerns.append("date_parsing_issues")
            skepticism_score += 1
            
        # 3. Sample Size Analysis
        if len(reviews) < 3:
            concerns.append("too_few_reviews")
            skepticism_score += 1
            
        # 4. Rating Diversity Analysis
        unique_ratings = set(r['stars'] for r in reviews)
        if len(unique_ratings) == 1:
            concerns.append("no_rating_diversity")
            skepticism_score += 2
            
        # 5. Personality-Based Skepticism Modifier
        personality = customer.role_desc.get("personality", "").lower()
        skeptical_personalities = ["analytical", "meticulous", "discerning", "strict", "picky", "reserved", "thoughtful"]
        trusting_personalities = ["easy-going", "easygoing", "relaxed", "carefree", "cheerful", "optimistic", "friendly", "outgoing"]
        
        personality_modifier = 0
        if any(trait in personality for trait in skeptical_personalities):
            personality_modifier = 2  # More skeptical
        elif any(trait in personality for trait in trusting_personalities):
            personality_modifier = -1  # Less skeptical
            
        final_score = max(0, skepticism_score + personality_modifier)
        
        # Determine skepticism level and behavior
        if final_score >= 5:
            level = "high"
            will_investigate = random.random() < 0.8  # 80% chance to investigate
            confidence_impact = -0.3  # Significant negative impact on confidence
        elif final_score >= 3:
            level = "medium" 
            will_investigate = random.random() < 0.6  # 60% chance to investigate
            confidence_impact = -0.15  # Moderate negative impact
        elif final_score >= 1:
            level = "low"
            will_investigate = random.random() < 0.3  # 30% chance to investigate
            confidence_impact = -0.05  # Minor negative impact
        else:
            level = "none"
            will_investigate = False
            confidence_impact = 0
            
        return {
            "level": level,
            "concerns": concerns,
            "will_investigate": will_investigate,
            "confidence_impact": confidence_impact,
            "score": final_score,
            "personality_modifier": personality_modifier
        }

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

    def _assess_post_investigation_effects(self, customer: Customer, initial_skepticism: Dict, 
                                         additional_reviews: List[Dict], restaurant_id: str) -> Dict:
        """
        Assess how additional reviews affect customer skepticism and confidence.
        Some customers remain doubtful even after investigation.
        """
        if not additional_reviews:
            return {
                "resolved": False,
                "confidence_change": initial_skepticism["confidence_impact"],
                "ongoing_doubt": True,
                "reason": "no_additional_reviews_found"
            }
        
        # Analyze additional reviews
        additional_avg_rating = sum(r['stars'] for r in additional_reviews) / len(additional_reviews)
        has_negative_reviews = any(r['stars'] <= 2 for r in additional_reviews)
        has_recent_reviews = True  # We specifically fetch recent ones
        
        personality = customer.role_desc.get("personality", "").lower()
        
        # Personality affects how they interpret additional evidence
        if "analytical" in personality or "meticulous" in personality:
            # Analytical customers are thorough but can be convinced by data
            if has_negative_reviews and additional_avg_rating < 3.5:
                return {
                    "resolved": True,
                    "confidence_change": -0.2,  # Confirmed concerns
                    "ongoing_doubt": False,
                    "reason": "analytical_confirmed_concerns"
                }
            elif additional_avg_rating >= 4.0:
                return {
                    "resolved": True,
                    "confidence_change": 0.1,  # Concerns alleviated
                    "ongoing_doubt": False,
                    "reason": "analytical_concerns_resolved"
                }
        
        elif "picky" in personality or "strict" in personality:
            # Picky customers often remain unsatisfied
            return {
                "resolved": False,
                "confidence_change": initial_skepticism["confidence_impact"] - 0.1,  # Even more doubtful
                "ongoing_doubt": True,
                "reason": "picky_never_satisfied"
            }
            
        elif "discerning" in personality:
            # Discerning customers need high quality evidence
            if additional_avg_rating >= 4.5:
                return {
                    "resolved": True,
                    "confidence_change": 0.05,
                    "ongoing_doubt": False,
                    "reason": "discerning_quality_confirmed"
                }
            else:
                return {
                    "resolved": False,
                    "confidence_change": initial_skepticism["confidence_impact"],
                    "ongoing_doubt": True,
                    "reason": "discerning_quality_insufficient"
                }
        
        elif any(trait in personality for trait in ["shy", "reserved", "thoughtful"]):
            # Shy/reserved customers often remain worried regardless
            doubt_persists = random.random() < 0.7  # 70% chance doubt persists
            if doubt_persists:
                return {
                    "resolved": False,
                    "confidence_change": initial_skepticism["confidence_impact"] - 0.05,
                    "ongoing_doubt": True,
                    "reason": "anxious_persistent_worry"
                }
        
        # Default case - most customers are somewhat reassured
        if additional_avg_rating >= 3.5:
            return {
                "resolved": True,
                "confidence_change": max(0, initial_skepticism["confidence_impact"] + 0.15),
                "ongoing_doubt": False,
                "reason": "general_concerns_addressed"
            }
        else:
            return {
                "resolved": False,
                "confidence_change": initial_skepticism["confidence_impact"] - 0.1,
                "ongoing_doubt": True,
                "reason": "additional_reviews_concerning"
            }

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
        return [r.__dict__ for r in sorted_reviews]  # Convert to dict

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
        self.restaurant_a = Restaurant("A", Config.RESTAURANT_A_REVIEW_POLICY)
        self.restaurant_b = Restaurant("B", Config.RESTAURANT_B_REVIEW_POLICY)
        # Give logger access to restaurants
        self.logger.restaurant_a = self.restaurant_a
        self.logger.restaurant_b = self.restaurant_b
        self.shared_reviews = self._load_shared_reviews()
        self.current_day = 0
        self.customers = []

    def _load_shared_reviews(self) -> List[Review]:
        try:
            with open("data/inputs/initial_reviews.json") as f:
                initial_data = json.load(f)
                reviews = [
                    Review(
                        review_id=r["review_id"],
                        user_id=r["user_id"],
                        business_id="shared",
                        stars=r["stars"],
                        text=r["text"],
                        date=r["date"],
                        ordered_item="(initial)"
                    ) 
                    for r in initial_data
                ]
                
                # Assign to both restaurants
                self.restaurant_a.initial_reviews = reviews.copy()
                self.restaurant_b.initial_reviews = reviews.copy()
                
                # Return the loaded reviews for shared_reviews
                return reviews
        except FileNotFoundError:
            # Initialize empty lists if file not found
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
                
                # Assess skepticism for both restaurants
                a_skepticism = self._assess_skepticism(customer, a_reviews_shown, "A")
                b_skepticism = self._assess_skepticism(customer, b_reviews_shown, "B")
                
                # Handle investigation behavior
                a_additional_reviews = []
                b_additional_reviews = []
                a_post_investigation = None
                b_post_investigation = None
                
                if a_skepticism["will_investigate"]:
                    a_additional_reviews = self._get_additional_reviews(self.restaurant_a)
                    a_reviews_shown.extend(a_additional_reviews)
                    a_reviews_shown = a_reviews_shown[:10]  # Limit to 10 total
                    
                    # Assess post-investigation effects
                    a_post_investigation = self._assess_post_investigation_effects(
                        customer, a_skepticism, a_additional_reviews, "A"
                    )
                    
                    # Log additional reviews seen and skepticism details
                    self.logger.log_reviews_seen(
                        customer.customer_id, customer.name, self.current_day,
                        "A", a_additional_reviews, is_additional=True
                    )
                    self.logger.log_skepticism_assessment(
                        customer.customer_id, customer.name, self.current_day,
                        "A", a_skepticism, a_post_investigation
                    )
                
                if b_skepticism["will_investigate"]:
                    b_additional_reviews = self._get_additional_reviews(self.restaurant_b)
                    b_reviews_shown.extend(b_additional_reviews)
                    b_reviews_shown = b_reviews_shown[:10]  # Limit to 10 total
                    
                    # Assess post-investigation effects
                    b_post_investigation = self._assess_post_investigation_effects(
                        customer, b_skepticism, b_additional_reviews, "B"
                    )
                    
                    # Log additional reviews seen and skepticism details
                    self.logger.log_reviews_seen(
                        customer.customer_id, customer.name, self.current_day,
                        "B", b_additional_reviews, is_additional=True
                    )
                    self.logger.log_skepticism_assessment(
                        customer.customer_id, customer.name, self.current_day,
                        "B", b_skepticism, b_post_investigation
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
                    b_total_count,   # Using total count
                    self.restaurant_a.review_policy,  # Pass policy A
                    self.restaurant_b.review_policy,  # Pass policy B
                    a_skepticism,      # Pass skepticism data A
                    b_skepticism,      # Pass skepticism data B
                    a_post_investigation,  # Pass post-investigation A
                    b_post_investigation   # Pass post-investigation B
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
        
        # Log review bias analysis at the end of each day
        self.logger.log_review_bias_analysis(self.current_day)

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
                "simulation_type": "reviews_orientation",
                "timestamp": datetime.now().isoformat(),
                "output_folder": self.output_dir.split('/')[-1]
            },
            "configuration": {
                "days": Config.DAYS,
                "customers_per_day": Config.CUSTOMERS_PER_DAY,
                "model": Config.MODEL,
                "log_dir": Config.LOG_DIR
            },
            "restaurant_setup": {
                "restaurant_a": {
                    "id": "A",
                    "review_policy": self.restaurant_a.review_policy,
                    "menu": self.restaurant_a.menu,
                    "initial_reviews_count": len(self.restaurant_a.initial_reviews),
                    "initial_avg_rating": sum(r.stars for r in self.restaurant_a.initial_reviews) / len(self.restaurant_a.initial_reviews) if self.restaurant_a.initial_reviews else 0
                },
                "restaurant_b": {
                    "id": "B", 
                    "review_policy": self.restaurant_b.review_policy,
                    "menu": self.restaurant_b.menu,
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
                },
                "final_review_bias_analysis": {
                    "restaurant_a": self.restaurant_a.get_review_bias_analysis(),
                    "restaurant_b": self.restaurant_b.get_review_bias_analysis()
                }
            }
        }
        
        with open(f"{self.output_dir}/simulation_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
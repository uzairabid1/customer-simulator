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
                a_reviews_shown = a_reviews[:Config.CONF_LIMITED_ATTENTION]
                b_reviews_shown = b_reviews[:Config.CONF_LIMITED_ATTENTION]

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

                total_cap = Config.CONF_LIMITED_ATTENTION + Config.CONF_SKEPTICAL_REVIEWS

                if a_skepticism["will_investigate"]:
                    a_additional_reviews = self._get_additional_reviews(self.restaurant_a)
                    a_reviews_shown.extend(a_additional_reviews)
                    a_reviews_shown = a_reviews_shown[:total_cap]  # Limit to 10 total
                    
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
                    b_reviews_shown = b_reviews_shown[:total_cap]  # Limit to 10 total
                    
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
                    self.restaurant_a,     # Pass restaurant A object
                    self.restaurant_b,     # Pass restaurant B object
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
                    ordered_item,
                    restaurant  # Pass restaurant object for dynamic quality rating
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
    
    def run_conf_experiment(self):
        """
        Run the Cost of Newest First experiment:
        Two restaurants competing - Restaurant A (newest first) vs Restaurant B (random)
        """
        import numpy as np
        
        print(f"Configuration:")
        print(f"- Restaurant A True Quality (μ): {Config.CONF_TRUE_QUALITY_A}")
        print(f"- Restaurant B True Quality (μ): {Config.CONF_TRUE_QUALITY_B}")
        print(f"- Dynamic Pricing: Each customer chooses a menu item with its actual price")
        print(f"- Total customers: {Config.CONF_NUM_CUSTOMERS}")
        print(f"- Limited attention: {Config.CONF_LIMITED_ATTENTION} + {Config.CONF_SKEPTICAL_REVIEWS} skeptical")
        print()
        
        # Set up restaurants with their policies
        restaurant_a = self.restaurant_a
        restaurant_b = self.restaurant_b
        
        # Ensure policies are set correctly
        restaurant_a.review_policy = Config.RESTAURANT_A_REVIEW_POLICY
        restaurant_b.review_policy = Config.RESTAURANT_B_REVIEW_POLICY
        
        print(f"Restaurant A {Config.RESTAURANT_A_REVIEW_POLICY} menu items and prices:")
        for item, price in restaurant_a.menu.items():
            print(f"  - {item}: ${price}")
        print()
        
        print(f"Restaurant B {Config.RESTAURANT_B_REVIEW_POLICY} menu items and prices:")
        for item, price in restaurant_b.menu.items():
            print(f"  - {item}: ${price}")
        print()
        
        # Initialize both restaurants with reviews
        self._initialize_conf_reviews(restaurant_a)
        self._initialize_conf_reviews(restaurant_b)
        
        # Run competitive simulation
        print("=== Running Competitive CoNF Experiment ===")
        results = self._run_competitive_conf_simulation(restaurant_a, restaurant_b)
        
        # Calculate CoNF analysis
        self._calculate_and_log_competitive_conf_results(results)
        
        # Save results
        self._save_competitive_conf_results(results)
    
    def _run_competitive_conf_simulation(self, restaurant_a: Restaurant, restaurant_b: Restaurant) -> Dict:
        """
        Run competitive simulation where customers choose between two restaurants over multiple days
        """
        import random
        import numpy as np
        import os
        from datetime import datetime
        
        # Create console log file
        log_file_path = os.path.join(self.output_dir, "simulation_console_log.txt")
        os.makedirs(self.output_dir, exist_ok=True)
        
        results = {
            "restaurant_a": {
                "policy": Config.RESTAURANT_A_REVIEW_POLICY,
                "revenue": 0,
                "purchases": 0,
                "customers_visited": 0,
                "customer_decisions": [],
                "daily_stats": []
            },
            "restaurant_b": {
                "policy": Config.RESTAURANT_B_REVIEW_POLICY,
                "revenue": 0,
                "purchases": 0,
                "customers_visited": 0,
                "customer_decisions": [],
                "daily_stats": []
            },
            "total_customers": Config.CONF_NUM_CUSTOMERS,
            "days": Config.DAYS,
            "customers_per_day": Config.CUSTOMERS_PER_DAY
        }
        
        # Calculate customers per day
        customers_per_day = Config.CONF_NUM_CUSTOMERS // Config.DAYS
        remaining_customers = Config.CONF_NUM_CUSTOMERS % Config.DAYS
        
        customer_counter = 0
        
        with open(log_file_path, 'w', encoding='utf-8') as log_file:
            def log_and_print(message):
                print(message)
                log_file.write(message + '\n')
                log_file.flush()
            
            log_and_print(f"=== COMPETITIVE CoNF SIMULATION STARTED ===")
            log_and_print(f"Timestamp: {datetime.now().isoformat()}")
            log_and_print(f"Total customers: {Config.CONF_NUM_CUSTOMERS} over {Config.DAYS} days")
            log_and_print(f"Base customers per day: {customers_per_day}")
            log_and_print("")
            
            for day in range(1, Config.DAYS + 1):
                # Add extra customer to some days if there's remainder
                day_customers = customers_per_day + (1 if day <= remaining_customers else 0)
                
                log_and_print(f"=== DAY {day} ===")
                log_and_print(f"Customers today: {day_customers}")
                
                # Daily stats tracking
                daily_stats_a = {"day": day, "customers_visited": 0, "purchases": 0, "revenue": 0}
                daily_stats_b = {"day": day, "customers_visited": 0, "purchases": 0, "revenue": 0}
                
                for i in range(day_customers):
                    customer_counter += 1
                    
                    # Generate customer with CoNF parameters
                    customer = self._generate_conf_customer(f"day{day}_customer_{i+1}")
                    
                    # Customer evaluates both restaurants and chooses the better one
                    restaurant_choice, chosen_restaurant, decision_data = self._customer_chooses_restaurant(
                        customer, restaurant_a, restaurant_b, log_and_print
                    )
                    
                    # Record the visit
                    if restaurant_choice == "A":
                        results["restaurant_a"]["customers_visited"] += 1
                        results["restaurant_a"]["customer_decisions"].append(decision_data)
                        daily_stats_a["customers_visited"] += 1
                    else:
                        results["restaurant_b"]["customers_visited"] += 1
                        results["restaurant_b"]["customer_decisions"].append(decision_data)
                        daily_stats_b["customers_visited"] += 1
                    
                    # Customer makes purchase decision at chosen restaurant
                    if decision_data["will_purchase"]:
                        item_price = decision_data["item_price"]
                        chosen_item = decision_data["chosen_item"]
                        
                        if restaurant_choice == "A":
                            results["restaurant_a"]["revenue"] += item_price
                            results["restaurant_a"]["purchases"] += 1
                            restaurant_a.revenue += item_price
                            daily_stats_a["purchases"] += 1
                            daily_stats_a["revenue"] += item_price
                            
                            # Customer leaves review at Restaurant A
                            new_review = restaurant_a.add_conf_review(
                                customer.customer_id, Config.CONF_TRUE_QUALITY_A, chosen_item
                            )
                            log_and_print(f"  Customer {i+1}: PURCHASED {chosen_item} at Restaurant A (${item_price})")
                            log_and_print(f"    → Left review: {new_review.stars} stars")
                        else:
                            results["restaurant_b"]["revenue"] += item_price
                            results["restaurant_b"]["purchases"] += 1
                            restaurant_b.revenue += item_price
                            daily_stats_b["purchases"] += 1
                            daily_stats_b["revenue"] += item_price
                            
                            # Customer leaves review at Restaurant B
                            new_review = restaurant_b.add_conf_review(
                                customer.customer_id, Config.CONF_TRUE_QUALITY_B, chosen_item
                            )
                            log_and_print(f"  Customer {i+1}: PURCHASED {chosen_item} at Restaurant B (${item_price})")
                            log_and_print(f"    → Left review: {new_review.stars} stars")
                    else:
                        log_and_print(f"  Customer {i+1}: NO PURCHASE at Restaurant {restaurant_choice}")
                        log_and_print(f"    → Valuation {decision_data['valuation_estimate']:.1f} <= Price ${decision_data['item_price']}")
                
                # End of day summary
                results["restaurant_a"]["daily_stats"].append(daily_stats_a)
                results["restaurant_b"]["daily_stats"].append(daily_stats_b)
                
                log_and_print(f"\n--- Day {day} Summary ---")
                log_and_print(f"Restaurant A: {daily_stats_a['customers_visited']} visitors, {daily_stats_a['purchases']} purchases, ${daily_stats_a['revenue']:.2f} revenue")
                log_and_print(f"Restaurant B: {daily_stats_b['customers_visited']} visitors, {daily_stats_b['purchases']} purchases, ${daily_stats_b['revenue']:.2f} revenue")
                log_and_print("")
            
            # Final simulation summary
            log_and_print("=== SIMULATION COMPLETED ===")
            log_and_print(f"Total customers processed: {customer_counter}")
            log_and_print(f"Console log saved to: {log_file_path}")
            log_and_print("")
        
        # Calculate final metrics
        for restaurant_key in ["restaurant_a", "restaurant_b"]:
            restaurant_data = results[restaurant_key]
            if restaurant_data["customers_visited"] > 0:
                restaurant_data["purchase_rate"] = restaurant_data["purchases"] / restaurant_data["customers_visited"]
                restaurant_data["avg_revenue_per_visitor"] = restaurant_data["revenue"] / restaurant_data["customers_visited"]
            else:
                restaurant_data["purchase_rate"] = 0
                restaurant_data["avg_revenue_per_visitor"] = 0
        
        return results
    
    def _customer_chooses_restaurant(self, customer: Customer, restaurant_a: Restaurant, restaurant_b: Restaurant, log_func) -> tuple:
        """
        Customer evaluates both restaurants and chooses the one with higher expected utility
        """
        import random
        
        # Evaluate Restaurant A
        valuation_a, decision_a = self._evaluate_restaurant_for_customer(
            customer, restaurant_a, Config.CONF_TRUE_QUALITY_A, "A"
        )
        
        # Evaluate Restaurant B  
        valuation_b, decision_b = self._evaluate_restaurant_for_customer(
            customer, restaurant_b, Config.CONF_TRUE_QUALITY_B, "B"
        )
        
        # Customer chooses restaurant with higher expected utility
        if valuation_a["expected_utility"] > valuation_b["expected_utility"]:
            chosen_restaurant = restaurant_a
            restaurant_choice = "A"
            decision_data = decision_a
            log_func(f"  {customer.customer_id}: Chose Restaurant A (utility: {valuation_a['expected_utility']:.1f} > {valuation_b['expected_utility']:.1f})")
        else:
            chosen_restaurant = restaurant_b
            restaurant_choice = "B" 
            decision_data = decision_b
            log_func(f"  {customer.customer_id}: Chose Restaurant B (utility: {valuation_b['expected_utility']:.1f} > {valuation_a['expected_utility']:.1f})")
        
        return restaurant_choice, chosen_restaurant, decision_data
    
    def _evaluate_restaurant_for_customer(self, customer: Customer, restaurant: Restaurant, true_quality: float, restaurant_id: str) -> tuple:
        """
        Customer evaluates a restaurant by reading reviews and estimating utility
        """
        import random
        
        # Customer chooses a menu item they're interested in
        menu_items = list(restaurant.menu.keys())
        chosen_item = random.choice(menu_items)
        item_price = restaurant.menu[chosen_item]
        
        # Customer sees initial reviews
        initial_reviews = restaurant.get_conf_reviews_for_customer(Config.CONF_LIMITED_ATTENTION)
        mu_estimate = customer.update_belief_beta_bernoulli(initial_reviews)
        valuation_estimate = customer.get_valuation_estimate(mu_estimate)
        
        # Assess skepticism
        is_skeptical = self._assess_conf_skepticism(initial_reviews, customer)
        
        if is_skeptical:
            # Customer sees additional reviews
            additional_reviews = restaurant.get_conf_reviews_for_customer(Config.CONF_SKEPTICAL_REVIEWS)
            all_reviews = initial_reviews + additional_reviews
            mu_estimate = customer.update_belief_beta_bernoulli(all_reviews)
            valuation_estimate = customer.get_valuation_estimate(mu_estimate)
            reviews_seen = all_reviews
        else:
            reviews_seen = initial_reviews
        
        # Purchase decision: buy if valuation > item_price
        will_purchase = valuation_estimate > item_price
        expected_utility = valuation_estimate - item_price  # Consumer surplus
        
        # Log which specific reviews the customer read
        reviews_read_details = [
            {
                "review_id": r.review_id,
                "stars": r.stars,
                "text": r.text[:100] + "..." if len(r.text) > 100 else r.text,
                "date": r.date,
                "user_id": r.user_id
            } for r in reviews_seen
        ]
        
        # Record decision with detailed review logging
        decision = {
            "customer_id": customer.customer_id,
            "restaurant_evaluated": restaurant_id,
            "theta": customer.theta,
            "chosen_item": chosen_item,
            "item_price": item_price,
            "reviews_seen_count": len(reviews_seen),
            "reviews_read_details": reviews_read_details,
            "positive_reviews": sum(1 for r in reviews_seen if r.stars >= 4.0),
            "negative_reviews": sum(1 for r in reviews_seen if r.stars < 4.0),
            "average_stars_seen": sum(r.stars for r in reviews_seen) / len(reviews_seen) if reviews_seen else 0,
            "mu_estimate": mu_estimate,
            "valuation_estimate": valuation_estimate,
            "expected_utility": expected_utility,
            "will_purchase": will_purchase,
            "is_skeptical": is_skeptical,
            "beta_prior": {"alpha": customer.alpha, "beta": customer.beta},
            "beta_posterior": {
                "alpha": customer.alpha + sum(1 for r in reviews_seen if r.stars >= 4.0),
                "beta": customer.beta + sum(1 for r in reviews_seen if r.stars < 4.0)
            }
        }
        
        valuation_data = {
            "expected_utility": expected_utility,
            "valuation_estimate": valuation_estimate,
            "item_price": item_price
        }
        
        return valuation_data, decision
    
    def _initialize_conf_reviews(self, restaurant: Restaurant):
        """Initialize restaurant with actual initial reviews from input file"""
        # Load initial reviews from input file
        try:
            with open("data/inputs/initial_reviews_a.json") as f:
                initial_data = json.load(f)
                
            # Clear any existing reviews
            restaurant.initial_reviews = []
            restaurant.reviews = []
            
            # Add initial reviews to restaurant
            for review_data in initial_data:
                review = Review(
                    review_id=review_data["review_id"],
                    user_id=review_data["user_id"],
                    business_id=review_data["business_id"],
                    stars=review_data["stars"],
                    text=review_data["text"],
                    date=review_data["date"]
                )
                restaurant.initial_reviews.append(review)
                
            print(f"Loaded {len(restaurant.initial_reviews)} initial reviews from input file")
            
        except FileNotFoundError:
            print("Warning: initial_reviews_a.json not found, generating reviews based on true quality")
            # Fallback to generated reviews
            for i in range(20):
                customer_id = f"init_{restaurant.restaurant_id}_{i}"
                restaurant.add_conf_review(customer_id, Config.CONF_TRUE_QUALITY)
    
    def _run_conf_simulation_for_restaurant(self, restaurant: Restaurant, restaurant_id: str) -> Dict:
        """Run CoNF simulation for a single restaurant"""
        results = {
            "restaurant_id": restaurant_id,
            "policy": restaurant.review_policy,
            "revenue": 0,
            "purchases": 0,
            "customers": 0,
            "customer_decisions": []
        }
        
        for i in range(Config.CONF_NUM_CUSTOMERS):
            # Generate customer with CoNF parameters
            customer = self._generate_conf_customer(f"{restaurant_id}_{i}")
            results["customers"] += 1
            
            # Customer chooses a menu item they're interested in
            menu_items = list(restaurant.menu.keys())
            chosen_item = random.choice(menu_items)
            item_price = restaurant.menu[chosen_item]
            
            # Customer sees initial reviews
            initial_reviews = restaurant.get_conf_reviews_for_customer(Config.CONF_LIMITED_ATTENTION)
            mu_estimate = customer.update_belief_beta_bernoulli(initial_reviews)
            valuation_estimate = customer.get_valuation_estimate(mu_estimate)
            
            # Assess skepticism
            is_skeptical = self._assess_conf_skepticism(initial_reviews, customer)
            
            if is_skeptical:
                # Customer sees additional reviews
                additional_reviews = restaurant.get_conf_reviews_for_customer(Config.CONF_SKEPTICAL_REVIEWS)
                all_reviews = initial_reviews + additional_reviews
                mu_estimate = customer.update_belief_beta_bernoulli(all_reviews)
                valuation_estimate = customer.get_valuation_estimate(mu_estimate)
                reviews_seen = all_reviews
            else:
                reviews_seen = initial_reviews
            
            # Purchase decision: buy if valuation > item_price
            will_purchase = valuation_estimate > item_price
            
            # Log which specific reviews the customer read
            reviews_read_details = [
                {
                    "review_id": r.review_id,
                    "stars": r.stars,
                    "text": r.text[:100] + "..." if len(r.text) > 100 else r.text,
                    "date": r.date,
                    "user_id": r.user_id
                } for r in reviews_seen
            ]
            
            # Record decision with detailed review logging
            decision = {
                "customer_id": customer.customer_id,
                "theta": customer.theta,
                "chosen_item": chosen_item,
                "item_price": item_price,
                "reviews_seen_count": len(reviews_seen),
                "reviews_read_details": reviews_read_details,
                "positive_reviews": sum(1 for r in reviews_seen if r.stars >= 4.0),
                "negative_reviews": sum(1 for r in reviews_seen if r.stars < 4.0),
                "average_stars_seen": sum(r.stars for r in reviews_seen) / len(reviews_seen) if reviews_seen else 0,
                "mu_estimate": mu_estimate,
                "valuation_estimate": valuation_estimate,
                "will_purchase": will_purchase,
                "is_skeptical": is_skeptical,
                "beta_prior": {"alpha": customer.alpha, "beta": customer.beta},
                "beta_posterior": {
                    "alpha": customer.alpha + sum(1 for r in reviews_seen if r.stars >= 4.0),
                    "beta": customer.beta + sum(1 for r in reviews_seen if r.stars < 4.0)
                }
            }
            results["customer_decisions"].append(decision)
            
            if will_purchase:
                results["revenue"] += item_price
                results["purchases"] += 1
                restaurant.revenue += item_price
                
                # Customer leaves a review (endogenous process) - use chosen item
                new_review = restaurant.add_conf_review(customer.customer_id, Config.CONF_TRUE_QUALITY, chosen_item)
                
                print(f"Customer {i+1}: PURCHASED {chosen_item} (val: {valuation_estimate:.1f} > price: ${item_price})")
                print(f"  → Read reviews: {[r.review_id for r in reviews_seen]} (avg: {sum(r.stars for r in reviews_seen)/len(reviews_seen):.1f} stars)")
                print(f"  → Left review: {new_review.stars} stars")
            else:
                print(f"Customer {i+1}: NO PURCHASE {chosen_item} (val: {valuation_estimate:.1f} <= price: ${item_price})")
                print(f"  → Read reviews: {[r.review_id for r in reviews_seen]} (avg: {sum(r.stars for r in reviews_seen)/len(reviews_seen):.1f} stars)")
        
        # Calculate final metrics
        results["purchase_rate"] = results["purchases"] / results["customers"]
        results["avg_revenue_per_customer"] = results["revenue"] / results["customers"]
        results["final_metrics"] = restaurant.calculate_conf_metrics()
        results["final_reviews"] = [
            {
                "stars": r.stars,
                "date": r.date,
                "customer_id": r.user_id
            } for r in restaurant.get_all_reviews()
        ]
        
        print(f"\nFinal Results for {restaurant_id} ({restaurant.review_policy}):")
        print(f"  - Total revenue: ${results['revenue']:.2f}")
        print(f"  - Purchase rate: {results['purchase_rate']:.1%}")
        print(f"  - Reviews generated: {len(restaurant.reviews)}")
        print(f"  - Positive ratio: {results['final_metrics']['positive_ratio']:.1%}")
        
        return results
    
    def _generate_conf_customer(self, customer_id: str) -> Customer:
        """Generate customer for CoNF experiment"""
        import numpy as np
        
        theta = np.random.normal(Config.CONF_THETA_MEAN, Config.CONF_THETA_STD)
        
        return Customer(
            customer_id=customer_id,
            name=f"CoNF_Customer_{customer_id}",
            role_desc={"type": "conf_experiment"},
            theta=theta,
            alpha=Config.CONF_PRIOR_ALPHA,
            beta=Config.CONF_PRIOR_BETA
        )
    
    def _assess_conf_skepticism(self, reviews: List[Review], customer: Customer) -> bool:
        """Simple skepticism model for CoNF experiment"""
        if len(reviews) == 0:
            return True
            
        positive_ratio = sum(1 for r in reviews if r.stars >= 4.0) / len(reviews)
        
        # Skeptical if all reviews are the same or customer has extreme preferences
        is_uniform = positive_ratio == 0.0 or positive_ratio == 1.0
        is_extreme_customer = abs(customer.theta) > 30.0  # Adjusted for price scale
        
        return is_uniform or is_extreme_customer
    
    def _calculate_and_log_conf_results(self, results_newest: Dict, results_random: Dict):
        """Calculate and display CoNF analysis"""
        newest_revenue = results_newest["avg_revenue_per_customer"]
        random_revenue = results_random["avg_revenue_per_customer"]
        
        if newest_revenue > 0:
            conf_ratio = random_revenue / newest_revenue
            revenue_loss = (random_revenue - newest_revenue) / random_revenue * 100 if random_revenue > 0 else 0
        else:
            conf_ratio = float('inf')
            revenue_loss = 100.0
        
        print(f"\n=== COST OF NEWEST FIRST ANALYSIS ===")
        print(f"Same Restaurant - Newest First Policy:")
        print(f"  - Revenue per customer: ${newest_revenue:.2f}")
        print(f"  - Purchase rate: {results_newest['purchase_rate']:.1%}")
        print(f"  - Total purchases: {results_newest['purchases']}/{results_newest['customers']}")
        print(f"  - Final reviews: {len(results_newest.get('final_reviews', []))}")
        
        print(f"\nSame Restaurant - Random Policy:")
        print(f"  - Revenue per customer: ${random_revenue:.2f}")
        print(f"  - Purchase rate: {results_random['purchase_rate']:.1%}")
        print(f"  - Total purchases: {results_random['purchases']}/{results_random['customers']}")
        print(f"  - Final reviews: {len(results_random.get('final_reviews', []))}")
        
        print(f"\nCoNF Analysis:")
        print(f"  - CoNF Ratio (Random/Newest): {conf_ratio:.3f}")
        print(f"  - Revenue Loss from Newest First: {revenue_loss:.1f}%")
        print(f"  - Absolute Revenue Difference: ${random_revenue - newest_revenue:.2f}")
        
        if conf_ratio > 1.0:
            print("  ✓ CoNF DETECTED: Random policy generates higher revenue")
            print("    → Negative reviews persist longer under Newest First")
        else:
            print("  ✗ No CoNF detected: Newest First performs better or equal")
    
    def _save_conf_results(self, results_newest: Dict, results_random: Dict):
        """Save CoNF experiment results"""
        import os
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        conf_results = {
            "experiment_type": "cost_of_newest_first_single_restaurant",
            "description": "Single restaurant tested with two review policies",
            "config": {
                "true_quality": Config.CONF_TRUE_QUALITY,
                "pricing_model": "dynamic_menu_items",
                "num_customers_per_policy": Config.CONF_NUM_CUSTOMERS,
                "limited_attention": Config.CONF_LIMITED_ATTENTION,
                "skeptical_reviews": Config.CONF_SKEPTICAL_REVIEWS,
                "prior_alpha": Config.CONF_PRIOR_ALPHA,
                "prior_beta": Config.CONF_PRIOR_BETA,
                "theta_mean": Config.CONF_THETA_MEAN,
                "theta_std": Config.CONF_THETA_STD
            },
            "newest_first_results": results_newest,
            "random_results": results_random,
            "conf_analysis": {
                "newest_first_revenue_per_customer": results_newest["avg_revenue_per_customer"],
                "random_revenue_per_customer": results_random["avg_revenue_per_customer"],
                "conf_ratio": results_random["avg_revenue_per_customer"] / results_newest["avg_revenue_per_customer"] if results_newest["avg_revenue_per_customer"] > 0 else float('inf'),
                "revenue_loss_percentage": (results_random["avg_revenue_per_customer"] - results_newest["avg_revenue_per_customer"]) / results_random["avg_revenue_per_customer"] * 100 if results_random["avg_revenue_per_customer"] > 0 else 0,
                "absolute_revenue_difference": results_random["avg_revenue_per_customer"] - results_newest["avg_revenue_per_customer"],
                "conf_detected": results_random["avg_revenue_per_customer"] > results_newest["avg_revenue_per_customer"]
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Save to JSON file
        conf_file = os.path.join(self.output_dir, "conf_experiment_results.json")
        with open(conf_file, 'w') as f:
            json.dump(conf_results, f, indent=2)
        
        print(f"\nCoNF results saved to: {conf_file}")

    def run_simulation(self):
        if Config.ENABLE_CONF_EXPERIMENT:
            print("=== RUNNING COST OF NEWEST FIRST (CoNF) EXPERIMENT ===")
            self.run_conf_experiment()
        else:
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
                    "quality_rating": self.restaurant_a.get_quality_rating(),  # Dynamic quality rating
                    "review_policy": self.restaurant_a.review_policy,
                    "menu": self.restaurant_a.menu,
                    "average_price": sum(self.restaurant_a.menu.values()) / len(self.restaurant_a.menu),
                    "initial_reviews_count": len(self.restaurant_a.initial_reviews),
                    "initial_avg_rating": sum(r.stars for r in self.restaurant_a.initial_reviews) / len(self.restaurant_a.initial_reviews) if self.restaurant_a.initial_reviews else 0
                },
                "restaurant_b": {
                    "id": "B",
                    "type": "Basic diner",
                    "quality_rating": self.restaurant_b.get_quality_rating(),  # Dynamic quality rating
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
                },
                "final_review_bias_analysis": {
                    "restaurant_a": self.restaurant_a.get_review_bias_analysis(),
                    "restaurant_b": self.restaurant_b.get_review_bias_analysis()
                }
            }
        }
        
        with open(f"{self.output_dir}/simulation_metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
    
    def _calculate_and_log_competitive_conf_results(self, results: Dict):
        """Calculate and log competitive CoNF analysis"""
        restaurant_a = results["restaurant_a"]
        restaurant_b = results["restaurant_b"]
        
        print("\n" + "="*60)
        print("COMPETITIVE CoNF EXPERIMENT RESULTS")
        print("="*60)
        
        print(f"\nSimulation Overview:")
        print(f"  - Total days: {results['days']}")
        print(f"  - Total customers: {results['total_customers']}")
        
        print(f"\nRestaurant A:")
        print(f"  - Customers visited: {restaurant_a['customers_visited']}")
        print(f"  - Purchases: {restaurant_a['purchases']}")
        print(f"  - Purchase rate: {restaurant_a['purchase_rate']:.1%}")
        print(f"  - Total revenue: ${restaurant_a['revenue']:.2f}")
        print(f"  - Avg revenue per visitor: ${restaurant_a['avg_revenue_per_visitor']:.2f}")
        
        print(f"\nRestaurant B:")
        print(f"  - Customers visited: {restaurant_b['customers_visited']}")
        print(f"  - Purchases: {restaurant_b['purchases']}")
        print(f"  - Purchase rate: {restaurant_b['purchase_rate']:.1%}")
        print(f"  - Total revenue: ${restaurant_b['revenue']:.2f}")
        print(f"  - Avg revenue per visitor: ${restaurant_b['avg_revenue_per_visitor']:.2f}")
        
        # Daily breakdown
        print(f"\nDaily Performance:")
        for day_stats_a, day_stats_b in zip(restaurant_a['daily_stats'], restaurant_b['daily_stats']):
            day = day_stats_a['day']
            print(f"  Day {day}:")
            print(f"    Restaurant A: {day_stats_a['customers_visited']} visitors, {day_stats_a['purchases']} purchases, ${day_stats_a['revenue']:.2f}")
            print(f"    Restaurant B: {day_stats_b['customers_visited']} visitors, {day_stats_b['purchases']} purchases, ${day_stats_b['revenue']:.2f}")
        
        # Calculate competitive metrics
        total_customers = results["total_customers"]
        market_share_a = restaurant_a['customers_visited'] / total_customers
        market_share_b = restaurant_b['customers_visited'] / total_customers
        
        print(f"\nCompetitive Analysis:")
        print(f"  - Restaurant A market share: {market_share_a:.1%}")
        print(f"  - Restaurant B market share: {market_share_b:.1%}")
        
        # Revenue comparison
        if restaurant_b['revenue'] > 0:
            revenue_ratio = restaurant_a['revenue'] / restaurant_b['revenue']
            print(f"  - Revenue ratio (A/B): {revenue_ratio:.2f}")
            
            if revenue_ratio < 1.0:
                conf_loss = (1 - revenue_ratio) * 100
                print(f"  - Cost of Newest First: {conf_loss:.1f}% revenue loss")
            else:
                conf_gain = (revenue_ratio - 1) * 100
                print(f"  - Newest First advantage: {conf_gain:.1f}% revenue gain")
        
        print("="*60)
    
    def _save_competitive_conf_results(self, results: Dict):
        """Save competitive CoNF experiment results"""
        import json
        import os
        from datetime import datetime
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        conf_results = {
            "experiment_type": "competitive_cost_of_newest_first",
            "description": "Two restaurants competing with different review policies",
            "config": {
                "true_quality_a": Config.CONF_TRUE_QUALITY_A,
                "true_quality_b": Config.CONF_TRUE_QUALITY_B,
                "pricing_model": "dynamic_menu_items",
                "total_customers": Config.CONF_NUM_CUSTOMERS,
                "limited_attention": Config.CONF_LIMITED_ATTENTION,
                "skeptical_reviews": Config.CONF_SKEPTICAL_REVIEWS,
                "prior_alpha": Config.CONF_PRIOR_ALPHA,
                "prior_beta": Config.CONF_PRIOR_BETA,
                "theta_mean": Config.CONF_THETA_MEAN,
                "theta_std": Config.CONF_THETA_STD
            },
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
        # Save main results
        results_file = os.path.join(self.output_dir, "competitive_conf_experiment_results.json")
        with open(results_file, 'w') as f:
            json.dump(conf_results, f, indent=2)
        
        print(f"\nResults saved to: {results_file}")
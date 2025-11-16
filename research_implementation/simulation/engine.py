# engine.py
import json
import uuid
import random
from datetime import datetime, timedelta
from typing import List, Dict
from config import Config
from .models import Customer, Review, Restaurant
from .llm import LLMInterface
from .logger import SimulationLogger

class RestaurantSimulation:
    def _assess_skepticism(self, customer: Customer, reviews: List[Dict], restaurant_id: str, rating_comparison: Dict = None) -> Dict:
        """
        Dynamic skepticism assessment based on customer personality and review patterns.
        Returns skepticism level and specific concerns with detailed reasoning.
        """
        if not reviews:
            return {
                "level": "none", 
                "concerns": [], 
                "will_investigate": False, 
                "confidence_impact": 0,
                "detailed_reasons": ["No reviews available to assess"]
            }
        
        concerns = []
        detailed_reasons = []
        skepticism_score = 0
        
        # 1. Pattern Analysis
        five_star_count = sum(1 for r in reviews if r['stars'] == 5)
        four_star_count = sum(1 for r in reviews if r['stars'] == 4)
        low_star_count = sum(1 for r in reviews if r['stars'] <= 2)
        five_star_ratio = five_star_count / len(reviews)
        
        if five_star_ratio > 0.9:
            concerns.append("suspiciously_perfect_ratings")
            detailed_reasons.append(f"Extremely suspicious: {five_star_count}/{len(reviews)} reviews are 5-star ({five_star_ratio:.1%})")
            skepticism_score += 3
        elif five_star_ratio > 0.8:
            concerns.append("too_many_perfect_ratings")
            detailed_reasons.append(f"Too many perfect ratings: {five_star_count}/{len(reviews)} are 5-star ({five_star_ratio:.1%})")
            skepticism_score += 2
        elif five_star_ratio > 0.6:
            detailed_reasons.append(f"High 5-star ratio noted: {five_star_count}/{len(reviews)} ({five_star_ratio:.1%}) - within normal range")
            
        if low_star_count == 0 and len(reviews) >= 5:
            concerns.append("no_negative_reviews")
            detailed_reasons.append(f"No negative reviews among {len(reviews)} reviews - seems unlikely for real business")
            skepticism_score += 1
            
        # 2. Recency Analysis using simulation timeline
        current_sim_date = self.simulation_start_date + timedelta(days=self.current_simulation_day)
        six_months_ago = current_sim_date - timedelta(days=180)
        one_year_ago = current_sim_date - timedelta(days=365)
        
        try:
            review_dates = [datetime.strptime(r['date'], "%Y-%m-%d %H:%M:%S") for r in reviews]
            most_recent_date = max(review_dates)
            oldest_date = min(review_dates)
            
            days_since_recent = (current_sim_date - most_recent_date).days
            
            if most_recent_date < one_year_ago:
                concerns.append("very_outdated_reviews")
                detailed_reasons.append(f"Very outdated: Most recent review is {days_since_recent} days old (over 1 year)")
                skepticism_score += 3
            elif most_recent_date < six_months_ago:
                concerns.append("outdated_reviews")
                detailed_reasons.append(f"Outdated: Most recent review is {days_since_recent} days old (over 6 months)")
                skepticism_score += 1
            else:
                detailed_reasons.append(f"Recency acceptable: Most recent review is {days_since_recent} days old")
                
            # Check for review clustering
            date_range = (most_recent_date - oldest_date).days
            if len(reviews) >= 5 and date_range <= 7:
                concerns.append("suspicious_review_clustering")
                detailed_reasons.append(f"Suspicious: {len(reviews)} reviews all within {date_range} days")
                skepticism_score += 2
                
        except ValueError:
            concerns.append("date_parsing_issues")
            detailed_reasons.append("Cannot parse review dates - data quality concern")
            skepticism_score += 1
            
        # 3. Sample Size Analysis
        if len(reviews) < 3:
            concerns.append("too_few_reviews")
            detailed_reasons.append(f"Very few reviews: Only {len(reviews)} reviews available")
            skepticism_score += 1
        elif len(reviews) >= 20:
            detailed_reasons.append(f"Good sample size: {len(reviews)} reviews available")
            
        # 4. Rating Diversity Analysis
        unique_ratings = set(r['stars'] for r in reviews)
        rating_distribution = {i: sum(1 for r in reviews if r['stars'] == i) for i in range(1, 6)}
        
        if len(unique_ratings) == 1:
            concerns.append("no_rating_diversity")
            detailed_reasons.append(f"No diversity: All {len(reviews)} reviews have {list(unique_ratings)[0]} stars")
            skepticism_score += 2
        elif len(unique_ratings) <= 2:
            concerns.append("limited_rating_diversity")
            detailed_reasons.append(f"Limited diversity: Only {len(unique_ratings)} different ratings ({sorted(unique_ratings)})")
            skepticism_score += 1
        else:
            detailed_reasons.append(f"Good rating diversity: {len(unique_ratings)} different ratings")
            
        # 5. Personality-Based Skepticism Modifier
        personality = customer.role_desc.get("personality", "").lower() if hasattr(customer, 'role_desc') and customer.role_desc else ""
        skeptical_personalities = ["analytical", "meticulous", "discerning", "strict", "picky", "reserved", "thoughtful", "critical", "demanding", "perfectionist", "skeptical", "cautious", "exacting", "uncompromising", "fastidious", "particular", "discriminating", "selective"]
        trusting_personalities = ["easy-going", "easygoing", "relaxed", "carefree", "cheerful", "optimistic", "friendly", "outgoing", "open-minded", "balanced", "reasonable", "fair-minded"]
        
        personality_modifier = 0
        personality_reason = ""
        
        matching_skeptical = [trait for trait in skeptical_personalities if trait in personality]
        matching_trusting = [trait for trait in trusting_personalities if trait in personality]
        
        if matching_skeptical:
            personality_modifier = 2  # More skeptical
            personality_reason = f"Naturally skeptical personality ({', '.join(matching_skeptical)}) increases scrutiny"
        elif matching_trusting:
            personality_modifier = -1  # Less skeptical
            personality_reason = f"Trusting personality ({', '.join(matching_trusting)}) reduces skepticism"
        else:
            personality_reason = "Neutral personality - no skepticism modifier"
        
        # Criticality level modifier
        criticality_modifier = 0
        if hasattr(customer, 'role_desc') and customer.role_desc:
            criticality = customer.role_desc.get("criticality", "medium")
            if criticality == "easy":
                criticality_modifier = -2  # Less skeptical
                detailed_reasons.append(f"EASY CUSTOMER: -2 skepticism points for being easy-going")
            elif criticality == "critical":
                criticality_modifier = 3  # More skeptical
                detailed_reasons.append(f"CRITICAL CUSTOMER: +3 skepticism points for being highly critical")
            else:  # medium
                criticality_modifier = 0
                detailed_reasons.append(f"MEDIUM CUSTOMER: No criticality modifier")
            
        detailed_reasons.append(personality_reason)
        
        # 6. Rating Comparison Analysis (if provided)
        rating_comparison_modifier = 0
        if rating_comparison:
            detailed_reasons.append(f"\n--- RATING COMPARISON ANALYSIS ---")
            
            # Add customer's comparison thoughts
            for thought in rating_comparison["comparison_thoughts"]:
                detailed_reasons.append(f"Customer thought: {thought}")
            
            # Check for skepticism triggers from rating comparison
            if rating_comparison["skepticism_triggers"]:
                for trigger in rating_comparison["skepticism_triggers"]:
                    if trigger == "suspiciously_high_sample":
                        concerns.append("rating_discrepancy_high")
                        detailed_reasons.append("CONCERN: Sample reviews much higher than overall rating - possible cherry-picking")
                        rating_comparison_modifier += 2
                    elif trigger == "suspiciously_low_sample":
                        concerns.append("rating_discrepancy_low")
                        detailed_reasons.append("CONCERN: Sample reviews much lower than overall rating - inconsistent")
                        rating_comparison_modifier += 2
                    elif trigger == "cherry_picked_positive_reviews":
                        concerns.append("cherry_picked_positive")
                        detailed_reasons.append("CONCERN: Excellent sample vs mediocre overall - likely cherry-picked reviews")
                        rating_comparison_modifier += 3
                    elif trigger == "cherry_picked_negative_reviews":
                        concerns.append("cherry_picked_negative")
                        detailed_reasons.append("CONCERN: Poor sample vs good overall - suspicious negative selection")
                        rating_comparison_modifier += 3
                    elif trigger == "small_sample_with_discrepancy":
                        concerns.append("small_sample_discrepancy")
                        detailed_reasons.append("CONCERN: Small sample with rating discrepancy - need more data")
                        rating_comparison_modifier += 1
            
            # Moderate discrepancies
            abs_diff = rating_comparison.get("abs_difference", 0)
            if 0.5 <= abs_diff < 1.0 and not rating_comparison["skepticism_triggers"]:
                concerns.append("moderate_rating_discrepancy")
                detailed_reasons.append(f"Moderate discrepancy: {abs_diff:.1f} star difference between sample and overall")
                rating_comparison_modifier += 1
            
            detailed_reasons.append(f"Rating comparison modifier: +{rating_comparison_modifier}")
            
        final_score = max(0, skepticism_score + personality_modifier + criticality_modifier + rating_comparison_modifier)
        
        # Determine skepticism level and behavior
        if final_score >= 5:
            level = "high"
            will_investigate = random.random() < 0.8  # 80% chance to investigate
            confidence_impact = -0.3  # Significant negative impact on confidence
            decision_reason = f"HIGH skepticism (score: {final_score}) - 80% chance to investigate further"
        elif final_score >= 3:
            level = "medium" 
            will_investigate = random.random() < 0.6  # 60% chance to investigate
            confidence_impact = -0.15  # Moderate negative impact
            decision_reason = f"MEDIUM skepticism (score: {final_score}) - 60% chance to investigate further"
        elif final_score >= 1:
            level = "low"
            will_investigate = random.random() < 0.3  # 30% chance to investigate
            confidence_impact = -0.05  # Minor negative impact
            decision_reason = f"LOW skepticism (score: {final_score}) - 30% chance to investigate further"
        else:
            level = "none"
            will_investigate = False
            confidence_impact = 0
            decision_reason = f"NO skepticism (score: {final_score}) - accepting reviews at face value"
            
        detailed_reasons.append(decision_reason)
        detailed_reasons.append(f"Will investigate further: {'YES' if will_investigate else 'NO'}")
            
        return {
            "level": level,
            "concerns": concerns,
            "will_investigate": will_investigate,
            "confidence_impact": confidence_impact,
            "score": final_score,
            "personality_modifier": personality_modifier,
            "criticality_modifier": criticality_modifier,
            "rating_comparison_modifier": rating_comparison_modifier,
            "detailed_reasons": detailed_reasons,
            "rating_distribution": rating_distribution,
            "review_timeline": {
                "total_reviews": len(reviews),
                "days_since_most_recent": days_since_recent if 'days_since_recent' in locals() else None,
                "date_range_days": date_range if 'date_range' in locals() else None
            },
            "rating_comparison": rating_comparison
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
        from datetime import datetime, timedelta, timedelta
        
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
        
        # Simulation timeline - start date for consistent dating
        self.simulation_start_date = datetime(2024, 1, 1, 9, 0, 0)  # Jan 1, 2024, 9:00 AM
        self.current_simulation_day = 0
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
        from datetime import datetime, timedelta
        
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
                self.current_simulation_day = day - 1  # Update simulation day for dating
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
                            review_date = self.simulation_start_date + timedelta(days=day-1, hours=random.randint(0, 12))
                            new_review = restaurant_a.add_conf_review(
                                customer.customer_id, Config.CONF_TRUE_QUALITY_A, chosen_item, review_date
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
                            review_date = self.simulation_start_date + timedelta(days=day-1, hours=random.randint(0, 12))
                            new_review = restaurant_b.add_conf_review(
                                customer.customer_id, Config.CONF_TRUE_QUALITY_B, chosen_item, review_date
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
        
        # Get both configured rating and review-based rating
        configured_rating = Config.RESTAURANT_A_RATING if restaurant_id == "A" else Config.RESTAURANT_B_RATING
        review_based_rating = restaurant.get_overall_rating()
        restaurant_total_reviews = restaurant.get_review_count()
        
        # Convert configured rating (0-100) to star scale (0-5) for comparison
        configured_rating_stars = configured_rating / 20.0
        
        # Simple 50/50 weighting between configured rating and review-based rating
        restaurant_overall_rating = (0.5 * configured_rating_stars) + (0.5 * review_based_rating)
        
        # Calculate rating of reviews customer is reading
        reviews_read_rating = sum(r.stars for r in initial_reviews) / len(initial_reviews) if initial_reviews else 0
        
        # Log what the customer sees for debugging
        print(f"    Customer {customer.customer_id} evaluating Restaurant {restaurant_id}:")
        print(f"      Configured rating: {configured_rating}/100 ({configured_rating_stars:.1f}★)")
        print(f"      Review-based rating: {review_based_rating:.1f}★ (from {restaurant_total_reviews} reviews)")
        print(f"      Combined rating shown to customer: {restaurant_overall_rating:.1f}★")
        print(f"      Review policy: '{restaurant.review_policy}' - {self._get_policy_description(restaurant.review_policy)}")
        print(f"      Reviews customer will read: {len(initial_reviews)} reviews, avg {reviews_read_rating:.1f}★")
        
        # Explicit rating comparison
        rating_comparison = self._compare_ratings(
            reviews_read_rating, restaurant_overall_rating, 
            len(initial_reviews), restaurant_total_reviews,
            customer, restaurant_id
        )
        
        # Assess skepticism with detailed logging (including rating comparison)
        reviews_dict = [r.__dict__ for r in initial_reviews]
        skepticism_result = self._assess_skepticism(customer, reviews_dict, restaurant_id, rating_comparison)
        is_skeptical = skepticism_result["will_investigate"]
        
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
        
        # Record decision with detailed review and skepticism logging
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
            "restaurant_policy": restaurant.review_policy,
            "policy_description": self._get_policy_description(restaurant.review_policy),
            "rating_comparison": rating_comparison,
            "skepticism_details": {
                "level": skepticism_result["level"],
                "score": skepticism_result["score"],
                "concerns": skepticism_result["concerns"],
                "detailed_reasons": skepticism_result["detailed_reasons"],
                "rating_distribution": skepticism_result["rating_distribution"],
                "review_timeline": skepticism_result["review_timeline"],
                "confidence_impact": skepticism_result["confidence_impact"],
                "rating_comparison_modifier": skepticism_result["rating_comparison_modifier"],
                "criticality_modifier": skepticism_result["criticality_modifier"]
            },
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
    
    def _compare_ratings(self, reviews_read_rating: float, restaurant_overall_rating: float, 
                        reviews_read_count: int, total_reviews_count: int,
                        customer: Customer, restaurant_id: str) -> Dict:
        """
        Explicit comparison between ratings of reviews customer is reading vs restaurant's overall rating.
        Returns detailed analysis of any discrepancies that might trigger skepticism.
        """
        rating_difference = reviews_read_rating - restaurant_overall_rating
        abs_difference = abs(rating_difference)
        
        comparison_result = {
            "reviews_read_rating": reviews_read_rating,
            "restaurant_overall_rating": restaurant_overall_rating,
            "rating_difference": rating_difference,
            "abs_difference": abs_difference,
            "reviews_read_count": reviews_read_count,
            "total_reviews_count": total_reviews_count,
            "sample_percentage": (reviews_read_count / total_reviews_count * 100) if total_reviews_count > 0 else 0,
            "discrepancy_concerns": [],
            "comparison_thoughts": [],
            "skepticism_triggers": []
        }
        
        # Customer's internal comparison thoughts
        if abs_difference < 0.2:
            comparison_result["comparison_thoughts"].append(
                f"Reviews I'm reading ({reviews_read_rating:.1f}★) match the overall rating ({restaurant_overall_rating:.1f}★) - consistent"
            )
        elif abs_difference < 0.5:
            comparison_result["comparison_thoughts"].append(
                f"Reviews I'm reading ({reviews_read_rating:.1f}★) are slightly different from overall rating ({restaurant_overall_rating:.1f}★) - minor variation"
            )
        else:
            comparison_result["comparison_thoughts"].append(
                f"Reviews I'm reading ({reviews_read_rating:.1f}★) differ significantly from overall rating ({restaurant_overall_rating:.1f}★) - notable discrepancy"
            )
        
        # Analyze specific discrepancy patterns
        if abs_difference >= 0.5:
            if rating_difference > 0:
                # Reviews read are higher than overall
                comparison_result["discrepancy_concerns"].append("reviews_read_higher_than_overall")
                comparison_result["comparison_thoughts"].append(
                    f"The {reviews_read_count} reviews I'm seeing are {rating_difference:.1f} stars higher than the restaurant's {restaurant_overall_rating:.1f}★ average"
                )
                if rating_difference >= 1.0:
                    comparison_result["skepticism_triggers"].append("suspiciously_high_sample")
                    comparison_result["comparison_thoughts"].append(
                        "This seems suspicious - why would the few reviews I'm seeing be so much better than average?"
                    )
            else:
                # Reviews read are lower than overall
                comparison_result["discrepancy_concerns"].append("reviews_read_lower_than_overall")
                comparison_result["comparison_thoughts"].append(
                    f"The {reviews_read_count} reviews I'm seeing are {abs(rating_difference):.1f} stars lower than the restaurant's {restaurant_overall_rating:.1f}★ average"
                )
                if abs(rating_difference) >= 1.0:
                    comparison_result["skepticism_triggers"].append("suspiciously_low_sample")
                    comparison_result["comparison_thoughts"].append(
                        "This is concerning - either I'm seeing the worst reviews, or something's not right with the overall rating"
                    )
        
        # Sample size analysis
        sample_percentage = comparison_result["sample_percentage"]
        if sample_percentage < 10 and total_reviews_count > 20:
            comparison_result["comparison_thoughts"].append(
                f"I'm only seeing {reviews_read_count} out of {total_reviews_count} reviews ({sample_percentage:.1f}%) - small sample"
            )
            if abs_difference >= 0.3:
                comparison_result["skepticism_triggers"].append("small_sample_with_discrepancy")
                comparison_result["comparison_thoughts"].append(
                    "With such a small sample showing different ratings, I should probably read more reviews"
                )
        
        # Extreme rating scenarios
        if reviews_read_rating >= 4.5 and restaurant_overall_rating <= 3.5:
            comparison_result["skepticism_triggers"].append("cherry_picked_positive_reviews")
            comparison_result["comparison_thoughts"].append(
                "I'm seeing mostly excellent reviews but the overall rating is mediocre - feels like cherry-picking"
            )
        elif reviews_read_rating <= 2.5 and restaurant_overall_rating >= 4.0:
            comparison_result["skepticism_triggers"].append("cherry_picked_negative_reviews")
            comparison_result["comparison_thoughts"].append(
                "I'm seeing mostly poor reviews but the overall rating is good - this doesn't add up"
            )
        
        # Customer personality affects interpretation
        if hasattr(customer, 'role_desc') and customer.role_desc:
            personality = customer.role_desc.get("personality", "").lower()
            if "analytical" in personality or "meticulous" in personality:
                comparison_result["comparison_thoughts"].append(
                    "As someone who pays attention to details, this rating discrepancy stands out to me"
                )
            elif "trusting" in personality or "optimistic" in personality:
                comparison_result["comparison_thoughts"].append(
                    "I tend to give businesses the benefit of the doubt, but this rating difference is hard to ignore"
                )
        
        return comparison_result
    
    def _get_policy_description(self, policy: str) -> str:
        """Get human-readable description of review policy"""
        policy_descriptions = {
            "highest_rating": "Shows highest-rated reviews first (best reviews at top)",
            "newest_first": "Shows newest reviews first (most recent at top)", 
            "latest": "Shows latest reviews first (most recent at top)",
            "random": "Shows reviews in random order (no specific sorting)",
            "recent_quality_boost": "Prioritizes recent high-quality reviews"
        }
        return policy_descriptions.get(policy, f"Unknown policy: {policy}")
    
    def _initialize_conf_reviews(self, restaurant: Restaurant):
        """Initialize restaurant with actual initial reviews from input file"""
        # Load initial reviews from input file
        try:
            if restaurant.restaurant_id == "A":
                filename = "data/inputs/initial_reviews_a.json"
            else:
                filename = "data/inputs/initial_reviews_b.json"
                
            with open(filename) as f:
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
                
            print(f"Loaded {len(restaurant.initial_reviews)} initial reviews from {filename}")
            
            # Show what reviews customers will actually see with current policy
            sorted_reviews = restaurant.get_sorted_reviews(Config.CONF_LIMITED_ATTENTION)
            avg_visible = sum(r.stars for r in sorted_reviews) / len(sorted_reviews) if sorted_reviews else 0
            print(f"Restaurant {restaurant.restaurant_id} policy '{restaurant.review_policy}': customers see {avg_visible:.1f} avg stars from initial reviews")
            
            # Show the actual reviews customers will see
            print(f"  First {Config.CONF_LIMITED_ATTENTION} reviews customers see:")
            for i, review in enumerate(sorted_reviews[:Config.CONF_LIMITED_ATTENTION]):
                print(f"    {i+1}. {review.stars}★ - {review.text[:50]}...")
            
        except FileNotFoundError:
            print(f"Warning: {filename} not found, generating fallback reviews")
            # Fallback to generated reviews
            true_quality = Config.CONF_TRUE_QUALITY_A if restaurant.restaurant_id == "A" else Config.CONF_TRUE_QUALITY_B
            for i in range(20):
                customer_id = f"init_{restaurant.restaurant_id}_{i}"
                # Initial reviews get dates before simulation start
                initial_date = self.simulation_start_date - timedelta(days=random.randint(30, 365))
                restaurant.add_conf_review(customer_id, true_quality, None, initial_date)
    
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
            
            # Assess skepticism with detailed logging
            reviews_dict = [r.__dict__ for r in initial_reviews]
            skepticism_result = self._assess_skepticism(customer, reviews_dict, restaurant_id)
            is_skeptical = skepticism_result["will_investigate"]
            
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
            
            # Record decision with detailed review and skepticism logging
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
                "skepticism_details": {
                    "level": skepticism_result["level"],
                    "score": skepticism_result["score"],
                    "concerns": skepticism_result["concerns"],
                    "detailed_reasons": skepticism_result["detailed_reasons"],
                    "rating_distribution": skepticism_result["rating_distribution"],
                    "review_timeline": skepticism_result["review_timeline"],
                    "confidence_impact": skepticism_result["confidence_impact"],
                    "rating_comparison_modifier": skepticism_result.get("rating_comparison_modifier", 0),
                    "criticality_modifier": skepticism_result["criticality_modifier"]
                },
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
                review_date = self.simulation_start_date + timedelta(days=i//10, hours=random.randint(0, 12))  # Spread reviews across simulation
                new_review = restaurant.add_conf_review(customer.customer_id, Config.CONF_TRUE_QUALITY_A, chosen_item, review_date)
                
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
        """Generate customer for CoNF experiment with simple criticality levels"""
        import numpy as np
        
        # Base theta calculation
        theta = np.random.normal(Config.CONF_THETA_MEAN, Config.CONF_THETA_STD)
        
        # Set personality and behavior based on criticality level
        criticality = Config.CUSTOMER_CRITICALITY.lower()
        
        if criticality == "easy":
            personalities = [
                "easy-going", "friendly", "optimistic", "relaxed", "cheerful",
                "trusting", "open-minded", "laid-back", "accommodating"
            ]
            customer_type = "easy_customer"
        elif criticality == "critical":
            personalities = [
                "analytical", "meticulous", "discerning", "picky", "strict",
                "demanding", "perfectionist", "skeptical", "critical", "exacting"
            ]
            customer_type = "critical_customer"
        else:  # medium
            personalities = [
                "balanced", "reasonable", "fair-minded", "thoughtful", "careful",
                "moderate", "sensible", "practical", "discerning"
            ]
            customer_type = "medium_customer"
        
        personality = random.choice(personalities)
        
        return Customer(
            customer_id=customer_id,
            name=f"{criticality.title()}_Customer_{customer_id}",
            role_desc={
                "type": customer_type,
                "personality": personality,
                "criticality": criticality
            },
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
        print(f"  - Restaurant A ({self.restaurant_a.review_policy}): {market_share_a:.1%} market share")
        print(f"  - Restaurant B ({self.restaurant_b.review_policy}): {market_share_b:.1%} market share")
        
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
        from datetime import datetime, timedelta
        
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
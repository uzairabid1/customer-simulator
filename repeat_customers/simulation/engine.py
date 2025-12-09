# engine.py - Repeat Customer Simulation Engine
import json
import os
import random
import sys
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from .models import Customer, Restaurant, Review, CustomerExperience
from .llm import LLMInterface
from .logger import SimulationLogger
from config import Config


class RepeatCustomerSimulation:
    def __init__(self, output_folder=None):
        self.output_folder = output_folder or f"repeat_simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.output_path = os.path.join("data", "outputs", self.output_folder)
        os.makedirs(self.output_path, exist_ok=True)
        
        # Set up console logging to file
        self.console_log_file = os.path.join(self.output_path, "simulation_console_log.txt")
        self.original_stdout = sys.stdout
        
        # Initialize components
        self.restaurant_a = Restaurant("A")
        self.restaurant_b = Restaurant("B")
        self.llm = LLMInterface()
        self.logger = SimulationLogger(os.path.join(self.output_path, "logs"))
        self.logger.restaurant_a = self.restaurant_a
        self.logger.restaurant_b = self.restaurant_b
        
        # Simulation state
        self.simulation_start_date = datetime(2024, 1, 1, 9, 0, 0)
        self.current_simulation_day = 0
        
        # Repeat customer tracking
        self.customers: List[Customer] = []  # The same 50 customers throughout simulation
        self.daily_results: List[Dict] = []
        
        print(f"Repeat Customer Simulation initialized")
        print(f"Output folder: {self.output_path}")
    
    def run_simulation(self):
        """Main simulation entry point"""
        if Config.ENABLE_REPEAT_CUSTOMERS:
            self.run_repeat_customer_simulation()
        else:
            print("Repeat customer simulation is disabled in config")
    
    def run_repeat_customer_simulation(self):
        """Run the repeat customer simulation"""
        print("=== REPEAT CUSTOMER SIMULATION ===")
        print(f"Running {Config.SIMULATION_DAYS} days with {Config.NUM_REPEAT_CUSTOMERS} repeat customers")
        print()
        
        # Redirect console output to file
        with open(self.console_log_file, 'w', encoding='utf-8') as log_file:
            class TeeOutput:
                def __init__(self, *files):
                    self.files = files
                def write(self, text):
                    for f in self.files:
                        f.write(text)
                        f.flush()
                def flush(self):
                    for f in self.files:
                        f.flush()
            
            sys.stdout = TeeOutput(self.original_stdout, log_file)
            
            try:
                # Initialize restaurants with initial reviews
                self._initialize_restaurants()
                
                # Generate the same 50 customers who will visit daily
                self._generate_repeat_customers()
                
                # Run simulation for each day
                for day in range(1, Config.SIMULATION_DAYS + 1):
                    print(f"\n=== DAY {day} ===")
                    self.current_simulation_day = day
                    
                    day_results = self._simulate_day(day)
                    self.daily_results.append(day_results)
                    
                    # Log daily statistics
                    self.logger.log_repeat_customer_stats(day)
                    
                    print(f"Day {day} complete: {day_results['total_customers']} customers, "
                          f"A: {day_results['restaurant_a_customers']} customers (${day_results['restaurant_a_revenue']:.2f}), "
                          f"B: {day_results['restaurant_b_customers']} customers (${day_results['restaurant_b_revenue']:.2f})")
                    
                    # Show daily memory summary
                    self._print_daily_memory_summary(day)
                
                # Calculate and save final results
                self._calculate_and_save_results()
                
            finally:
                sys.stdout = self.original_stdout
        
        print(f"\nRepeat Customer Simulation complete! Results saved to {self.output_path}")
        print(f"Console log saved to: {self.console_log_file}")
    
    def _initialize_restaurants(self):
        """Initialize both restaurants with initial reviews"""
        print("Initializing restaurants with initial reviews...")
        
        for restaurant in [self.restaurant_a, self.restaurant_b]:
            self._load_initial_reviews(restaurant)
        
        print(f"Restaurant A: {len(self.restaurant_a.initial_reviews)} initial reviews, avg {self.restaurant_a.get_overall_rating():.1f} stars")
        print(f"Restaurant B: {len(self.restaurant_b.initial_reviews)} initial reviews, avg {self.restaurant_b.get_overall_rating():.1f} stars")
    
    def _load_initial_reviews(self, restaurant: Restaurant):
        """Load initial reviews from input files"""
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
                
        except FileNotFoundError:
            print(f"Warning: {filename} not found, generating fallback reviews")
            # Fallback to generated reviews if file not found
            true_quality = Config.TRUE_QUALITY_A if restaurant.restaurant_id == "A" else Config.TRUE_QUALITY_B
            for i in range(20):
                customer_id = f"init_{restaurant.restaurant_id}_{i}"
                initial_date = self.simulation_start_date - timedelta(days=random.randint(30, 365))
                # Generate experience quality based on true quality with variation
                concentration = 5.0
                alpha_param = true_quality * concentration
                beta_param = (1.0 - true_quality) * concentration
                experience_quality = np.random.beta(max(alpha_param, 0.1), max(beta_param, 0.1))
                experience_quality = max(0.0, min(1.0, experience_quality))
                restaurant.add_conf_review(customer_id, experience_quality, true_quality, None, initial_date)
    
    def _generate_repeat_customers(self):
        """Generate the same 50 customers who will visit throughout the simulation"""
        print(f"Generating {Config.NUM_REPEAT_CUSTOMERS} repeat customers...")
        
        for i in range(Config.NUM_REPEAT_CUSTOMERS):
            customer_profile = self.llm.generate_customer()
            customer_id = f"repeat_customer_{i+1:02d}"
            
            # Add criticality based on config
            criticality = Config.CUSTOMER_CRITICALITY
            customer_profile["criticality"] = criticality
            
            customer = Customer(
                customer_id=customer_id,
                name=customer_profile["name"],
                role_desc=customer_profile,
                theta=random.normalvariate(Config.THETA_MEAN, Config.THETA_STD),
                alpha=Config.PRIOR_ALPHA,
                beta=Config.PRIOR_BETA
            )
            
            self.customers.append(customer)
        
        print(f"Generated {len(self.customers)} repeat customers")
    
    def _simulate_day(self, day: int) -> Dict:
        """Simulate one day where all customers make decisions"""
        day_revenue_a = 0
        day_revenue_b = 0
        day_customers_a = 0
        day_customers_b = 0
        
        # Shuffle customers for random order each day
        daily_customers = self.customers.copy()
        random.shuffle(daily_customers)
        
        for customer in daily_customers:
            print(f"\n--- Customer {customer.customer_id} ({customer.name}) - Day {day} ---")
            
            # Show customer's memory state if they have experiences
            if customer.experiences:
                pref_a = customer.get_restaurant_preference("A")
                pref_b = customer.get_restaurant_preference("B")
                visits_a = customer.get_experience_count("A")
                visits_b = customer.get_experience_count("B")
                
                print(f"  Memory: {len(customer.experiences)} total experiences")
                print(f"  Restaurant A: {visits_a} visits, preference {pref_a:+.2f}")
                print(f"  Restaurant B: {visits_b} visits, preference {pref_b:+.2f}")
                
                if pref_a > pref_b:
                    print(f"  → Prefers Restaurant A (difference: {pref_a - pref_b:+.2f})")
                elif pref_b > pref_a:
                    print(f"  → Prefers Restaurant B (difference: {pref_b - pref_a:+.2f})")
                else:
                    print(f"  → Neutral preference")
            else:
                print(f"  Memory: No past experiences (first-time decision)")
            
            # Log customer arrival and past experiences
            customer_profile = customer.role_desc.copy()
            customer_profile["customer_id"] = customer.customer_id
            self.logger.log_customer_arrival(customer_profile, day)
            if customer.experiences:
                self.logger.log_customer_experience_summary(
                    customer.customer_id, customer.name, day, customer.experiences
                )
                # Log customer's current memory state and preferences
                self.logger.log_customer_memory_state(
                    customer.customer_id, customer.name, day, customer
                )
            
            # Customer evaluates both restaurants and makes choice
            chosen_restaurant, decision_reason = self._customer_makes_choice(customer, day)
            
            if chosen_restaurant:
                # Customer orders and has experience
                revenue, experience = self._customer_visits_restaurant(customer, chosen_restaurant, day)
                
                if chosen_restaurant.restaurant_id == "A":
                    day_revenue_a += revenue
                    day_customers_a += 1
                else:
                    day_revenue_b += revenue
                    day_customers_b += 1
                
                # Add experience to customer's memory
                customer.add_experience(experience)
                
                # Log the experience
                self.logger.log_customer_experience(customer.customer_id, customer.name, day, experience)
                
                # Customer leaves a review
                self._customer_leaves_review(customer, chosen_restaurant, experience, day)
            else:
                print(f"  {customer.name} decided not to visit any restaurant today")
        
        return {
            "day": day,
            "total_customers": len(daily_customers),
            "restaurant_a_customers": day_customers_a,
            "restaurant_b_customers": day_customers_b,
            "restaurant_a_revenue": day_revenue_a,
            "restaurant_b_revenue": day_revenue_b
        }
    
    def _customer_makes_choice(self, customer: Customer, day: int) -> Tuple[Restaurant, str]:
        """Customer evaluates both restaurants and chooses one (or neither)"""
        
        # Get reviews for both restaurants
        a_reviews = self._get_reviews_for_customer(self.restaurant_a, customer)
        b_reviews = self._get_reviews_for_customer(self.restaurant_b, customer)
        
        # Convert reviews to dict format for LLM
        a_reviews_dict = [self._review_to_dict(r) for r in a_reviews]
        b_reviews_dict = [self._review_to_dict(r) for r in b_reviews]
        
        # Calculate skepticism for both restaurants based on customer criticality
        a_skepticism = self._calculate_skepticism(customer, a_reviews_dict, self.restaurant_a, "A")
        b_skepticism = self._calculate_skepticism(customer, b_reviews_dict, self.restaurant_b, "B")
        
        # Log skepticism assessments
        self.logger.log_skepticism_assessment(customer.customer_id, customer.name, day, "A", a_skepticism)
        self.logger.log_skepticism_assessment(customer.customer_id, customer.name, day, "B", b_skepticism)
        
        # If skeptical, get additional reviews
        a_post_investigation = None
        b_post_investigation = None
        
        if a_skepticism["will_investigate"]:
            additional_a_reviews = self.restaurant_a.get_sorted_reviews(limit=Config.SKEPTICAL_REVIEWS)
            a_reviews_dict.extend([self._review_to_dict(r) for r in additional_a_reviews])
            a_post_investigation = self._post_investigation_assessment(a_skepticism, additional_a_reviews)
            self.logger.log_reviews_seen(customer.customer_id, customer.name, day, "A", 
                                        [self._review_to_dict(r) for r in additional_a_reviews], is_additional=True)
        
        if b_skepticism["will_investigate"]:
            additional_b_reviews = self.restaurant_b.get_sorted_reviews(limit=Config.SKEPTICAL_REVIEWS)
            b_reviews_dict.extend([self._review_to_dict(r) for r in additional_b_reviews])
            b_post_investigation = self._post_investigation_assessment(b_skepticism, additional_b_reviews)
            self.logger.log_reviews_seen(customer.customer_id, customer.name, day, "B", 
                                        [self._review_to_dict(r) for r in additional_b_reviews], is_additional=True)
        
        # Get restaurant ratings
        a_rating = self.restaurant_a.get_overall_rating()
        b_rating = self.restaurant_b.get_overall_rating()
        a_count = self.restaurant_a.get_review_count()
        b_count = self.restaurant_b.get_review_count()
        
        # Use LLM to make decision considering past experiences and skepticism
        decision_result = self.llm.make_repeat_customer_decision(
            customer=customer.role_desc,
            customer_experiences=customer.experiences,
            a_reviews=a_reviews_dict,
            b_reviews=b_reviews_dict,
            a_menu=self.restaurant_a.menu,
            b_menu=self.restaurant_b.menu,
            a_rating=a_rating,
            a_count=a_count,
            b_rating=b_rating,
            b_count=b_count,
            restaurant_a=self.restaurant_a,
            restaurant_b=self.restaurant_b,
            a_skepticism=a_skepticism,
            b_skepticism=b_skepticism,
            a_post_investigation=a_post_investigation,
            b_post_investigation=b_post_investigation,
            day=day
        )
        
        decision = decision_result.get("decision", "B")
        reason = decision_result.get("reason", "No specific reason provided")
        
        # Log decision
        self.logger.log_decision(customer.customer_id, customer.name, decision, reason, day)
        self.logger.log_decision_details(
            customer.customer_id, customer.name,
            a_reviews_dict, b_reviews_dict,
            decision, reason, day
        )
        
        print(f"  Decision: Restaurant {decision}")
        print(f"  Reason: {reason}")
        
        # Return chosen restaurant
        if decision == "A":
            return self.restaurant_a, reason
        elif decision == "B":
            return self.restaurant_b, reason
        else:
            return None, reason
    
    def _get_reviews_for_customer(self, restaurant: Restaurant, customer: Customer) -> List[Review]:
        """Get reviews that customer will see based on restaurant's policy"""
        return restaurant.get_sorted_reviews(limit=Config.LIMITED_ATTENTION)
    
    def _review_to_dict(self, review: Review) -> Dict:
        """Convert Review object to dictionary for LLM"""
        return {
            "review_id": review.review_id,
            "user_id": review.user_id,
            "business_id": review.business_id,
            "stars": review.stars,
            "text": review.text,
            "date": review.date,
            "ordered_item": review.ordered_item
        }
    
    def _customer_visits_restaurant(self, customer: Customer, restaurant: Restaurant, day: int) -> Tuple[float, CustomerExperience]:
        """Customer visits restaurant, orders, and has an experience"""
        
        # Get past orders at this restaurant for context
        past_orders = [exp.ordered_item for exp in customer.experiences if exp.restaurant_id == restaurant.restaurant_id]
        
        # Customer chooses menu item
        menu_choice = self.llm.choose_menu_item(
            customer=customer.role_desc,
            restaurant_id=restaurant.restaurant_id,
            menu=restaurant.menu,
            past_orders=past_orders
        )
        
        chosen_item = menu_choice.get("chosen_item", list(restaurant.menu.keys())[0])
        menu_reason = menu_choice.get("reason", "No reason provided")
        item_price = restaurant.menu.get(chosen_item, 20)  # Default price if item not found
        
        print(f"  Ordered: {chosen_item} (${item_price}) - {menu_reason}")
        
        # Log the order
        self.logger.log_order(customer.customer_id, customer.name, restaurant.restaurant_id, 
                             chosen_item, item_price, day, menu_reason)
        
        # Generate experience based on true quality with variation
        true_quality = Config.TRUE_QUALITY_A if restaurant.restaurant_id == "A" else Config.TRUE_QUALITY_B
        
        # Generate experience quality as a continuous value (0.0 to 1.0)
        # Use true_quality as the mean, but add variation
        # Use a beta distribution to create natural variation around the true quality
        # Beta distribution parameters: higher concentration around true_quality
        # Scale alpha and beta to create appropriate variance
        concentration = 5.0  # Controls variance (higher = less variance)
        alpha_param = true_quality * concentration
        beta_param = (1.0 - true_quality) * concentration
        experience_quality = np.random.beta(max(alpha_param, 0.1), max(beta_param, 0.1))
        experience_quality = max(0.0, min(1.0, experience_quality))  # Clamp to [0, 1]
        
        # Map experience quality to star rating
        if experience_quality <= 0.1:
            stars_given = 1.0
            was_satisfied = False
        elif experience_quality <= 0.3:
            stars_given = 2.0
            was_satisfied = False
        elif experience_quality <= 0.5:
            stars_given = 3.0
            was_satisfied = False
        elif experience_quality <= 0.8:
            stars_given = 4.0
            was_satisfied = True
        else:
            stars_given = 5.0
            was_satisfied = True
        
        # Create experience (store experience_quality for review generation)
        current_date = self.simulation_start_date + timedelta(days=day-1, hours=random.randint(9, 21))
        experience = CustomerExperience(
            restaurant_id=restaurant.restaurant_id,
            date=current_date.strftime("%Y-%m-%d %H:%M:%S"),
            ordered_item=chosen_item,
            stars_given=stars_given,
            price_paid=item_price,
            was_satisfied=was_satisfied,
            review_text="",  # Will be filled when review is generated
            experience_quality=experience_quality
        )
        
        # Update restaurant revenue and tracking
        restaurant.revenue += item_price
        restaurant.add_daily_customer(day, customer.customer_id)
        
        print(f"  Experience: {stars_given} stars ({'Satisfied' if was_satisfied else 'Disappointed'})")
        
        return item_price, experience
    
    def _customer_leaves_review(self, customer: Customer, restaurant: Restaurant, experience: CustomerExperience, day: int):
        """Customer leaves a review based on their experience"""
        
        # Determine if customer will leave a review (not everyone leaves reviews)
        will_leave_review = random.random() < 0.7  # 70% chance to leave review
        
        if will_leave_review:
            # Generate review date (same day or next day)
            review_date = self.simulation_start_date + timedelta(days=day-1, hours=random.randint(12, 23))
            
            # Add review to restaurant
            # Get experience quality from the experience object
            experience_quality = experience.experience_quality
            
            review = restaurant.add_conf_review(
                customer_id=customer.customer_id,
                experience_quality=experience_quality,
                true_quality=Config.TRUE_QUALITY_A if restaurant.restaurant_id == "A" else Config.TRUE_QUALITY_B,
                ordered_item=experience.ordered_item,
                simulation_date=review_date
            )
            
            # Update experience with review text
            experience.review_text = review.text
            
            # Log the review
            self.logger.log_review(self._review_to_dict(review), "Customer experience review", day)
            
            print(f"  Left review: {review.stars} stars - {review.text[:50]}...")
        else:
            print(f"  Did not leave a review")
    
    def _calculate_and_save_results(self):
        """Calculate final results and save to files"""
        print("\n=== FINAL RESULTS ===")
        
        # Calculate totals
        total_revenue_a = sum(day["restaurant_a_revenue"] for day in self.daily_results)
        total_revenue_b = sum(day["restaurant_b_revenue"] for day in self.daily_results)
        total_customers_a = sum(day["restaurant_a_customers"] for day in self.daily_results)
        total_customers_b = sum(day["restaurant_b_customers"] for day in self.daily_results)
        
        # Get repeat customer statistics
        a_stats = self.restaurant_a.get_repeat_customer_stats()
        b_stats = self.restaurant_b.get_repeat_customer_stats()
        
        # Calculate customer loyalty metrics
        loyalty_metrics = self._calculate_loyalty_metrics()
        
        results = {
            "simulation_config": {
                "num_repeat_customers": Config.NUM_REPEAT_CUSTOMERS,
                "simulation_days": Config.SIMULATION_DAYS,
                "customer_criticality": Config.CUSTOMER_CRITICALITY,
                "true_quality_a": Config.TRUE_QUALITY_A,
                "true_quality_b": Config.TRUE_QUALITY_B,
                "restaurant_a_policy": Config.RESTAURANT_A_REVIEW_POLICY,
                "restaurant_b_policy": Config.RESTAURANT_B_REVIEW_POLICY
            },
            "overall_results": {
                "total_revenue_a": total_revenue_a,
                "total_revenue_b": total_revenue_b,
                "total_customers_a": total_customers_a,
                "total_customers_b": total_customers_b,
                "market_share_a": total_customers_a / (total_customers_a + total_customers_b) if (total_customers_a + total_customers_b) > 0 else 0,
                "market_share_b": total_customers_b / (total_customers_a + total_customers_b) if (total_customers_a + total_customers_b) > 0 else 0,
                "revenue_per_customer_a": total_revenue_a / total_customers_a if total_customers_a > 0 else 0,
                "revenue_per_customer_b": total_revenue_b / total_customers_b if total_customers_b > 0 else 0
            },
            "repeat_customer_stats": {
                "restaurant_a": a_stats,
                "restaurant_b": b_stats
            },
            "loyalty_metrics": loyalty_metrics,
            "daily_breakdown": self.daily_results,
            "final_restaurant_ratings": {
                "restaurant_a": self.restaurant_a.get_overall_rating(),
                "restaurant_b": self.restaurant_b.get_overall_rating()
            }
        }
        
        # Save results
        results_file = os.path.join(self.output_path, "repeat_customer_results.json")
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Save logs
        self.logger.save_logs()
        
        # Print summary
        print(f"Restaurant A ({Config.RESTAURANT_A_REVIEW_POLICY}): {total_customers_a} visits, ${total_revenue_a:.2f} revenue")
        print(f"Restaurant B ({Config.RESTAURANT_B_REVIEW_POLICY}): {total_customers_b} visits, ${total_revenue_b:.2f} revenue")
        print(f"Market Share: A={results['overall_results']['market_share_a']:.1%}, B={results['overall_results']['market_share_b']:.1%}")
        print(f"Customer Loyalty: A={loyalty_metrics['restaurant_a_loyalty']:.1%}, B={loyalty_metrics['restaurant_b_loyalty']:.1%}")
        print(f"Results saved to: {results_file}")
    
    def _print_daily_memory_summary(self, day: int):
        """Print a summary of customer memory states for the day"""
        customers_with_experiences = [c for c in self.customers if c.experiences]
        if not customers_with_experiences:
            print(f"  Memory Summary: No customers have experiences yet")
            return
        
        # Calculate preference distribution
        prefer_a = 0
        prefer_b = 0
        neutral = 0
        
        for customer in customers_with_experiences:
            pref_a = customer.get_restaurant_preference("A")
            pref_b = customer.get_restaurant_preference("B")
            
            if pref_a > pref_b:
                prefer_a += 1
            elif pref_b > pref_a:
                prefer_b += 1
            else:
                neutral += 1
        
        total_with_exp = len(customers_with_experiences)
        print(f"  Memory Summary: {total_with_exp}/{len(self.customers)} customers have experiences")
        print(f"    Prefer A: {prefer_a} ({prefer_a/total_with_exp*100:.1f}%)")
        print(f"    Prefer B: {prefer_b} ({prefer_b/total_with_exp*100:.1f}%)")
        print(f"    Neutral: {neutral} ({neutral/total_with_exp*100:.1f}%)")
    
    def _calculate_skepticism(self, customer: Customer, reviews: List[Dict], restaurant: Restaurant, restaurant_id: str) -> Dict:
        """
        Calculate customer skepticism based on review patterns and customer criticality.
        Returns a skepticism dictionary with level, concerns, and investigation decision.
        """
        if not reviews:
            return {
                "level": "none",
                "score": 0.0,
                "concerns": [],
                "will_investigate": False,
                "confidence_impact": 0.0,
                "personality_modifier": 1.0
            }
        
        # Get customer criticality from config
        criticality = customer.role_desc.get("criticality", Config.CUSTOMER_CRITICALITY).lower()
        
        # Base skepticism thresholds based on criticality
        if criticality == "easy":
            base_threshold = 0.7  # Easy customers are less skeptical
            personality_modifier = 0.5
        elif criticality == "critical":
            base_threshold = 0.3  # Critical customers are more skeptical
            personality_modifier = 1.5
        else:  # medium
            base_threshold = 0.5
            personality_modifier = 1.0
        
        concerns = []
        skepticism_score = 0.0
        
        # Check for suspicious patterns
        stars = [r["stars"] for r in reviews]
        avg_rating = sum(stars) / len(stars) if stars else 0
        
        # 1. Suspiciously uniform distribution (all same rating or very little variation)
        if len(set(stars)) <= 1 and len(reviews) >= 3:
            concerns.append("suspiciously_uniform_distribution")
            skepticism_score += 0.3
        
        # 2. Low variance with extreme mean (all high or all low)
        variance = sum((s - avg_rating) ** 2 for s in stars) / len(stars) if stars else 0
        if variance < 0.5 and (avg_rating >= 4.5 or avg_rating <= 1.5):
            concerns.append("low_variance_extreme_mean")
            skepticism_score += 0.25
        
        # 3. Rating vs overall restaurant rating mismatch
        overall_rating = restaurant.get_overall_rating()
        if abs(avg_rating - overall_rating) > 1.5:
            concerns.append("rating_comparison")
            skepticism_score += 0.2
        
        # 4. Check for text-rating mismatch (simplified - just check if there's variation)
        # In a real implementation, you'd use sentiment analysis
        positive_words = ["great", "excellent", "amazing", "love", "perfect", "wonderful", "delicious", "fantastic"]
        negative_words = ["terrible", "awful", "disappointed", "bad", "poor", "horrible", "worst"]
        
        for review in reviews:
            text_lower = review.get("text", "").lower()
            stars = review.get("stars", 0)
            
            has_positive_words = any(word in text_lower for word in positive_words)
            has_negative_words = any(word in text_lower for word in negative_words)
            
            if stars >= 4 and has_negative_words and not has_positive_words:
                concerns.append("text_rating_incongruence")
                skepticism_score += 0.15
                break
            elif stars <= 2 and has_positive_words and not has_negative_words:
                concerns.append("text_rating_incongruence")
                skepticism_score += 0.15
                break
        
        # 5. Check for outdated reviews
        from datetime import datetime, timedelta
        try:
            recent_count = 0
            for review in reviews:
                review_date = datetime.strptime(review.get("date", ""), "%Y-%m-%d %H:%M:%S")
                if (datetime.now() - review_date).days <= 30:
                    recent_count += 1
            
            if recent_count == 0 and len(reviews) >= 3:
                concerns.append("outdated_feedback")
                skepticism_score += 0.1
        except:
            pass  # If date parsing fails, skip this check
        
        # Apply personality modifier
        skepticism_score *= personality_modifier
        skepticism_score = min(skepticism_score, 1.0)  # Cap at 1.0
        
        # Determine skepticism level
        if skepticism_score >= base_threshold:
            if skepticism_score >= 0.7:
                level = "high"
            elif skepticism_score >= 0.4:
                level = "medium"
            else:
                level = "low"
            will_investigate = True
        else:
            level = "none"
            will_investigate = False
        
        confidence_impact = -skepticism_score * 0.3  # Reduce confidence by up to 30%
        
        return {
            "level": level,
            "score": skepticism_score,
            "concerns": list(set(concerns)),  # Remove duplicates
            "will_investigate": will_investigate,
            "confidence_impact": confidence_impact,
            "personality_modifier": personality_modifier
        }
    
    def _post_investigation_assessment(self, initial_skepticism: Dict, additional_reviews: List) -> Dict:
        """
        Assess whether additional reviews resolved or increased skepticism.
        """
        if not additional_reviews:
            return {
                "resolved": True,
                "reason": "no_additional_reviews_available",
                "ongoing_doubt": False
            }
        
        # Simple check: if additional reviews show similar patterns, skepticism remains
        # If they show more variation, skepticism may be reduced
        additional_stars = [r.stars for r in additional_reviews]
        if len(additional_stars) > 0:
            additional_avg = sum(additional_stars) / len(additional_stars)
            additional_variance = sum((s - additional_avg) ** 2 for s in additional_stars) / len(additional_stars)
            
            # If variance is higher, it's more credible
            if additional_variance > 0.5:
                return {
                    "resolved": True,
                    "reason": "additional_reviews_show_variation",
                    "ongoing_doubt": False
                }
            else:
                return {
                    "resolved": False,
                    "reason": "additional_reviews_confirm_suspicious_pattern",
                    "ongoing_doubt": True
                }
        
        return {
            "resolved": False,
            "reason": "insufficient_additional_information",
            "ongoing_doubt": True
        }
    
    def _calculate_loyalty_metrics(self) -> Dict:
        """Calculate customer loyalty and switching behavior"""
        customer_patterns = {}
        
        for customer in self.customers:
            if not customer.experiences:
                continue
                
            customer_id = customer.customer_id
            visits_a = len([exp for exp in customer.experiences if exp.restaurant_id == "A"])
            visits_b = len([exp for exp in customer.experiences if exp.restaurant_id == "B"])
            total_visits = visits_a + visits_b
            
            # Calculate switching behavior
            switches = 0
            if len(customer.experiences) > 1:
                for i in range(1, len(customer.experiences)):
                    if customer.experiences[i].restaurant_id != customer.experiences[i-1].restaurant_id:
                        switches += 1
            
            customer_patterns[customer_id] = {
                "visits_a": visits_a,
                "visits_b": visits_b,
                "total_visits": total_visits,
                "switches": switches,
                "loyalty_a": visits_a / total_visits if total_visits > 0 else 0,
                "loyalty_b": visits_b / total_visits if total_visits > 0 else 0,
                "switch_rate": switches / (total_visits - 1) if total_visits > 1 else 0
            }
        
        # Calculate aggregate metrics
        total_customers_with_visits = len([p for p in customer_patterns.values() if p["total_visits"] > 0])
        
        if total_customers_with_visits == 0:
            return {"restaurant_a_loyalty": 0, "restaurant_b_loyalty": 0, "avg_switch_rate": 0}
        
        avg_loyalty_a = sum(p["loyalty_a"] for p in customer_patterns.values()) / total_customers_with_visits
        avg_loyalty_b = sum(p["loyalty_b"] for p in customer_patterns.values()) / total_customers_with_visits
        avg_switch_rate = sum(p["switch_rate"] for p in customer_patterns.values()) / total_customers_with_visits
        
        return {
            "restaurant_a_loyalty": avg_loyalty_a,
            "restaurant_b_loyalty": avg_loyalty_b,
            "avg_switch_rate": avg_switch_rate,
            "customer_patterns": customer_patterns
        }

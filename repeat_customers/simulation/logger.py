# logger.py - Repeat Customer Simulation
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict

class SimulationLogger:
    def __init__(self, log_dir: str):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_entries: List[Dict] = []
        self.restaurant_a = None  # Will be set by engine
        self.restaurant_b = None  # Will be set by engine
        
        # Initialize review exposure log file with empty array
        review_log_path = self.log_dir / "review_exposure.json"
        if not review_log_path.exists():
            with open(review_log_path, "w") as f:
                json.dump([], f)
    
    def log_customer_arrival(self, customer: Dict, day: int):
        self.log_entries.append({
            "timestamp": datetime.now().isoformat(),
            "type": "customer_arrival",
            "day": day,
            "customer_id": customer["customer_id"],
            "name": customer["name"],
            "details": {
                "income": customer["income"],
                "taste": customer["taste"],
                "health": customer["health"],
                "dietary_restriction": customer["dietary_restriction"],
                "personality": customer["personality"]
            }
        })
    
    def log_customer_experience_summary(self, customer_id: str, name: str, day: int, experiences: List):
        """Log customer's past experiences for context"""
        self.log_entries.append({
            "timestamp": datetime.now().isoformat(),
            "type": "customer_experience_summary",
            "day": day,
            "customer_id": customer_id,
            "name": name,
            "past_experiences": [
                {
                    "restaurant_id": exp.restaurant_id,
                    "date": exp.date,
                    "ordered_item": exp.ordered_item,
                    "stars_given": exp.stars_given,
                    "price_paid": exp.price_paid,
                    "was_satisfied": exp.was_satisfied
                }
                for exp in experiences[-5:]  # Last 5 experiences
            ],
            "total_experiences": len(experiences)
        })
    
    def log_customer_memory_state(self, customer_id: str, name: str, day: int, customer):
        """Log customer's current memory state and preferences"""
        # Calculate preferences for both restaurants
        pref_a = customer.get_restaurant_preference("A")
        pref_b = customer.get_restaurant_preference("B")
        visits_a = customer.get_experience_count("A")
        visits_b = customer.get_experience_count("B")
        
        self.log_entries.append({
            "timestamp": datetime.now().isoformat(),
            "type": "customer_memory_state",
            "day": day,
            "customer_id": customer_id,
            "name": name,
            "total_experiences": len(customer.experiences),
            "restaurant_preferences": {
                "restaurant_a": {
                    "preference_score": round(pref_a, 3),
                    "visit_count": visits_a,
                    "last_visit": customer.get_last_experience("A").date if customer.get_last_experience("A") else None
                },
                "restaurant_b": {
                    "preference_score": round(pref_b, 3),
                    "visit_count": visits_b,
                    "last_visit": customer.get_last_experience("B").date if customer.get_last_experience("B") else None
                }
            },
            "preferred_restaurant": "A" if pref_a > pref_b else "B" if pref_b > pref_a else "Neutral"
        })
    
    def log_decision(self, customer_id: str, name: str, decision: str, reason: str, day: int):
        self.log_entries.append({
            "timestamp": datetime.now().isoformat(),
            "type": "decision",
            "day": day,
            "customer_id": customer_id,
            "name": name,
            "decision": decision,
            "reason": reason
        })
    
    def log_order(self, customer_id: str, name: str, restaurant_id: str, item: str, price: float, day: int, menu_reason: str = ""):
        self.log_entries.append({
            "timestamp": datetime.now().isoformat(),
            "type": "order",
            "day": day,
            "customer_id": customer_id,
            "name": name,
            "restaurant_id": restaurant_id,
            "item": item,
            "price": price,
            "menu_selection_reason": menu_reason
        })
    
    def log_customer_experience(self, customer_id: str, name: str, day: int, experience):
        """Log the experience a customer had at a restaurant"""
        self.log_entries.append({
            "timestamp": datetime.now().isoformat(),
            "type": "customer_experience",
            "day": day,
            "customer_id": customer_id,
            "name": name,
            "restaurant_id": experience.restaurant_id,
            "ordered_item": experience.ordered_item,
            "stars_given": experience.stars_given,
            "price_paid": experience.price_paid,
            "was_satisfied": experience.was_satisfied,
            "review_text": experience.review_text
        })
    
    def log_review(self, review: Dict, reason: str, day: int):
        self.log_entries.append({
            "timestamp": datetime.now().isoformat(),
            "type": "review",
            "day": day,
            "review_id": review["review_id"],
            "customer_id": review["user_id"],
            "restaurant_id": review["business_id"],
            "stars": review["stars"],
            "text": review["text"],
            "item": review["ordered_item"],
            "reason": reason,
            "expectation_level": "high" if review["business_id"] == "A" else "normal"
        })
    
    def log_repeat_customer_stats(self, day: int):
        """Log statistics about repeat customers"""
        if self.restaurant_a and self.restaurant_b:
            a_stats = self.restaurant_a.get_repeat_customer_stats()
            b_stats = self.restaurant_b.get_repeat_customer_stats()
            
            self.log_entries.append({
                "timestamp": datetime.now().isoformat(),
                "type": "repeat_customer_stats",
                "day": day,
                "restaurant_a_stats": a_stats,
                "restaurant_b_stats": b_stats,
                "market_share": {
                    "restaurant_a_visits": a_stats["total_visits"],
                    "restaurant_b_visits": b_stats["total_visits"],
                    "total_visits": a_stats["total_visits"] + b_stats["total_visits"]
                }
            })
    
    def save_logs(self):
        with open(self.log_dir / "simulation_logs.json", "w") as f:
            json.dump(self.log_entries, f, indent=2)

    def log_decision_details(self, customer_id: str, name: str, 
                       a_reviews_shown: List[Dict], b_reviews_shown: List[Dict], 
                       decision: str, reason: str, day: int):
        """Logs which reviews were shown during decision-making along with TOTAL stats"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "decision_details",
            "day": day,
            "customer_id": customer_id,
            "name": name,
            "restaurant_a_info": {
                "overall_rating": round(self.restaurant_a.get_overall_rating(), 1),
                "total_reviews": self.restaurant_a.get_review_count(),
                "reviews_shown_count": len(a_reviews_shown),
                "reviews_shown": [
                    {"stars": r["stars"], "text": r["text"][:100] + "...", "date": r["date"]}
                    for r in a_reviews_shown
                ],
                "sort_method": self.restaurant_a.review_policy
            },
            "restaurant_b_info": {
                "overall_rating": round(self.restaurant_b.get_overall_rating(), 1),
                "total_reviews": self.restaurant_b.get_review_count(), 
                "reviews_shown_count": len(b_reviews_shown),
                "reviews_shown": [
                    {"stars": r["stars"], "text": r["text"][:100] + "...", "date": r["date"]}
                    for r in b_reviews_shown
                ],
                "sort_method": self.restaurant_b.review_policy
            },
            "decision": decision,
            "reason": reason
        }
                
        # Save to a separate file
        decision_log_path = self.log_dir / "decision_details.json"
        try:
            existing_data = []
            if decision_log_path.exists():
                with open(decision_log_path, "r") as f:
                    existing_data = json.load(f)
            
            existing_data.append(log_entry)
            
            with open(decision_log_path, "w") as f:
                json.dump(existing_data, f, indent=2)
        except Exception as e:
            print(f"Error saving decision details: {e}")

    def log_reviews_seen(self, customer_id: str, name: str, day: int,
                    restaurant_id: str, reviews: List[Dict], 
                    is_additional: bool = False):
        """Logs all reviews seen by a customer for a restaurant"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "reviews_seen",
            "day": day,
            "customer_id": customer_id,
            "name": name,
            "restaurant_id": restaurant_id,
            "is_additional": is_additional,
            "reviews": [
                {
                    "stars": r["stars"],
                    "text": r["text"][:200] + "..." if len(r["text"]) > 200 else r["text"],
                    "date": r["date"],
                    "review_id": r["review_id"]
                }
                for r in reviews
            ]
        }
        
        # Save to a separate file for detailed review tracking
        review_log_path = self.log_dir / "review_exposure.json"
        try:
            # Read existing data if file exists
            existing_data = []
            if review_log_path.exists():
                with open(review_log_path, "r") as f:
                    existing_data = json.load(f)
            
            # Append new entry
            existing_data.append(log_entry)
            
            # Write back to file
            with open(review_log_path, "w") as f:
                json.dump(existing_data, f, indent=2)
        except Exception as e:
            print(f"Error saving review exposure logs: {e}")

    def log_skepticism_assessment(self, customer_id: str, name: str, day: int,
                                restaurant_id: str, skepticism: Dict, post_investigation: Dict = None):
        """Log customer skepticism assessment and investigation results"""
        self.log_entries.append({
            "timestamp": datetime.now().isoformat(),
            "type": "skepticism_assessment",
            "day": day,
            "customer_id": customer_id,
            "name": name,
            "restaurant_id": restaurant_id,
            "skepticism_level": skepticism["level"],
            "concerns": skepticism["concerns"],
            "investigated": skepticism["will_investigate"],
            "initial_confidence_impact": skepticism["confidence_impact"],
            "skepticism_score": skepticism["score"],
            "personality_modifier": skepticism["personality_modifier"],
            "post_investigation": post_investigation
        })

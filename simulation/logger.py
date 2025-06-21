# logger.py
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict

class SimulationLogger:
    def __init__(self, log_dir: str):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_entries: List[Dict] = []
         # Initialize review exposure log file with empty array
        review_log_path = self.log_dir / "review_exposure.json"
        if not review_log_path.exists():
            with open(review_log_path, "w") as f:
                json.dump([], f)
    
    def log_customer_arrival(self, customer: Dict):
        self.log_entries.append({
            "timestamp": datetime.now().isoformat(),
            "type": "customer_arrival",
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
    
    def log_order(self, customer_id: str, name: str, restaurant_id: str, item: str, price: float, day: int):
        self.log_entries.append({
            "timestamp": datetime.now().isoformat(),
            "type": "order",
            "day": day,
            "customer_id": customer_id,
            "name": name,
            "restaurant_id": restaurant_id,
            "item": item,
            "price": price
        })
    
    def log_review(self, review: Dict, reason: str):
        self.log_entries.append({
            "timestamp": datetime.now().isoformat(),
            "type": "review",
            "review_id": review["review_id"],
            "customer_id": review["user_id"],
            "restaurant_id": review["business_id"],
            "stars": review["stars"],
            "text": review["text"],
            "item": review["ordered_item"],
            "reason": reason,
            "expectation_level": "high" if review["business_id"] == "A" else "normal"
        })
    
    def save_logs(self):
        with open(self.log_dir / "simulation_logs.json", "w") as f:
            json.dump(self.log_entries, f, indent=2)

    def log_decision_details(self, customer_id: str, name: str, 
                           a_reviews_shown: List[Dict], b_reviews_shown: List[Dict], 
                           decision: str, reason: str, day: int):
        """Logs which reviews were shown during decision-making"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "decision_details",
            "day": day,
            "customer_id": customer_id,
            "name": name,
            "restaurant_a_reviews_shown": [
                {"stars": r["stars"], "text": r["text"][:100] + "..."}  # Truncate for readability
                for r in a_reviews_shown
            ],
            "restaurant_b_reviews_shown": [
                {"stars": r["stars"], "text": r["text"][:100] + "..."}
                for r in b_reviews_shown
            ],
            "decision": decision,
            "reason": reason
        }
        
        # Save to a separate file
        decision_log_path = self.log_dir / "decision_details.json"
        try:
            # Read existing data if file exists
            existing_data = []
            if decision_log_path.exists():
                with open(decision_log_path, "r") as f:
                    existing_data = json.load(f)
            
            # Append new entry
            existing_data.append(log_entry)
            
            # Write back to file
            with open(decision_log_path, "w") as f:
                json.dump(existing_data, f, indent=2)
        except Exception as e:
            print(f"Error saving decision details: {e}")


    def log_review_investigation(self, customer_id: str, name: str, 
                            restaurant_id: str, initial_count: int,
                            additional_count: int, day: int):
        self.log_entries.append({
            "timestamp": datetime.now().isoformat(),
            "type": "review_investigation",
            "day": day,
            "customer_id": customer_id,
            "name": name,
            "restaurant_id": restaurant_id,
            "initial_reviews": initial_count,
            "additional_reviews": additional_count
        })


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
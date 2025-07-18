# llm.py
import openai
import json
import random
from datetime import datetime
from typing import Dict, List
from config import Config
import uuid

class LLMInterface:
    def __init__(self):
        self.client = openai.OpenAI(api_key=Config.API_KEY)
        self.model = Config.MODEL

    def generate_customer(self) -> Dict[str, str]:
        return {
            "name": f"Customer_{random.randint(1000, 9999)}",
            "income": random.choice([
                "$5K-5.8K(Very Poor)", 
                "$6K-7.9K(Poor)", 
                "$8K-11.9K(Middle Class)", 
                "$12K-14.8K(Affluent)"
            ]),
            "taste": random.choice([
                "Local comfort foods", "Rice and noodle dishes", "Sandwiches and salads", 
                "Breakfast foods", "Simple dishes", "Fast food", "Soups and stews", 
                "Meat", "Seafood", "Steak and meat dishes", "Vegan dishes", "Pasta and pizza", 
                "Chocolate and sweets", "Grilled dishes", "Mediterranean cuisine", 
                "Baked goods", "Spicy food", "Gourmet dishes", "Home cooking", "Exotic fruits", 
                "Grilled seafood", "Comfort food", "Sushi and Japanese cuisine", 
                "Italian cuisine", "Vegan options", "French cuisine", "Mexican food", 
                "Street food", "Indian cuisine", "Barbecue", "Organic food", "Chinese cuisine", 
                "Desserts", "Gourmet burgers", "Salads", "Fried food", "Plant-based meals", 
                "Fine dining", "Traditional cuisine", "Greek food", "Caribbean cuisine", 
                "Vegetarian dishes", "International cuisine"
            ]),
            "health": random.choice([
                "Healthy", "No concerns", "High blood pressure", "Diabetic", "Allergies", 
                "Lactose intolerant", "High cholesterol", "Overweight", "Gluten sensitivity", 
                "Gluten intolerance", "Vegan"
            ]),
            "dietary_restriction": random.choice([
                "None", "Low sodium", "Low sugar", "Low cholesterol", "Low fat", 
                "Gluten-free", "Dairy-free", "Vegan"
            ]),
            "personality": random.choice([
                "Easy-going", "Strict", "Picky", "Cheerful", "Shy", "Adventurous", 
                "Friendly", "Reserved", "Outspoken", "Energetic", "Compassionate", 
                "Relaxed", "Carefree", "Meticulous", "Artistic", "Curious", "Bold", 
                "Sophisticated", "Warm", "Discerning", "Easygoing", "Lively", "Spirited", 
                "Resourceful", "Thoughtful", "Sociable", "Optimistic", "Analytical", 
                "Creative", "Leader", "Gentle", "Jovial", "Ambitious", "Elegant", 
                "Outgoing", "Charismatic", "Explorer", "Intellectual", "Hardworking", 
                "Vibrant"
            ])
        }

    def generate_review(self, customer: Dict, business_id: str, ordered_item: str) -> Dict:
        quality_level = "Michelin-level (90/100)" if business_id == "A" else "local diner (60/100)"
        prompt = f"""Write a restaurant review in JSON based on:
        
        Customer: {customer['name']} ({customer['personality']})
        - Likes: {customer['taste']} food
        - Health: {customer['health']}/{customer['dietary_restriction']}
        - Budget: {customer['income']}
        Ordered: {ordered_item}
        Restaurant: {'A (Michelin-level, quality rating: 90/100)' if business_id == 'A' else 'B (Local diner, quality rating: 60/100)'}

        Rules:
        1. Star rating (1-5) should reflect both the restaurant's quality level AND how well it matched expectations
        2. Michelin-level (A) should be held to higher standards
        3. Mention price/value perception based on customer's budget
        4. Keep tone personality-appropriate
        5. Include specific reason for the rating

        Format:
        {{
            "stars": [1-5],
            "text": "I [30-50 words]",
            "rating_reason": "Specific explanation referencing quality level and my preferences",
            "review_id": "[REPLACE_WITH_UUID]",
            "user_id": "{customer['customer_id']}",
            "business_id": "{business_id}",
            "date": "YYYY-MM-DD HH:MM:SS",
            "ordered_item": "{ordered_item}"
        }}"""

        response = self._call_llm(prompt)
        
        review = response
        review["review_id"] = f"rev_{uuid.uuid4().hex[:8]}"
        review["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        review["ordered_item"] = ordered_item
        
        return review
    
    # llm.py - modify the make_decision method
# llm.py - update make_decision prompt
    def make_decision(self, customer: Dict, a_reviews: List[Dict], b_reviews: List[Dict], 
                    a_menu: Dict, b_menu: Dict, a_rating: float, a_count: int,
                    b_rating: float, b_count: int) -> Dict:
        prompt = f"""Act as {customer['name']} and choose between Restaurant A (high-end) or B (local diner) based on:

        Customer Profile:
        - Budget: {customer['income']}
        - Food Preferences: {customer['taste']}
        - Health/Diet: {customer['health']}{' ('+customer['dietary_restriction']+')' if customer['dietary_restriction'] != 'None' else ''}
        - Personality: {customer['personality']}

        Restaurant A (Michelin-level, quality rating: 90/100):
        - Shows highest rated reviews first
        - TOTAL Rating: {a_rating:.1f} stars from {a_count} combined reviews
        - Price Range: $$$$ (Average ${sum(a_menu.values())/len(a_menu):.1f})
        - Menu Items: {', '.join(a_menu.keys())}

        Restaurant B (Local diner, quality rating: 60/100):
        - Shows highest rated reviews first
        - TOTAL Rating: {b_rating:.1f} stars from {b_count} combined reviews
        - Price Range: $ (Average ${sum(b_menu.values())/len(b_menu):.1f})
        - Menu Items: {', '.join(b_menu.keys())}

        Restaurant A Sample Reviews (Highest Rated):
        {self._format_reviews(a_reviews[:5])}

        Restaurant B Sample Reviews (Highest Rated):
        {self._format_reviews(b_reviews[:5])}

        Consider:
        1. Objective quality ratings (90 vs 60)
        2. Price range and your budget
        3. Menu items matching your taste and dietary needs
        4. Your personality and dining preferences
        5. Whether the quality difference justifies the price difference

        Return JSON with:
        {{
            "decision": "A" or "B",
            "reason": "Detailed explanation considering quality rating, price, and personal factors"
        }}"""
            
        return self._call_llm(prompt)
            

    def _call_llm(self, prompt: str) -> Dict:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.7,
                timeout=10
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"LLM Error: {e}")
            return self._generate_fallback(prompt)    

    def _generate_fallback(self, prompt: str) -> Dict:
        if "review" in prompt:
            return {
                "review_id": f"fallback_{random.randint(1000,9999)}",
                "user_id": "fallback_user",
                "business_id": "A",
                "stars": 3,
                "text": "I had an average experience that matched my expectations.",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "ordered_item": "Burger"
            }
        elif "customer" in prompt:
            return {
                "name": "Fallback Customer",
                "income": "$0 (Unknown)",
                "taste": "Generic",
                "health": "Average",
                "dietary_restriction": "None",
                "personality": "Neutral"
            }
        else:
            return {
                "decision": random.choice(["A", "B"]),
                "reason": "I randomly chose this restaurant due to system error"
            }
        
    def _format_reviews(self, reviews: List[Dict]) -> str:
        return "\n".join(
            f"{r['stars']}⭐: {r['text']}"
            for r in reviews
        )
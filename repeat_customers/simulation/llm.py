# llm.py - Repeat Customer Simulation
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
    
    def generate_conf_review(self, customer_id: str, business_id: str, ordered_item: str, 
                           is_positive: bool, true_quality: float) -> Dict:
        """
        Generate a realistic review for CoNF experiment using LLM.
        """
        
        # Create a basic customer profile for the review generation
        experience_type = "positive" if is_positive else "negative"
        quality_description = "high-quality" if true_quality > 0.6 else "average" if true_quality > 0.4 else "below-average"
        
        prompt = f"""Generate a realistic restaurant review for the following scenario:

Customer ID: {customer_id}
Restaurant: {business_id}
Ordered Item: {ordered_item}
Experience Type: {experience_type}
Restaurant Quality Level: {quality_description} (μ={true_quality:.1f})

The customer had a {experience_type} experience that reflects the restaurant's {quality_description} quality level.

Requirements:
1. Generate a star rating appropriate for the experience type:
   - Positive experience: 4-5 stars
   - Negative experience: 1-3 stars
2. Write 20-40 words of realistic review text
3. Mention the ordered item naturally in the review
4. Use authentic restaurant review language
5. Make the rating consistent with the text

Format as JSON:
{{
    "stars": [rating 1-5],
    "text": "[realistic review text mentioning the experience and food]",
    "user_id": "{customer_id}",
    "business_id": "{business_id}",
    "ordered_item": "{ordered_item}"
}}"""

        response = self._call_llm(prompt)
        
        # Add additional fields
        review = response
        review["review_id"] = f"conf_{uuid.uuid4().hex[:8]}"
        review["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return review
    
    def make_repeat_customer_decision(self, customer: Dict, customer_experiences: List, 
                                    a_reviews: List[Dict], b_reviews: List[Dict], 
                                    a_menu: Dict, b_menu: Dict, a_rating: float, a_count: int,
                                    b_rating: float, b_count: int, restaurant_a=None, restaurant_b=None, 
                                    a_skepticism: Dict = None, b_skepticism: Dict = None,
                                    a_post_investigation: Dict = None, b_post_investigation: Dict = None,
                                    day: int = 1) -> Dict:
        """
        Make decision for repeat customer considering past experiences
        """
        # Get dynamic quality ratings (convert to 0-100 scale)
        a_quality = restaurant_a.get_overall_rating() * 20 if restaurant_a else Config.RESTAURANT_A_RATING
        b_quality = restaurant_b.get_overall_rating() * 20 if restaurant_b else Config.RESTAURANT_B_RATING
        
        # Calculate price values
        a_avg_price = sum(a_menu.values()) / len(a_menu)
        b_avg_price = sum(b_menu.values()) / len(b_menu)
        price_diff = a_avg_price - b_avg_price
        
        # Format past experiences
        experience_context = self._format_customer_experiences(customer_experiences)
        
        prompt = f"""Act as {customer['name']} (Day {day}) and choose between Restaurant A or B based on:

        Customer Profile:
        - Budget: {customer['income']}
        - Food Preferences: {customer['taste']}
        - Health/Diet: {customer['health']}{' ('+customer['dietary_restriction']+')' if customer['dietary_restriction'] != 'None' else ''}
        - Personality: {customer['personality']}

        {experience_context}

        Restaurant A:
        - Quality Rating: {a_quality}/100 (based on average of all reviews)
        - TOTAL Rating: {a_rating:.1f} stars from {a_count} combined reviews
        - Average Meal Price: ${a_avg_price:.1f} per person
        - Price Range: $$$$ (${min(a_menu.values())} - ${max(a_menu.values())})
        - Menu Items: {', '.join(a_menu.keys())}

        Restaurant B:
        - Quality Rating: {b_quality}/100 (based on average of all reviews)
        - TOTAL Rating: {b_rating:.1f} stars from {b_count} combined reviews
        - Average Meal Price: ${b_avg_price:.1f} per person
        - Price Range: $ (${min(b_menu.values())} - ${max(b_menu.values())})
        - Menu Items: {', '.join(b_menu.keys())}

        Restaurant A Sample Reviews (Highest Rated):
        {self._format_reviews(a_reviews[:5])}

        Restaurant B Sample Reviews (Highest Rated):
        {self._format_reviews(b_reviews[:5])}

        {self._format_skepticism_context(a_skepticism, a_post_investigation, "A")}
        {self._format_skepticism_context(b_skepticism, b_post_investigation, "B")}

        DECISION CRITERIA (considering your past experiences):
        1. **Personal Experience**: How did your past visits go? Which restaurant gave you better experiences?
        2. **Reviews vs Reality**: Do the reviews match what you experienced personally?
        3. **Quality vs Price**: Is the quality difference worth the price difference?
        4. **Consistency**: Which restaurant has been more consistent?

        Return JSON with:
        {{
            "decision": "A" or "B",
            "reason": "Brief explanation (1-2 sentences max)"
        }}"""
            
        return self._call_llm(prompt)
    
    def choose_menu_item(self, customer: Dict, restaurant_id: str, menu: Dict, past_orders: List = None) -> Dict:
        """Let customer choose menu item based on their profile and past orders"""
        restaurant_type = "High-end restaurant" if restaurant_id == "A" else "Basic diner"
        
        # Format past orders if available
        past_orders_context = ""
        if past_orders:
            past_orders_context = f"\nYour past orders at this restaurant: {', '.join(past_orders)}"
        
        prompt = f"""Act as {customer['name']} and choose what to order from the {restaurant_type} menu based on:

        Customer Profile:
        - Budget: {customer['income']}
        - Food Preferences: {customer['taste']}
        - Health/Diet: {customer['health']}{' ('+customer['dietary_restriction']+')' if customer['dietary_restriction'] != 'None' else ''}
        - Personality: {customer['personality']}
        {past_orders_context}

        Restaurant {restaurant_id} ({restaurant_type}) Menu:
        {chr(10).join(f"- {item}: ${price}" for item, price in menu.items())}

        Consider:
        1. Which menu item best matches your taste preferences
        2. Price affordability based on your income level
        3. Dietary restrictions and health considerations
        4. Your personality traits (adventurous vs conservative, etc.)
        5. The restaurant type and expected quality level
        6. Whether you want to try something new or stick with what you know worked

        Return JSON with:
        {{
            "chosen_item": "[exact menu item name]",
            "reason": "Brief explanation (1 sentence)"
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
        elif "choose what to order" in prompt:
            return {
                "chosen_item": "Burger",
                "reason": "Fallback selection due to system error"
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
    
    def _format_customer_experiences(self, experiences: List) -> str:
        """Format customer's past experiences for the prompt"""
        if not experiences:
            return "Your Past Experiences: This is your first time choosing between these restaurants."
        
        context = "Your Past Experiences:\n"
        for exp in experiences[-5:]:  # Show last 5 experiences
            satisfaction = "satisfied" if exp.was_satisfied else "disappointed"
            context += f"- Restaurant {exp.restaurant_id}: Ordered {exp.ordered_item} (${exp.price_paid}), rated {exp.stars_given}★ - you were {satisfaction}\n"
        
        return context

    def _format_skepticism_context(self, skepticism: Dict, post_investigation: Dict, restaurant_id: str) -> str:
        """Format skepticism information for the LLM prompt"""
        if not skepticism:
            return ""
        
        context = f"\nYour feelings about Restaurant {restaurant_id}:\n"
        
        if skepticism["level"] == "none":
            context += "- You feel confident about the reviews shown\n"
        else:
            level_descriptions = {
                "low": "slightly suspicious",
                "medium": "moderately skeptical", 
                "high": "very skeptical"
            }
            context += f"- You feel {level_descriptions.get(skepticism['level'], 'uncertain')} about the reviews\n"
            
            if skepticism["concerns"]:
                concern_descriptions = {
                    "suspiciously_uniform_distribution": "ratings look unnaturally consistent — real reviews usually show some variation",
                    "low_variance_extreme_mean": "ratings cluster too tightly around an extreme average, which feels less credible",
                    "rating_sentiment_mismatch": "average star rating and written sentiment don't align, lowering trust",
                    "text_rating_incongruence": "review text tone conflicts with the star ratings, suggesting inconsistency",
                    "outdated_feedback": "most reviews are old, reducing their relevance",
                    "stale_reviews": "feedback seems outdated and may not reflect current quality",
                    "rating_comparison": "compare ratings of reviews we are looking at versus the restaurant total reviews, suggesting they don't match"
                }
                context += "- Your concerns: " + ", ".join(
                    concern_descriptions.get(concern, concern) for concern in skepticism["concerns"]
                ) + "\n"
        
        if post_investigation:
            if post_investigation["resolved"]:
                context += f"- After investigating more reviews, your concerns were {post_investigation['reason'].replace('_', ' ')}\n"
            else:
                context += f"- Even after seeing more reviews, you still feel doubtful because {post_investigation['reason'].replace('_', ' ')}\n"
                if post_investigation["ongoing_doubt"]:
                    context += "- You remain somewhat uncertain about this restaurant\n"
        
        return context

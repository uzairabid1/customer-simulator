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

    def generate_review(self, customer: Dict, business_id: str, ordered_item: str, restaurant=None) -> Dict:
        # Use dynamic quality rating if restaurant object is provided
        if restaurant:
            quality_rating = restaurant.get_quality_rating()
            quality_level = f"quality rating: {quality_rating}/100"
        else:
            # Fallback to static values if no restaurant object
            quality_rating = Config.RESTAURANT_A_RATING if business_id == "A" else Config.RESTAURANT_B_RATING
            quality_level = f"Michelin-level ({Config.RESTAURANT_A_RATING}/100)" if business_id == "A" else f"local diner ({Config.RESTAURANT_B_RATING}/100)"
        prompt = f"""Write a restaurant review in JSON based on:
        
        Customer: {customer['name']} ({customer['personality']})
        - Likes: {customer['taste']} food
        - Health: {customer['health']}/{customer['dietary_restriction']}
        - Budget: {customer['income']}
        Ordered: {ordered_item}
        Restaurant: {business_id} ({quality_level})

        Rules:
        1. Star rating (1-5) should reflect both the restaurant's quality level AND how well it matched expectations
        2. Higher quality ratings should be held to higher standards - expectations should match the quality level
        3. Mention price/value perception based on customer's budget
        4. Keep tone personality-appropriate
        5. Include specific reason for the rating
        6. Quality expectations should be proportional to the restaurant's quality rating

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
    
    def generate_conf_review(self, customer_id: str, business_id: str, ordered_item: str, 
                           is_positive: bool, true_quality: float) -> Dict:
        """
        Generate a realistic review for CoNF experiment using LLM.
        
        Args:
            customer_id: ID of the customer leaving the review
            business_id: Restaurant ID
            ordered_item: Menu item ordered
            is_positive: Whether the experience was positive (X_t=1) or negative (X_t=0)
            true_quality: True quality parameter (μ) for context
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
    
    # llm.py - modify the make_decision method
# llm.py - update make_decision prompt
    def make_decision(self, customer: Dict, a_reviews: List[Dict], b_reviews: List[Dict], 
                    a_menu: Dict, b_menu: Dict, a_rating: float, a_count: int,
                    b_rating: float, b_count: int, restaurant_a=None, restaurant_b=None, 
                    a_skepticism: Dict = None, b_skepticism: Dict = None,
                    a_post_investigation: Dict = None, b_post_investigation: Dict = None) -> Dict:
        # Get dynamic quality ratings
        a_quality = restaurant_a.get_quality_rating() if restaurant_a else Config.RESTAURANT_A_RATING
        b_quality = restaurant_b.get_quality_rating() if restaurant_b else Config.RESTAURANT_B_RATING
        
        # Calculate price values to avoid f-string syntax issues
        a_avg_price = sum(a_menu.values()) / len(a_menu)
        b_avg_price = sum(b_menu.values()) / len(b_menu)
        price_diff = a_avg_price - b_avg_price
        
        prompt = f"""Act as {customer['name']} and choose between Restaurant A or B based on:

        Customer Profile:
        - Budget: {customer['income']}
        - Food Preferences: {customer['taste']}
        - Health/Diet: {customer['health']}{' ('+customer['dietary_restriction']+')' if customer['dietary_restriction'] != 'None' else ''}
        - Personality: {customer['personality']}

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

        PRICE COMPARISON SUMMARY:
        - Restaurant A: ${a_avg_price:.1f} average meal price
        - Restaurant B: ${b_avg_price:.1f} average meal price
        - Price Difference: ${price_diff:.1f} more for Restaurant A

        DECISION CRITERIA (in order of importance):
        1. **Quality Difference**: Restaurant A has {a_quality - b_quality:.1f} points higher quality rating (based on actual reviews)
        2. **Budget Compatibility**: Can you afford Restaurant A's prices (${a_avg_price:.1f} avg) given your income level?
        3. **Review Trustworthiness**: How confident are you in the reviews for each restaurant?
        4. **Food Preferences**: Do the menu items match your taste preferences?
        5. **Personality Match**: Does the dining experience align with your personality?
        6. **Value Assessment**: Is the quality improvement worth the ${price_diff:.1f} price difference for you?

        IMPORTANT: Restaurant A offers {a_quality - b_quality:.1f} points higher quality (based on review averages) for ${price_diff:.1f} more per meal. Consider if this quality difference justifies the price difference.

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
        
    def choose_menu_item(self, customer: Dict, restaurant_id: str, menu: Dict) -> Dict:
        """Let customer choose menu item based on their profile"""
        restaurant_type = "High-end restaurant" if restaurant_id == "A" else "Basic diner"
        prompt = f"""Act as {customer['name']} and choose what to order from the {restaurant_type} menu based on:

        Customer Profile:
        - Budget: {customer['income']}
        - Food Preferences: {customer['taste']}
        - Health/Diet: {customer['health']}{' ('+customer['dietary_restriction']+')' if customer['dietary_restriction'] != 'None' else ''}
        - Personality: {customer['personality']}

        Restaurant {restaurant_id} ({restaurant_type}) Menu:
        {chr(10).join(f"- {item}: ${price}" for item, price in menu.items())}

        Consider:
        1. Which menu item best matches your taste preferences
        2. Price affordability based on your income level
        3. Dietary restrictions and health considerations
        4. Your personality traits (adventurous vs conservative, etc.)
        5. The restaurant type and expected quality level

        Return JSON with:
        {{
            "chosen_item": "[exact menu item name]",
            "reason": "Brief explanation of why this item appeals to you"
        }}"""
        
        return self._call_llm(prompt)

    def _format_reviews(self, reviews: List[Dict]) -> str:
        return "\n".join(
            f"{r['stars']}⭐: {r['text']}"
            for r in reviews
        )

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
import random
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MealRecommender:
    def __init__(self, nutrition_data_loader):
        self.data_loader = nutrition_data_loader
        self.food_database = nutrition_data_loader.food_database if nutrition_data_loader.food_database is not None else None
        
    def generate_meal_plan(self, user_profile, days=7):
        """Generate a personalized meal plan based on user profile"""
        if self.food_database is None:
            logger.error("Food database not loaded")
            return None
        
        try:
            # Calculate daily calorie needs
            daily_calories = self._calculate_daily_calories(user_profile)
            
            # Calculate macronutrient ratios
            macros = self._calculate_macros(user_profile, daily_calories)
            
            # Generate meal plan
            meal_plan = {}
            days_of_week = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            
            for i in range(days):
                day = days_of_week[i % 7]
                meal_plan[day] = self._generate_day_plan(daily_calories, macros, user_profile)
            
            return meal_plan
        except Exception as e:
            logger.error(f"Error generating meal plan: {str(e)}")
            return None
    
    def _calculate_daily_calories(self, user_profile):
        """Calculate daily calorie needs using Mifflin-St Jeor Equation"""
        base_calories = 1800  # Default
        
        # If we have enough data for a better estimate
        if all(k in user_profile for k in ['weight', 'height', 'age', 'gender', 'activity_level']):
            weight = float(user_profile['weight'])
            height = float(user_profile['height'])
            age = int(user_profile['age'])
            gender = user_profile['gender'].lower()
            
            if gender == 'male':
                base_calories = 10 * weight + 6.25 * height - 5 * age + 5
            else:
                base_calories = 10 * weight + 6.25 * height - 5 * age - 161
            
            # Activity multiplier
            activity_multipliers = {
                'sedentary': 1.2,
                'lightly_active': 1.375,
                'moderately_active': 1.55,
                'very_active': 1.725,
                'extra_active': 1.9
            }
            
            activity_level = user_profile.get('activity_level', 'moderately_active')
            daily_calories = base_calories * activity_multipliers.get(activity_level, 1.55)
            
            # Adjust for weight goals
            if 'goals' in user_profile:
                goals = user_profile['goals'].lower()
                if 'weight_loss' in goals:
                    daily_calories *= 0.85  # 15% deficit for weight loss
                elif 'weight_gain' in goals:
                    daily_calories *= 1.15  # 15% surplus for weight gain
            
            return int(daily_calories)
        
        return int(base_calories)
    
    def _calculate_macros(self, user_profile, daily_calories):
        """Calculate macronutrient distribution based on user profile"""
        # Default macros
        macros = {
            'protein': 0.25,  # 25% of calories from protein
            'carbs': 0.5,     # 50% of calories from carbs
            'fat': 0.25       # 25% of calories from fat
        }
        
        # Adjust based on goals
        if 'goals' in user_profile:
            goals = user_profile['goals'].lower()
            if 'weight_loss' in goals:
                macros = {
                    'protein': 0.30,  # Higher protein for weight loss
                    'carbs': 0.40,
                    'fat': 0.30
                }
            elif 'weight_gain' in goals:
                macros = {
                    'protein': 0.25,
                    'carbs': 0.55,    # Higher carbs for weight gain
                    'fat': 0.20
                }
            elif 'muscle_gain' in goals:
                macros = {
                    'protein': 0.35,  # Higher protein for muscle gain
                    'carbs': 0.45,
                    'fat': 0.20
                }
        
        # Calculate grams based on caloric distribution
        # Protein: 4 calories per gram
        # Carbs: 4 calories per gram
        # Fat: 9 calories per gram
        return {
            'protein_g': round((daily_calories * macros['protein']) / 4),
            'carbs_g': round((daily_calories * macros['carbs']) / 4),
            'fat_g': round((daily_calories * macros['fat']) / 9),
            'protein_pct': macros['protein'] * 100,
            'carbs_pct': macros['carbs'] * 100,
            'fat_pct': macros['fat'] * 100
        }
    
    def _generate_day_plan(self, total_calories, macros, user_profile):
        """Generate a day's meal plan"""
        # Meal distribution
        meal_distribution = {
            'breakfast': 0.25,
            'lunch': 0.35,
            'dinner': 0.30,
            'snack': 0.10
        }
        
        meal_plan = {"meals": [], "totalCalories": 0, "totalProtein": 0, "totalCarbs": 0, "totalFat": 0}
        
        # Account for dietary preferences
        preferences = user_profile.get('dietary_preferences', '').lower()
        filtered_foods = self.food_database.copy()
        
        if 'vegetarian' in preferences:
            # Filter out meat items
            meat_keywords = ['beef', 'chicken', 'pork', 'turkey', 'meat', 'fish', 'salmon']
            filtered_foods = filtered_foods[~filtered_foods['label'].str.lower().str.contains('|'.join(meat_keywords))]
        
        # Generate meals
        for meal_type, percentage in meal_distribution.items():
            meal_calories = int(total_calories * percentage)
            
            # Select a random food item appropriate for this meal
            suitable_foods = self._filter_by_meal_type(filtered_foods, meal_type)
            if suitable_foods.empty:
                suitable_foods = filtered_foods  # Fallback if no specific foods
            
            food = suitable_foods.sample(1).iloc[0]
            
            # Calculate appropriate servings
            serving_size = food['weight']  # in grams
            calories_per_serving = food['calories']
            servings = meal_calories / max(calories_per_serving, 1)
            
            meal = {
                "type": meal_type,
                "name": food['label'],
                "calories": int(calories_per_serving * servings),
                "protein": round(food['protein'] * servings, 1),
                "carbs": round(food['carbohydrates'] * servings, 1),
                "fat": round(food['fats'] * servings, 1),
                "servings": round(servings, 2),
                "serving_size": f"{serving_size}g",
                "recipe_link": f"https://example.com/recipes/{food['label'].lower().replace(' ', '-')}"
            }
            
            meal_plan["meals"].append(meal)
            meal_plan["totalCalories"] += meal["calories"]
            meal_plan["totalProtein"] += meal["protein"] 
            meal_plan["totalCarbs"] += meal["carbs"]
            meal_plan["totalFat"] += meal["fat"]
        
        # Round totals
        meal_plan["totalProtein"] = round(meal_plan["totalProtein"], 1)
        meal_plan["totalCarbs"] = round(meal_plan["totalCarbs"], 1)
        meal_plan["totalFat"] = round(meal_plan["totalFat"], 1)
        
        return meal_plan
    
    def _filter_by_meal_type(self, foods_df, meal_type):
        """Filter foods by appropriate meal type"""
        if meal_type == 'breakfast':
            breakfast_keywords = ['pancakes', 'waffles', 'french_toast', 'eggs', 'omelette', 'breakfast']
            return foods_df[foods_df['label'].str.lower().str.contains('|'.join(breakfast_keywords))]
        elif meal_type == 'lunch':
            lunch_keywords = ['sandwich', 'salad', 'soup', 'wrap', 'bowl']
            return foods_df[foods_df['label'].str.lower().str.contains('|'.join(lunch_keywords))]
        elif meal_type == 'dinner':
            dinner_keywords = ['steak', 'chicken', 'fish', 'salmon', 'pasta', 'rice', 'bowl']
            return foods_df[foods_df['label'].str.lower().str.contains('|'.join(dinner_keywords))]
        elif meal_type == 'snack':
            snack_keywords = ['fruit', 'yogurt', 'nuts', 'hummus', 'bar']
            return foods_df[foods_df['label'].str.lower().str.contains('|'.join(snack_keywords))]
        
        return foods_df
    
    def get_nutrition_insights(self, user_food_logs, user_profile):
        """Generate nutrition insights based on user's food logs"""
        insights = []
        
        # Calculate total and average nutrients
        if not user_food_logs:
            return {
                "message": "Not enough data for insights. Log more meals for personalized nutrition insights.",
                "insights": []
            }
        
        # Extract nutrients from food logs
        total_calories = sum(log.calories for log in user_food_logs)
        total_protein = sum(log.protein for log in user_food_logs)
        total_carbs = sum(log.carbs for log in user_food_logs)
        total_fat = sum(log.fat for log in user_food_logs)
        total_fiber = sum(log.fiber or 0 for log in user_food_logs)
        total_sugar = sum(log.sugar or 0 for log in user_food_logs)
        
        # Calculate daily averages
        days = max(1, len(set(log.logged_at.date() for log in user_food_logs)))
        avg_calories = total_calories / days
        avg_protein = total_protein / days
        avg_carbs = total_carbs / days
        avg_fat = total_fat / days
        avg_fiber = total_fiber / days
        avg_sugar = total_sugar / days
        
        # Calculate calorie distribution
        calories_from_protein = total_protein * 4
        calories_from_carbs = total_carbs * 4
        calories_from_fat = total_fat * 9
        total_calorie_sum = calories_from_protein + calories_from_carbs + calories_from_fat
        
        if total_calorie_sum > 0:
            protein_pct = (calories_from_protein / total_calorie_sum) * 100
            carbs_pct = (calories_from_carbs / total_calorie_sum) * 100
            fat_pct = (calories_from_fat / total_calorie_sum) * 100
        else:
            protein_pct = carbs_pct = fat_pct = 0
        
        # Generate insights based on calculated values
        # Protein insights
        if protein_pct < 10:
            insights.append({
                "category": "protein",
                "message": "Your protein intake is very low. Protein is essential for muscle maintenance and recovery.",
                "recommendation": "Try to include more lean protein sources like chicken, fish, tofu, or legumes.",
                "priority": "high"
            })
        elif protein_pct < 15:
            insights.append({
                "category": "protein",
                "message": "Your protein intake could be higher for optimal health.",
                "recommendation": "Consider adding more protein-rich foods to your meals.",
                "priority": "medium"
            })
        elif protein_pct > 35:
            insights.append({
                "category": "protein",
                "message": "Your protein intake is quite high. While protein is important, balance is key.",
                "recommendation": "Consider diversifying your diet with more fruits, vegetables, and whole grains.",
                "priority": "medium"
            })
        
        # Carbs insights
        if carbs_pct < 30:
            insights.append({
                "category": "carbs",
                "message": "Your carbohydrate intake is low. Carbs are your body's main energy source.",
                "recommendation": "Include more complex carbohydrates like whole grains, fruits, and vegetables.",
                "priority": "medium"
            })
        elif carbs_pct > 65:
            insights.append({
                "category": "carbs",
                "message": "Your diet is very high in carbohydrates.",
                "recommendation": "Try to balance your meals with more protein and healthy fats.",
                "priority": "medium"
            })
        
        # Fat insights
        if fat_pct < 15:
            insights.append({
                "category": "fat",
                "message": "Your fat intake is low. Healthy fats are essential for hormone production and nutrient absorption.",
                "recommendation": "Include sources of healthy fats like avocados, nuts, seeds, and olive oil.",
                "priority": "medium"
            })
        elif fat_pct > 40:
            insights.append({
                "category": "fat",
                "message": "Your fat intake is high. While healthy fats are important, they're also calorie-dense.",
                "recommendation": "Focus on healthy fat sources and consider moderating overall fat intake.",
                "priority": "medium"
            })
        
        # Fiber insights
        if avg_fiber < 25:
            insights.append({
                "category": "fiber",
                "message": "Your fiber intake appears to be below recommendations. Fiber is important for digestive health.",
                "recommendation": "Add more fruits, vegetables, legumes, and whole grains to increase your fiber intake.",
                "priority": "medium"
            })
        
        # Sugar insights
        if avg_sugar > 50:
            insights.append({
                "category": "sugar",
                "message": "Your sugar intake appears to be high. Excessive sugar consumption is linked to various health issues.",
                "recommendation": "Try to reduce added sugars in your diet by limiting sweetened beverages and processed foods.",
                "priority": "high"
            })
        
        # Calorie insights
        if 'weight' in user_profile and 'height' in user_profile and 'age' in user_profile and 'gender' in user_profile:
            # Calculate estimated calorie needs
            estimated_calories = self._calculate_daily_calories(user_profile)
            
            if avg_calories < estimated_calories * 0.7:
                insights.append({
                    "category": "calories",
                    "message": f"Your average calorie intake ({int(avg_calories)}) is much lower than your estimated needs ({estimated_calories}).",
                    "recommendation": "Consider eating more nutrient-dense foods to meet your energy requirements.",
                    "priority": "high"
                })
            elif avg_calories > estimated_calories * 1.3:
                insights.append({
                    "category": "calories",
                    "message": f"Your average calorie intake ({int(avg_calories)}) is higher than your estimated needs ({estimated_calories}).",
                    "recommendation": "Consider monitoring portion sizes if weight maintenance is your goal.",
                    "priority": "medium"
                })
        
        # Return the insights along with the calculated averages
        return {
            "macronutrient_ratios": {
                "protein_percentage": round(protein_pct, 1),
                "carbs_percentage": round(carbs_pct, 1),
                "fat_percentage": round(fat_pct, 1)
            },
            "daily_averages": {
                "calories": round(avg_calories, 1),
                "protein": round(avg_protein, 1),
                "carbs": round(avg_carbs, 1),
                "fat": round(avg_fat, 1),
                "fiber": round(avg_fiber, 1),
                "sugar": round(avg_sugar, 1)
            },
            "insights": insights,
            "food_recommendations": self._generate_food_recommendations(insights, user_profile)
        }
    
    def _generate_food_recommendations(self, insights, user_profile):
        """Generate food recommendations based on insights"""
        recommendations = []
        
        # Extract which categories need improvement
        categories_to_improve = [insight["category"] for insight in insights if insight["priority"] in ["high", "medium"]]
        
        if "protein" in categories_to_improve:
            if 'vegetarian' in user_profile.get('dietary_preferences', '').lower():
                recommendations.extend([
                    "Greek yogurt (high protein dairy)",
                    "Lentils (plant-based protein)",
                    "Tofu (complete plant protein)",
                    "Chickpeas (protein and fiber)",
                    "Quinoa (complete protein grain)"
                ])
            else:
                recommendations.extend([
                    "Chicken breast (lean protein)",
                    "Greek yogurt (high protein dairy)",
                    "Eggs (complete protein)",
                    "Tuna (lean protein source)",
                    "Turkey (lean meat protein)"
                ])
        
        if "carbs" in categories_to_improve:
            if any("carbs" in insight["message"] and "high" in insight["message"] for insight in insights):
                # Recommendation for reducing carbs
                recommendations.extend([
                    "Replace refined grains with vegetables",
                    "Choose lower-carb fruits like berries",
                    "Include more leafy greens"
                ])
            else:
                # Recommendation for increasing carbs
                recommendations.extend([
                    "Oatmeal (complex carbs with fiber)",
                    "Sweet potatoes (nutrient-dense carb source)",
                    "Brown rice (whole grain carb source)",
                    "Bananas (carbs with potassium)",
                    "Whole grain bread (complex carbs)"
                ])
        
        if "fat" in categories_to_improve:
            if any("fat" in insight["message"] and "high" in insight["message"] for insight in insights):
                # Recommendation for healthier fats
                recommendations.extend([
                    "Choose lean protein sources",
                    "Use olive oil instead of butter",
                    "Include fatty fish like salmon"
                ])
            else:
                # Recommendation for increasing healthy fats
                recommendations.extend([
                    "Avocados (healthy monounsaturated fats)",
                    "Nuts (healthy fats and protein)",
                    "Olive oil (healthy cooking oil)",
                    "Chia seeds (omega-3 fatty acids)",
                    "Fatty fish like salmon (omega-3 sources)"
                ])
        
        if "fiber" in categories_to_improve:
            recommendations.extend([
                "Chia seeds (high in soluble fiber)",
                "Berries (fruit with high fiber)",
                "Lentils (protein and fiber)",
                "Broccoli (vegetable with fiber)",
                "Oats (whole grain with beta-glucan fiber)"
            ])
        
        if "sugar" in categories_to_improve:
            recommendations.extend([
                "Replace sugary drinks with water or herbal tea",
                "Choose whole fruits instead of fruit juices",
                "Read labels for hidden added sugars",
                "Try cinnamon as a natural sweetener",
                "Gradually reduce sugar in coffee/tea"
            ])
        
        # If no specific categories, add general healthy eating recommendations
        if not recommendations:
            recommendations = [
                "Eat a variety of colorful fruits and vegetables",
                "Choose whole grains over refined grains",
                "Include lean proteins in your meals",
                "Stay hydrated by drinking water throughout the day",
                "Limit highly processed foods and added sugars"
            ]
        
        return recommendations[:10]  # Limit to top 10 recommendations
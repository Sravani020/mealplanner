# Fake Nutrition Data (Instead of API)
NUTRITION_DATA = {
    "Pizza": {"calories": 300, "protein": 12, "carbs": 36, "fats": 10},
    "Burger": {"calories": 450, "protein": 20, "carbs": 40, "fats": 25},
    "Pasta": {"calories": 350, "protein": 15, "carbs": 50, "fats": 8},
    "Salad": {"calories": 150, "protein": 5, "carbs": 20, "fats": 5},
}

def get_nutrition(food_name):
    return NUTRITION_DATA.get(food_name, {"calories": 0, "protein": 0, "carbs": 0, "fats": 0})

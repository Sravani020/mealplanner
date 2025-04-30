from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import re

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str

    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    dietary_preferences: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    activity_level: Optional[str] = None
    goals: Optional[str] = None

class UserResponse(UserBase):
    id: int
    dietary_preferences: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    activity_level: Optional[str] = None
    goals: Optional[str] = None
    created_at: datetime
    
    class Config:
        orm_mode = True

# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]

# Food schemas
class FoodItemBase(BaseModel):
    name: str
    brand: Optional[str] = None
    serving_size: str
    calories: float
    protein: float
    carbs: float
    fat: float

class FoodItemCreate(FoodItemBase):
    barcode: Optional[str] = None
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None
    potassium: Optional[float] = None
    cholesterol: Optional[float] = None
    saturated_fat: Optional[float] = None
    trans_fat: Optional[float] = None
    vitamin_a: Optional[float] = None
    vitamin_c: Optional[float] = None
    calcium: Optional[float] = None
    iron: Optional[float] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None

class FoodItem(FoodItemBase):
    id: int
    barcode: Optional[str] = None
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    
    class Config:
        orm_mode = True

class FoodItemDetail(FoodItem):
    potassium: Optional[float] = None
    cholesterol: Optional[float] = None
    saturated_fat: Optional[float] = None
    trans_fat: Optional[float] = None
    vitamin_a: Optional[float] = None
    vitamin_c: Optional[float] = None
    calcium: Optional[float] = None
    iron: Optional[float] = None
    subcategory: Optional[str] = None
    created_at: datetime
    is_verified: bool
    
    class Config:
        orm_mode = True

# Food log schemas
class FoodLogBase(BaseModel):
    food_name: str
    meal_type: str
    calories: float
    protein: float
    carbs: float
    fat: float
    serving_size: Optional[str] = None
    servings: float = 1.0
    fiber: Optional[float] = None
    sugar: Optional[float] = None

class FoodLogCreate(FoodLogBase):
    logged_at: Optional[datetime] = None
    food_item_id: Optional[int] = None

class FoodLog(FoodLogBase):
    id: int
    user_id: int
    logged_at: datetime
    food_item_id: Optional[int] = None
    
    class Config:
        orm_mode = True

# Meal schemas
class MealItem(BaseModel):
    type: str
    name: str
    calories: int
    protein: float
    carbs: float
    fat: float
    servings: Optional[float] = None
    recipe_link: Optional[str] = None

class DailyMealPlan(BaseModel):
    meals: List[MealItem]
    totalCalories: int
    totalProtein: float
    totalCarbs: float
    totalFat: float

class WeeklyMealPlan(BaseModel):
    monday: DailyMealPlan
    tuesday: DailyMealPlan
    wednesday: DailyMealPlan
    thursday: DailyMealPlan
    friday: DailyMealPlan
    saturday: DailyMealPlan
    sunday: DailyMealPlan

class MealPlanCreate(BaseModel):
    name: Optional[str] = "Weekly Meal Plan"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class MealPlanHistory(BaseModel):
    id: int
    user_id: int
    plan_data: Dict[str, Any]  # This will be a WeeklyMealPlan but stored as JSON
    created_at: datetime
    name: Optional[str] = None
    is_active: bool
    
    class Config:
        orm_mode = True

# Analytics schemas
class DailyNutrition(BaseModel):
    date: str
    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: Optional[float] = None
    sugar: Optional[float] = None

class NutritionSummary(BaseModel):
    start_date: datetime
    end_date: datetime
    avg_calories: float
    avg_protein: float
    avg_carbs: float
    avg_fat: float
    avg_fiber: Optional[float] = None
    avg_sugar: Optional[float] = None
    daily_data: List[DailyNutrition]

class MacronutrientRatios(BaseModel):
    protein_percentage: float
    carbs_percentage: float
    fat_percentage: float

class NutritionInsight(BaseModel):
    category: str
    message: str
    priority: str  # low, medium, high

class NutritionInsights(BaseModel):
    macronutrient_ratios: MacronutrientRatios
    insights: List[NutritionInsight]
    food_recommendations: List[str]

# User goal schemas
class UserGoalBase(BaseModel):
    goal_type: str
    target_value: Optional[float] = None
    current_value: Optional[float] = None
    target_date: Optional[datetime] = None

class UserGoalCreate(UserGoalBase):
    pass

class UserGoal(UserGoalBase):
    id: int
    user_id: int
    start_date: datetime
    is_active: bool
    
    class Config:
        orm_mode = True

# Search schemas
class SearchQuery(BaseModel):
    query: str
    category: Optional[str] = None
    limit: int = 10

# Image recognition schemas
class ImageRecognitionResult(BaseModel):
    food_name: str
    confidence: float
    food_item: Optional[FoodItem] = None
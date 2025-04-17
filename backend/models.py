from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

# Association table for many-to-many relationships
user_food_preference = Table('user_food_preference', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('food_item_id', Integer, ForeignKey('food_items.id'))
)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    dietary_preferences = Column(String, nullable=True)
    height = Column(Float, nullable=True)  # in cm
    weight = Column(Float, nullable=True)  # in kg
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    activity_level = Column(String, nullable=True)
    goals = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    meal_plans = relationship("MealPlan", back_populates="user")
    food_logs = relationship("FoodLog", back_populates="user")
    favorite_foods = relationship("FoodItem", secondary=user_food_preference)

class MealPlan(Base):
    __tablename__ = "meal_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    plan_data = Column(JSON)  # Stores the entire meal plan as JSON
    created_at = Column(DateTime, default=datetime.now)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="meal_plans")

class FoodLog(Base):
    __tablename__ = "food_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    food_name = Column(String)
    meal_type = Column(String)  # breakfast, lunch, dinner, snack
    calories = Column(Float)
    protein = Column(Float)
    carbs = Column(Float)
    fat = Column(Float)
    fiber = Column(Float, nullable=True)
    sugar = Column(Float, nullable=True)
    serving_size = Column(String, nullable=True)
    servings = Column(Float, default=1.0)
    logged_at = Column(DateTime, default=datetime.now)
    food_item_id = Column(Integer, ForeignKey("food_items.id"), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="food_logs")
    food_item = relationship("FoodItem", back_populates="food_logs")

class FoodItem(Base):
    __tablename__ = "food_items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    barcode = Column(String, nullable=True, unique=True, index=True)
    brand = Column(String, nullable=True)
    serving_size = Column(String)
    calories = Column(Float)
    protein = Column(Float)
    carbs = Column(Float)
    fat = Column(Float)
    fiber = Column(Float, nullable=True)
    sugar = Column(Float, nullable=True)
    sodium = Column(Float, nullable=True)
    potassium = Column(Float, nullable=True)
    cholesterol = Column(Float, nullable=True)
    saturated_fat = Column(Float, nullable=True)
    trans_fat = Column(Float, nullable=True)
    vitamin_a = Column(Float, nullable=True)
    vitamin_c = Column(Float, nullable=True)
    calcium = Column(Float, nullable=True)
    iron = Column(Float, nullable=True)
    image_url = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    category = Column(String, nullable=True)
    subcategory = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    food_logs = relationship("FoodLog", back_populates="food_item")

class UserGoal(Base):
    __tablename__ = "user_goals"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    goal_type = Column(String)  # weight_loss, weight_gain, maintain, nutrition
    target_value = Column(Float, nullable=True)  # target weight, calorie intake, etc.
    current_value = Column(Float, nullable=True)  # current weight, calorie intake, etc.
    start_date = Column(DateTime, default=datetime.now)
    target_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User")
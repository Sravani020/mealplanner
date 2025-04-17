from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import uvicorn
from datetime import datetime, timedelta
import os
import numpy as np
import pandas as pd
from io import BytesIO
from PIL import Image
import requests
import logging
import json
from pathlib import Path

# Local imports
from database import get_db, engine
import models
import schemas
from auth import create_access_token, get_current_user, verify_password, get_password_hash
from data_loader import NutritionDataLoader
from recommendations import MealRecommender
from ml_models import FoodRecognitionModel, BarcodeScannerModel

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Meal Planner API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load data
data_path = Path(__file__).parent / "data"

# Initialize nutrition data loader
nutrition_data_loader = NutritionDataLoader(data_dir=data_path)
if not nutrition_data_loader.load_data():
    logger.warning("Failed to load nutrition data, using default values")

# Initialize meal recommender
meal_recommender = MealRecommender(nutrition_data_loader)

# Initialize ML models
food_recognition_model = FoodRecognitionModel(nutrition_data_loader)
barcode_scanner_model = BarcodeScannerModel(nutrition_data_loader)

# Try to load the datasets from the data directory
try:
    # Try to load the datasets from the data directory
    food_nutrition_path = data_path / "food_nutrition.csv"
    healthy_diet_path = data_path / "covid19_healthy_diet.csv"
    
    if food_nutrition_path.exists():
        food_nutrition_data = pd.read_csv(food_nutrition_path)
        logger.info(f"Loaded food nutrition data: {len(food_nutrition_data)} items")
    else:
        logger.warning(f"Food nutrition data not found at {food_nutrition_path}")
        food_nutrition_data = pd.DataFrame({
            'name': ['Apple', 'Banana', 'Chicken Breast', 'Salmon', 'Brown Rice'],
            'calories': [52, 89, 165, 208, 112],
            'protein': [0.3, 1.1, 31, 20, 2.6],
            'carbs': [14, 23, 0, 0, 23],
            'fat': [0.2, 0.3, 3.6, 12, 0.9]
        })
    
    if healthy_diet_path.exists():
        healthy_diet_data = pd.read_csv(healthy_diet_path)
        logger.info(f"Loaded healthy diet data: {len(healthy_diet_data)} items")
    else:
        logger.warning(f"Healthy diet data not found at {healthy_diet_path}")
        healthy_diet_data = pd.DataFrame({
            'country': ['USA', 'Japan', 'Italy', 'Greece', 'India'],
            'diet_pattern': ['Western', 'Asian', 'Mediterranean', 'Mediterranean', 'Plant-based'],
            'avg_calories': [2200, 1900, 2000, 2100, 1800]
        })
    
    # Insert food data into database if it's empty
    def populate_food_database(db: Session = next(get_db())):
        existing_count = db.query(models.FoodItem).count()
        if existing_count == 0:
            logger.info("Populating food database with initial data...")
            
            # Take first 100 items to avoid loading too much data initially
            for _, row in food_nutrition_data.head(100).iterrows():
                food_item = models.FoodItem(
                    name=row['name'],
                    calories=row['calories'],
                    protein=row.get('protein', 0),
                    carbs=row.get('carbs', 0),
                    fat=row.get('fat', 0),
                    serving_size="1 serving",
                    is_verified=True
                )
                db.add(food_item)
            
            db.commit()
            logger.info(f"Added {100} food items to database")
    
    # Populate database in the background
    import threading
    threading.Thread(target=populate_food_database).start()
    
except Exception as e:
    logger.error(f"Error loading data: {e}")
    # Create sample data
    food_nutrition_data = pd.DataFrame({
        'name': ['Apple', 'Banana', 'Chicken Breast', 'Salmon', 'Brown Rice'],
        'calories': [52, 89, 165, 208, 112],
        'protein': [0.3, 1.1, 31, 20, 2.6],
        'carbs': [14, 23, 0, 0, 23],
        'fat': [0.2, 0.3, 3.6, 12, 0.9]
    })
    healthy_diet_data = pd.DataFrame({
        'country': ['USA', 'Japan', 'Italy', 'Greece', 'India'],
        'diet_pattern': ['Western', 'Asian', 'Mediterranean', 'Mediterranean', 'Plant-based'],
        'avg_calories': [2200, 1900, 2000, 2100, 1800]
    })

# Authentication routes
@app.post("/auth/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Log the registration
    logger.info(f"New user registered: {user.email}")
    
    return db_user

@app.post("/auth/login", response_model=schemas.Token)
def login(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_credentials.email).first()
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login timestamp
    user.last_login = datetime.now()
    db.commit()
    
    # Create access token
    access_token = create_access_token(data={"sub": user.email})
    
    logger.info(f"User logged in: {user.email}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name
        }
    }

# User profile routes
@app.get("/users/me", response_model=schemas.UserResponse)
def get_current_user_profile(current_user: models.User = Depends(get_current_user)):
    return current_user

@app.put("/users/me", response_model=schemas.UserResponse)
def update_user_profile(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Update user profile
    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    
    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    
    if user_update.dietary_preferences is not None:
        user.dietary_preferences = user_update.dietary_preferences
    
    if user_update.height is not None:
        user.height = user_update.height
    
    if user_update.weight is not None:
        user.weight = user_update.weight
    
    if user_update.age is not None:
        user.age = user_update.age
    
    if user_update.gender is not None:
        user.gender = user_update.gender
    
    if user_update.activity_level is not None:
        user.activity_level = user_update.activity_level
    
    if user_update.goals is not None:
        user.goals = user_update.goals
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"User profile updated: {user.email}")
    
    return user

# Meal Planning Routes
@app.get("/meal-plan/generate", response_model=schemas.WeeklyMealPlan)
def generate_meal_plan(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Generating meal plan for user: {current_user.email}")
    
    # In a real app, this would use AI to generate personalized meal plans
    # For this demo, we'll return sample data
    
    # Get user preferences and requirements
    user_preferences = current_user.dietary_preferences or ""
    is_vegetarian = "vegetarian" in user_preferences.lower()
    
    # Calculate daily calorie needs based on user profile (simplified)
    # In a real app, you would use formulas like Mifflin-St Jeor
    base_calories = 2000  # default
    if current_user.gender and current_user.weight and current_user.height and current_user.age:
        if current_user.gender.lower() == "male":
            base_calories = 10 * current_user.weight + 6.25 * current_user.height - 5 * current_user.age + 5
        else:
            base_calories = 10 * current_user.weight + 6.25 * current_user.height - 5 * current_user.age - 161
    
    # Adjust for activity level
    activity_multipliers = {
        "sedentary": 1.2,
        "lightly_active": 1.375,
        "moderately_active": 1.55,
        "very_active": 1.725,
        "extra_active": 1.9
    }
    
    activity_level = current_user.activity_level or "moderately_active"
    daily_calories = int(base_calories * activity_multipliers.get(activity_level, 1.55))
    
    # Adjust for goal
    if current_user.goals:
        if "weight_loss" in current_user.goals.lower():
            daily_calories = int(daily_calories * 0.8)  # 20% deficit
        elif "weight_gain" in current_user.goals.lower():
            daily_calories = int(daily_calories * 1.15)  # 15% surplus
    
    # Filter food items based on preferences and create meal plan
    filtered_foods = food_nutrition_data
    if is_vegetarian:
        # This is simplified - in a real app you would have proper food categories
        meat_keywords = ['chicken', 'beef', 'pork', 'turkey', 'fish', 'salmon']
        filtered_foods = filtered_foods[~filtered_foods['name'].str.lower().str.contains('|'.join(meat_keywords))]
    
    # Generate weekly meal plan
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    meal_types = ["breakfast", "lunch", "dinner", "snack"]
    
    weekly_plan = {}
    
    for day in days:
        daily_meals = []
        total_calories = 0
        total_protein = 0
        total_carbs = 0
        total_fat = 0
        
        for meal_type in meal_types:
            # In a real app, you would have more sophisticated meal selection logic
            # and proper distribution of calories across meals
            if meal_type == "breakfast":
                meal_calories = int(daily_calories * 0.25)
            elif meal_type == "lunch":
                meal_calories = int(daily_calories * 0.3)
            elif meal_type == "dinner":
                meal_calories = int(daily_calories * 0.3)
            else:  # snack
                meal_calories = int(daily_calories * 0.15)
            
            # Sample random meals (simplified)
            sample_food = filtered_foods.sample(1).iloc[0]
            
            # Calculate serving size to match target calories
            servings = meal_calories / max(sample_food['calories'], 1)
            
            meal = {
                "type": meal_type,
                "name": sample_food['name'],
                "calories": int(sample_food['calories'] * servings),
                "protein": round(sample_food.get('protein', 0) * servings, 1),
                "carbs": round(sample_food.get('carbs', 0) * servings, 1),
                "fat": round(sample_food.get('fat', 0) * servings, 1),
                "servings": round(servings, 2),
                "recipe_link": f"https://example.com/recipes/{sample_food['name'].lower().replace(' ', '-')}"
            }
            
            daily_meals.append(meal)
            total_calories += meal["calories"]
            total_protein += meal["protein"]
            total_carbs += meal["carbs"]
            total_fat += meal["fat"]
        
        weekly_plan[day] = {
            "meals": daily_meals,
            "totalCalories": total_calories,
            "totalProtein": round(total_protein, 1),
            "totalCarbs": round(total_carbs, 1),
            "totalFat": round(total_fat, 1)
        }
    
    # Save the meal plan to the database
    db_meal_plan = models.MealPlan(
        user_id=current_user.id,
        plan_data=weekly_plan,
        created_at=datetime.now(),
        name="Weekly Meal Plan",
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=7),
        is_active=True
    )
    db.add(db_meal_plan)
    db.commit()
    
    logger.info(f"Meal plan generated and saved for user: {current_user.email}")
    
    return weekly_plan

@app.post("/meal-plan/create", response_model=schemas.MealPlanHistory)
def create_meal_plan(
    meal_plan_data: schemas.MealPlanCreate,
    weekly_plan: schemas.WeeklyMealPlan,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Save custom meal plan to database
    start_date = meal_plan_data.start_date or datetime.now()
    end_date = meal_plan_data.end_date or (start_date + timedelta(days=7))
    
    db_meal_plan = models.MealPlan(
        user_id=current_user.id,
        plan_data=json.loads(weekly_plan.json()),  # Convert pydantic model to dict
        created_at=datetime.now(),
        name=meal_plan_data.name,
        start_date=start_date,
        end_date=end_date,
        is_active=True
    )
    
    db.add(db_meal_plan)
    db.commit()
    db.refresh(db_meal_plan)
    
    logger.info(f"Custom meal plan created by user: {current_user.email}")
    
    return db_meal_plan

@app.get("/meal-plan/history", response_model=List[schemas.MealPlanHistory])
def get_meal_plan_history(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 10
):
    meal_plans = db.query(models.MealPlan).filter(
        models.MealPlan.user_id == current_user.id
    ).order_by(models.MealPlan.created_at.desc()).offset(skip).limit(limit).all()
    
    return meal_plans

@app.get("/meal-plan/{meal_plan_id}", response_model=schemas.MealPlanHistory)
def get_meal_plan(
    meal_plan_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    meal_plan = db.query(models.MealPlan).filter(
        models.MealPlan.id == meal_plan_id,
        models.MealPlan.user_id == current_user.id
    ).first()
    
    if not meal_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal plan not found"
        )
    
    return meal_plan

@app.delete("/meal-plan/{meal_plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meal_plan(
    meal_plan_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    meal_plan = db.query(models.MealPlan).filter(
        models.MealPlan.id == meal_plan_id,
        models.MealPlan.user_id == current_user.id
    ).first()
    
    if not meal_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal plan not found"
        )
    
    db.delete(meal_plan)
    db.commit()
    
    logger.info(f"Meal plan {meal_plan_id} deleted by user: {current_user.email}")
    
    return

# Food Recognition and Logging Routes
@app.get("/food/barcode/{barcode}")
def get_food_by_barcode(
    barcode: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if barcode exists in database
    food_item = db.query(models.FoodItem).filter(
        models.FoodItem.barcode == barcode
    ).first()
    
    if food_item:
        logger.info(f"Food item found by barcode: {barcode}")
        return food_item
    
    # Look up barcode using the barcode scanner model
    barcode_result = barcode_scanner_model.lookup_barcode(barcode)
    
    if barcode_result:
        # Save to database for future lookups
        new_food = {
            "name": barcode_result["food_name"],
            "barcode": barcode,
            "brand": "Detected Brand",
            "serving_size": "1 serving",
            "calories": float(barcode_result["nutrition"]["calories"]),
            "protein": float(barcode_result["nutrition"]["protein"]),
            "carbs": float(barcode_result["nutrition"]["carbohydrates"]),
            "fat": float(barcode_result["nutrition"]["fats"]),
            "fiber": float(barcode_result["nutrition"].get("fiber", 0)),
            "sugar": float(barcode_result["nutrition"].get("sugars", 0)),
            "sodium": float(barcode_result["nutrition"].get("sodium", 0)),
            "image_url": f"https://example.com/images/{barcode_result['food_name'].lower().replace(' ', '-')}.jpg"
        }
        
        db_food_item = models.FoodItem(**new_food)
        db.add(db_food_item)
        db.commit()
        db.refresh(db_food_item)
        
        logger.info(f"Created new food item from barcode: {barcode}")
        
        return db_food_item
    
    # If barcode not found, return a mock response
    logger.warning(f"Barcode not found: {barcode}, returning generic response")
    sample_food = nutrition_data_loader.search_foods("chicken", 1)[0] if nutrition_data_loader.search_foods("chicken", 1) else {"label": "Generic Food", "calories": 200, "protein": 10, "carbohydrates": 20, "fats": 10}
    
    # Create a new food item
    new_food = {
        "name": sample_food.get("label", "Generic Food"),
        "brand": "Generic Brand",
        "serving_size": "1 serving",
        "calories": float(sample_food.get("calories", 200)),
        "protein": float(sample_food.get("protein", 10)),
        "carbs": float(sample_food.get("carbohydrates", 20)),
        "fat": float(sample_food.get("fats", 10)),
        "fiber": 2.0,
        "sugar": 5.0,
        "sodium": 50,
        "barcode": barcode,
        "image_url": f"https://example.com/images/generic-food.jpg"
    }
    
    db_food_item = models.FoodItem(**new_food)
    db.add(db_food_item)
    db.commit()
    db.refresh(db_food_item)
    
    logger.info(f"Created generic food item for unknown barcode: {barcode}")
    
    return db_food_item

@app.post("/food/image-recognition", response_model=List[dict])
async def recognize_food_from_image(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Processing food image recognition request")
    
    try:
        contents = await file.read()
        
        # Use the food recognition model to predict food items
        predictions = food_recognition_model.predict(contents)
        
        if not predictions:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not process image"
            )
        
        return predictions
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/food/log", response_model=schemas.FoodLog)
def log_food(
    food_log: schemas.FoodLogCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Create new food log entry
    db_food_log = models.FoodLog(
        user_id=current_user.id,
        food_name=food_log.food_name,
        meal_type=food_log.meal_type,
        calories=food_log.calories,
        protein=food_log.protein,
        carbs=food_log.carbs,
        fat=food_log.fat,
        fiber=food_log.fiber,
        sugar=food_log.sugar,
        serving_size=food_log.serving_size,
        servings=food_log.servings,
        food_item_id=food_log.food_item_id,
        logged_at=food_log.logged_at or datetime.now()
    )
    
    db.add(db_food_log)
    db.commit()
    db.refresh(db_food_log)
    
    logger.info(f"Food logged: {food_log.food_name} for user: {current_user.email}")
    
    return db_food_log

@app.get("/food/logs", response_model=List[schemas.FoodLog])
def get_food_logs(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    meal_type: Optional[str] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    # Default to today if dates not provided
    if not start_date:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if not end_date:
        end_date = start_date + timedelta(days=1)
    
    # Build query
    query = db.query(models.FoodLog).filter(
        models.FoodLog.user_id == current_user.id,
        models.FoodLog.logged_at >= start_date,
        models.FoodLog.logged_at < end_date
    )
    
    # Add meal type filter if provided
    if meal_type:
        query = query.filter(models.FoodLog.meal_type == meal_type)
    
    # Execute query with pagination
    food_logs = query.order_by(models.FoodLog.logged_at).offset(skip).limit(limit).all()
    
    logger.info(f"Retrieved {len(food_logs)} food logs for user: {current_user.email}")
    
    return food_logs

@app.get("/food/log/{log_id}", response_model=schemas.FoodLog)
def get_food_log(
    log_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    food_log = db.query(models.FoodLog).filter(
        models.FoodLog.id == log_id,
        models.FoodLog.user_id == current_user.id
    ).first()
    
    if not food_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food log not found"
        )
    
    return food_log

@app.delete("/food/log/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_food_log(
    log_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    food_log = db.query(models.FoodLog).filter(
        models.FoodLog.id == log_id,
        models.FoodLog.user_id == current_user.id
    ).first()
    
    if not food_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food log not found"
        )
    
    db.delete(food_log)
    db.commit()
    
    logger.info(f"Food log {log_id} deleted by user: {current_user.email}")
    
    return

# Food Search Routes
@app.get("/food/search", response_model=List[schemas.FoodItem])
def search_food(
    query: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10
):
    # Search for food in the database
    search_results = db.query(models.FoodItem).filter(
        models.FoodItem.name.ilike(f"%{query}%")
    ).limit(limit).all()
    
    if search_results:
        logger.info(f"Found {len(search_results)} database results for search: {query}")
        return search_results
    
    # If no results in database, search the CSV data
    filtered_foods = food_nutrition_data[food_nutrition_data['name'].str.contains(query, case=False, na=False)]
    
    # If still no results, return empty list
    if filtered_foods.empty:
        logger.info(f"No results for search: {query}")
        return []
    
    # Convert matched foods to FoodItem objects and save to database
    top_results = filtered_foods.head(limit)
    saved_items = []
    
    for _, row in top_results.iterrows():
        food_item = models.FoodItem(
            name=row['name'],
            calories=float(row['calories']),
            protein=float(row.get('protein', 0)),
            carbs=float(row.get('carbs', 0)),
            fat=float(row.get('fat', 0)),
            serving_size="1 serving",
            is_verified=True
        )
        db.add(food_item)
        saved_items.append(food_item)
    
    db.commit()
    
    # Refresh to get IDs
    for item in saved_items:
        db.refresh(item)
    
    logger.info(f"Added {len(saved_items)} new food items from search: {query}")
    
    return saved_items

# Nutrition Analytics Routes
@app.get("/analytics/nutrition-summary", response_model=schemas.NutritionSummary)
def get_nutrition_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Default to last 7 days if dates not provided
    if not end_date:
        end_date = datetime.now().replace(hour=23, minute=59, second=59)
    if not start_date:
        start_date = end_date - timedelta(days=7)
    
    # Get food logs for the date range
    food_logs = db.query(models.FoodLog).filter(
        models.FoodLog.user_id == current_user.id,
        models.FoodLog.logged_at >= start_date,
        models.FoodLog.logged_at <= end_date
    ).all()
    
    # Process data for summary
    days_in_range = (end_date - start_date).days + 1
    
    # Initialize daily data
    daily_data = {}
    for i in range(days_in_range):
        current_date = (start_date + timedelta(days=i)).date()
        daily_data[current_date] = {
            "date": current_date.isoformat(),
            "calories": 0,
            "protein": 0,
            "carbs": 0,
            "fat": 0,
            "fiber": 0,
            "sugar": 0
        }
    
    # Fill in food log data
    for log in food_logs:
        log_date = log.logged_at.date()
        if log_date in daily_data:
            daily_data[log_date]["calories"] += log.calories
            daily_data[log_date]["protein"] += log.protein
            daily_data[log_date]["carbs"] += log.carbs
            daily_data[log_date]["fat"] += log.fat
            daily_data[log_date]["fiber"] += log.fiber or 0
            daily_data[log_date]["sugar"] += log.sugar or 0
    
    # Calculate averages
    total_calories = sum(day["calories"] for day in daily_data.values())
    total_protein = sum(day["protein"] for day in daily_data.values())
    total_carbs = sum(day["carbs"] for day in daily_data.values())
    total_fat = sum(day["fat"] for day in daily_data.values())
    total_fiber = sum(day["fiber"] for day in daily_data.values())
    total_sugar = sum(day["sugar"] for day in daily_data.values())
    
    avg_calories = round(total_calories / days_in_range, 1)
    avg_protein = round(total_protein / days_in_range, 1)
    avg_carbs = round(total_carbs / days_in_range, 1)
    avg_fat = round(total_fat / days_in_range, 1)
    avg_fiber = round(total_fiber / days_in_range, 1)
    avg_sugar = round(total_sugar / days_in_range, 1)
    
    logger.info(f"Generated nutrition summary for user: {current_user.email}")
    
    return {
        "start_date": start_date,
        "end_date": end_date,
        "avg_calories": avg_calories,
        "avg_protein": avg_protein,
        "avg_carbs": avg_carbs,
        "avg_fat": avg_fat,
        "avg_fiber": avg_fiber,
        "avg_sugar": avg_sugar,
        "daily_data": list(daily_data.values())
    }

@app.get("/analytics/nutrition-insights", response_model=schemas.NutritionInsights)
def get_nutrition_insights(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # In a real app, this would analyze eating patterns
    # For demo purposes, we'll return sample insights
    
    # Get user's recent food logs (last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    food_logs = db.query(models.FoodLog).filter(
        models.FoodLog.user_id == current_user.id,
        models.FoodLog.logged_at >= start_date,
        models.FoodLog.logged_at <= end_date
    ).all()
    
    # Calculate macronutrient ratios
    total_calories = sum(log.calories for log in food_logs) if food_logs else 0
    total_protein = sum(log.protein for log in food_logs) if food_logs else 0
    total_carbs = sum(log.carbs for log in food_logs) if food_logs else 0
    total_fat = sum(log.fat for log in food_logs) if food_logs else 0
    
    if total_calories > 0:
        protein_pct = round((total_protein * 4 / total_calories) * 100, 1)
        carbs_pct = round((total_carbs * 4 / total_calories) * 100, 1)
        fat_pct = round((total_fat * 9 / total_calories) * 100, 1)
    else:
        protein_pct = carbs_pct = fat_pct = 0
    
    # Generate sample insights
    insights = []
    
    # Protein intake insights
    if protein_pct < 15:
        insights.append({
            "category": "protein",
            "message": "Your protein intake is below recommended levels. Consider adding more lean protein sources like chicken, fish, tofu, or legumes to your diet.",
            "priority": "high"
        })
    elif protein_pct > 35:
        insights.append({
            "category": "protein",
            "message": "Your protein intake is relatively high. While protein is important, ensure you're getting a balanced diet with adequate carbs and healthy fats.",
            "priority": "medium"
        })
    
    # Carb intake insights
    if carbs_pct < 30:
        insights.append({
            "category": "carbs",
            "message": "Your carbohydrate intake is relatively low. Consider adding more healthy carbs like whole grains, fruits, and vegetables for sustained energy.",
            "priority": "medium"
        })
    elif carbs_pct > 65:
        insights.append({
            "category": "carbs",
            "message": "Your diet is very high in carbohydrates. Try to include more protein and healthy fats for better macronutrient balance.",
            "priority": "high"
        })
    
    # Fat intake insights
    if fat_pct < 20:
        insights.append({
            "category": "fat",
            "message": "Your fat intake is lower than recommended. Healthy fats from nuts, avocados, olive oil, and fatty fish are important for hormone production and vitamin absorption.",
            "priority": "medium"
        })
    elif fat_pct > 40:
        insights.append({
            "category": "fat",
            "message": "Your fat intake is higher than recommended. Focus on healthy fat sources and consider reducing overall fat consumption slightly.",
            "priority": "medium"
        })
    
    # Add generic insights if we don't have enough data
    if not food_logs or len(food_logs) < 10:
        insights = [
            {
                "category": "general",
                "message": "Keep logging your meals regularly to receive personalized nutrition insights!",
                "priority": "medium"
            },
            {
                "category": "hydration",
                "message": "Don't forget to stay hydrated by drinking water throughout the day.",
                "priority": "medium"
            }
        ]
    
    # Food recommendations based on nutrition analysis
    recommendations = []
    
    if protein_pct < 20:
        recommendations.append("Greek yogurt (high protein, low fat dairy)")
        recommendations.append("Chicken breast (lean protein source)")
        recommendations.append("Lentils (plant-based protein and fiber)")
    
    if carbs_pct > 60:
        recommendations.append("Replace refined grains with whole grains like brown rice")
        recommendations.append("Include more vegetables in place of starchy sides")
    
    if fat_pct < 20:
        recommendations.append("Avocados (healthy monounsaturated fats)")
        recommendations.append("Nuts and seeds (healthy fats and protein)")
        recommendations.append("Olive oil (healthy cooking oil rich in antioxidants)")
    
    # Add some generic recommendations if list is empty
    if not recommendations:
        recommendations = [
            "Aim for a colorful plate with a variety of fruits and vegetables",
            "Include lean proteins, healthy fats, and complex carbohydrates in each meal",
            "Stay hydrated by drinking water throughout the day"
        ]
    
    logger.info(f"Generated nutrition insights for user: {current_user.email}")
    
    return {
        "macronutrient_ratios": {
            "protein_percentage": protein_pct,
            "carbs_percentage": carbs_pct,
            "fat_percentage": fat_pct
        },
        "insights": insights,
        "food_recommendations": recommendations
    }

# User Goals Routes
@app.post("/goals", response_model=schemas.UserGoal)
def create_user_goal(
    goal: schemas.UserGoalCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Create new goal
    db_goal = models.UserGoal(
        user_id=current_user.id,
        goal_type=goal.goal_type,
        target_value=goal.target_value,
        current_value=goal.current_value,
        start_date=datetime.now(),
        target_date=goal.target_date,
        is_active=True
    )
    
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    
    logger.info(f"Goal created for user: {current_user.email}, type: {goal.goal_type}")
    
    return db_goal

@app.get("/goals", response_model=List[schemas.UserGoal])
def get_user_goals(
    active_only: bool = True,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Query goals
    query = db.query(models.UserGoal).filter(models.UserGoal.user_id == current_user.id)
    
    if active_only:
        query = query.filter(models.UserGoal.is_active == True)
    
    goals = query.order_by(models.UserGoal.start_date.desc()).all()
    
    return goals

@app.put("/goals/{goal_id}", response_model=schemas.UserGoal)
def update_user_goal(
    goal_id: int,
    goal_update: schemas.UserGoalCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get goal
    goal = db.query(models.UserGoal).filter(
        models.UserGoal.id == goal_id,
        models.UserGoal.user_id == current_user.id
    ).first()
    
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found"
        )
    
    # Update goal
    goal.goal_type = goal_update.goal_type
    goal.target_value = goal_update.target_value
    goal.current_value = goal_update.current_value
    goal.target_date = goal_update.target_date
    
    db.commit()
    db.refresh(goal)
    
    logger.info(f"Goal {goal_id} updated for user: {current_user.email}")
    
    return goal

@app.delete("/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_goal(
    goal_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get goal
    goal = db.query(models.UserGoal).filter(
        models.UserGoal.id == goal_id,
        models.UserGoal.user_id == current_user.id
    ).first()
    
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Goal not found"
        )
    
    # Delete goal
    db.delete(goal)
    db.commit()
    
    logger.info(f"Goal {goal_id} deleted for user: {current_user.email}")
    
    return

# Nutrition Data API Routes
@app.get("/nutrition/foods", response_model=List[str])
def get_food_items(current_user: models.User = Depends(get_current_user)):
    """Get a list of all available food items"""
    return nutrition_data_loader.get_food_items()

@app.get("/nutrition/food/{food_name}")
def get_food_nutrition(
    food_name: str,
    current_user: models.User = Depends(get_current_user)
):
    """Get nutritional information for a specific food"""
    food_data = nutrition_data_loader.get_food_nutrition(food_name)
    if not food_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food not found"
        )
    return food_data

@app.get("/nutrition/search")
def search_foods(
    query: str,
    limit: int = 10,
    current_user: models.User = Depends(get_current_user)
):
    """Search for foods by name"""
    return nutrition_data_loader.search_foods(query, limit)

@app.get("/nutrition/countries")
def get_countries(current_user: models.User = Depends(get_current_user)):
    """Get a list of all countries with nutrition data"""
    return nutrition_data_loader.get_countries()

@app.get("/nutrition/country/{country_name}")
def get_country_nutrition(
    country_name: str,
    current_user: models.User = Depends(get_current_user)
):
    """Get nutritional data for a specific country"""
    country_data = nutrition_data_loader.get_country_nutrition(country_name)
    if not country_data['data']:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Country not found"
        )
    return country_data

@app.get("/nutrition/categories")
def get_food_categories(current_user: models.User = Depends(get_current_user)):
    """Get all food categories and descriptions"""
    return nutrition_data_loader.get_food_categories()

# Enhanced Meal Planning with Nutrition Data
@app.get("/meal-plan/ai-generate")
def generate_ai_meal_plan(
    days: int = 7,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate an AI-powered meal plan based on nutritional data and user profile"""
    # Get user profile as dictionary
    user_dict = {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "dietary_preferences": current_user.dietary_preferences,
        "height": current_user.height,
        "weight": current_user.weight,
        "age": current_user.age,
        "gender": current_user.gender,
        "activity_level": current_user.activity_level,
        "goals": current_user.goals
    }
    
    # Generate meal plan
    meal_plan = meal_recommender.generate_meal_plan(user_dict, days)
    
    if not meal_plan:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate meal plan"
        )
    
    # Save the meal plan to the database
    db_meal_plan = models.MealPlan(
        user_id=current_user.id,
        plan_data=meal_plan,
        created_at=datetime.now(),
        name="AI-Generated Meal Plan",
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=days),
        is_active=True
    )
    db.add(db_meal_plan)
    db.commit()
    
    logger.info(f"AI-Generated meal plan created for user: {current_user.email}")
    
    return meal_plan

@app.get("/nutrition/recommendations")
def get_nutrition_recommendations(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get personalized nutrition recommendations based on user profile"""
    # Get user profile as dictionary
    user_dict = {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "dietary_preferences": current_user.dietary_preferences,
        "height": current_user.height,
        "weight": current_user.weight,
        "age": current_user.age,
        "gender": current_user.gender,
        "activity_level": current_user.activity_level,
        "goals": current_user.goals
    }
    
    return nutrition_data_loader.get_healthy_diet_recommendations(user_dict)

@app.get("/nutrition/insights")
def get_enhanced_nutrition_insights(
    days: int = 30,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get enhanced nutrition insights based on food logs and nutritional data"""
    # Get recent food logs
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    food_logs = db.query(models.FoodLog).filter(
        models.FoodLog.user_id == current_user.id,
        models.FoodLog.logged_at >= start_date,
        models.FoodLog.logged_at <= end_date
    ).all()
    
    # Get user profile as dictionary
    user_dict = {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "dietary_preferences": current_user.dietary_preferences,
        "height": current_user.height,
        "weight": current_user.weight,
        "age": current_user.age,
        "gender": current_user.gender,
        "activity_level": current_user.activity_level,
        "goals": current_user.goals
    }
    
    # Generate insights
    insights = meal_recommender.get_nutrition_insights(food_logs, user_dict)
    
    return insights

# Health endpoint for monitoring
@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
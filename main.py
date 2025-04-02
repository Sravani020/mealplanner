from fastapi import FastAPI, UploadFile, File
from food_recognition import predict_food
from barcode_scanner import scan_barcode
from nutrition import get_nutrition

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "AI Meal Planner API"}

@app.post("/predict-food/")
async def recognize_food(image: UploadFile = File(...)):
    file_path = f"temp/{image.filename}"
    with open(file_path, "wb") as buffer:
        buffer.write(image.file.read())
    
    result = predict_food(file_path)
    return {"prediction": result}

@app.post("/scan-barcode/")
async def barcode_scan(image: UploadFile = File(...)):
    file_path = f"temp/{image.filename}"
    with open(file_path, "wb") as buffer:
        buffer.write(image.file.read())
    
    result = scan_barcode(file_path)
    return {"barcode": result}

@app.get("/nutrition/{food_name}")
def nutrition_info(food_name: str):
    result = get_nutrition(food_name)
    return {"nutrition": result}

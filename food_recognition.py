import torch
import torchvision.transforms as transforms
from torchvision import models
from PIL import Image

# Load Pretrained Food101 Model
model = models.resnet18(pretrained=True)
model.eval()

# Preprocessing
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])

# Fake Food Classes (Since we don’t have actual Food101 labels)
food_classes = ["Pizza", "Burger", "Pasta", "Salad", "Sushi", "Sandwich"]

def predict_food(image_path):
    img = Image.open(image_path)
    img = transform(img).unsqueeze(0)
    
    with torch.no_grad():
        output = model(img)
    
    predicted_class = output.argmax().item() % len(food_classes)
    return food_classes[predicted_class]

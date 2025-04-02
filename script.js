function navigateTo(screen) {
    document.getElementById('home-screen').classList.add('hidden');
    document.getElementById('meal-planner-screen').classList.add('hidden');

    if (screen === 'home') {
        document.getElementById('home-screen').classList.remove('hidden');
    } else if (screen === 'meal-planner') {
        document.getElementById('meal-planner-screen').classList.remove('hidden');
    }
}

function generateMeal() {
    const mealType = document.getElementById('meal-type').value;
    const dietPreference = document.getElementById('diet-preference').value;

    let suggestedMeal = '';

    if (mealType === 'Breakfast' && dietPreference === 'Vegetarian') {
        suggestedMeal = 'Oatmeal with Banana & Nuts';
    } else if (mealType === 'Lunch' && dietPreference === 'Vegan') {
        suggestedMeal = 'Quinoa & Avocado Salad';
    } else if (mealType === 'Dinner' && dietPreference === 'High Protein') {
        suggestedMeal = 'Grilled Salmon with Steamed Veggies';
    } else {
        suggestedMeal = 'Custom Healthy Meal';
    }

    document.getElementById('suggested-meal').innerText = suggestedMeal;
    document.getElementById('meal-suggestion').classList.remove('hidden');
}

function openBarcodeScanner() {
    document.getElementById('barcode-input').click();
}

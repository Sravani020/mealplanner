// app/(app)/food-details/[id].js
import { useState, useEffect, useContext } from 'react';
import { 
  View, Text, StyleSheet, ScrollView, Image, TouchableOpacity, 
  ActivityIndicator, Alert 
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { AuthContext } from '../../../context/AuthContext';
import { API_URL } from '../../../config';

export default function FoodDetails() {
  const { id } = useLocalSearchParams();
  const [food, setFood] = useState(null);
  const [loading, setLoading] = useState(true);
  const { authState } = useContext(AuthContext);
  const router = useRouter();

  useEffect(() => {
    const fetchFoodDetails = async () => {
      try {
        setLoading(true);
        const response = await fetch(`${API_URL}/food/${id}`, {
          headers: {
            'Authorization': `Bearer ${authState.token}`,
          },
        });
        
        if (!response.ok) {
          throw new Error('Failed to fetch food details');
        }
        
        const data = await response.json();
        setFood(data);
      } catch (error) {
        console.error('Error fetching food details:', error);
        Alert.alert('Error', 'Failed to load food details');
        router.back();
      } finally {
        setLoading(false);
      }
    };

    fetchFoodDetails();
  }, [id, authState.token]);

  const handleLogFood = () => {
    // Navigate to food log screen with pre-filled data
    router.navigate({
      pathname: '/food-log',
      params: {
        food_id: food.id,
        food_name: food.name,
        calories: food.calories,
        protein: food.protein,
        carbs: food.carbs,
        fat: food.fat,
      },
    });
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#4CAF50" />
        <Text style={styles.loadingText}>Loading food details...</Text>
      </View>
    );
  }

  if (!food) {
    return (
      <View style={styles.errorContainer}>
        <Ionicons name="alert-circle-outline" size={60} color="#FF5252" />
        <Text style={styles.errorText}>Failed to load food details</Text>
        <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
          <Text style={styles.backButtonText}>Go Back</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      {/* Food Image Header */}
      {food.image_url ? (
        <Image source={{ uri: food.image_url }} style={styles.foodImage} />
      ) : (
        <View style={styles.foodImagePlaceholder}>
          <Ionicons name="fast-food-outline" size={60} color="#ccc" />
        </View>
      )}
      
      {/* Food Basic Info */}
      <View style={styles.infoContainer}>
        <Text style={styles.foodName}>{food.name}</Text>
        
        {food.brand && (
          <Text style={styles.foodBrand}>{food.brand}</Text>
        )}
        
        <View style={styles.servingInfo}>
          <Text style={styles.servingText}>Serving Size: {food.serving_size}</Text>
        </View>
        
        <View style={styles.badgesContainer}>
          {food.is_verified && (
            <View style={styles.verifiedBadge}>
              <Ionicons name="checkmark-circle" size={14} color="#4CAF50" />
              <Text style={styles.verifiedText}>Verified</Text>
            </View>
          )}
          
          {food.category && (
            <View style={styles.categoryBadge}>
              <Text style={styles.categoryText}>{food.category}</Text>
            </View>
          )}
        </View>
      </View>
      
      {/* Nutrition Summary */}
      <View style={styles.nutritionSummary}>
        <View style={styles.nutrientContainer}>
          <Text style={styles.nutrientValue}>{Math.round(food.calories)}</Text>
          <Text style={styles.nutrientLabel}>Calories</Text>
        </View>
        
        <View style={styles.verticalDivider} />
        
        <View style={styles.nutrientContainer}>
          <Text style={styles.nutrientValue}>{food.protein}g</Text>
          <Text style={styles.nutrientLabel}>Protein</Text>
        </View>
        
        <View style={styles.verticalDivider} />
        
        <View style={styles.nutrientContainer}>
          <Text style={styles.nutrientValue}>{food.carbs}g</Text>
          <Text style={styles.nutrientLabel}>Carbs</Text>
        </View>
        
        <View style={styles.verticalDivider} />
        
        <View style={styles.nutrientContainer}>
          <Text style={styles.nutrientValue}>{food.fat}g</Text>
          <Text style={styles.nutrientLabel}>Fat</Text>
        </View>
      </View>
      
      {/* Detailed Nutrition Information */}
      <View style={styles.detailedNutrition}>
        <Text style={styles.sectionTitle}>Nutrition Facts</Text>
        
        <View style={styles.nutritionTable}>
          <View style={styles.nutritionRow}>
            <Text style={styles.nutritionLabel}>Calories</Text>
            <Text style={styles.nutritionValue}>{Math.round(food.calories)}</Text>
          </View>
          
          <View style={styles.divider} />
          
          <View style={styles.nutritionRow}>
            <Text style={styles.nutritionLabel}>Total Fat</Text>
            <Text style={styles.nutritionValue}>{food.fat}g</Text>
          </View>
          
          {food.saturated_fat !== null && food.saturated_fat !== undefined && (
            <View style={styles.subNutritionRow}>
              <Text style={styles.subNutritionLabel}>Saturated Fat</Text>
              <Text style={styles.nutritionValue}>{food.saturated_fat}g</Text>
            </View>
          )}
          
          {food.trans_fat !== null && food.trans_fat !== undefined && (
            <View style={styles.subNutritionRow}>
              <Text style={styles.subNutritionLabel}>Trans Fat</Text>
              <Text style={styles.nutritionValue}>{food.trans_fat}g</Text>
            </View>
          )}
          
          <View style={styles.divider} />
          
          <View style={styles.nutritionRow}>
            <Text style={styles.nutritionLabel}>Total Carbs</Text>
            <Text style={styles.nutritionValue}>{food.carbs}g</Text>
          </View>
          
          {food.fiber !== null && food.fiber !== undefined && (
            <View style={styles.subNutritionRow}>
              <Text style={styles.subNutritionLabel}>Dietary Fiber</Text>
              <Text style={styles.nutritionValue}>{food.fiber}g</Text>
            </View>
          )}
          
          {food.sugar !== null && food.sugar !== undefined && (
            <View style={styles.subNutritionRow}>
              <Text style={styles.subNutritionLabel}>Sugars</Text>
              <Text style={styles.nutritionValue}>{food.sugar}g</Text>
            </View>
          )}
          
          <View style={styles.divider} />
          
          <View style={styles.nutritionRow}>
            <Text style={styles.nutritionLabel}>Protein</Text>
            <Text style={styles.nutritionValue}>{food.protein}g</Text>
          </View>
          
          <View style={styles.divider} />
          
          {food.sodium !== null && food.sodium !== undefined && (
            <>
              <View style={styles.nutritionRow}>
                <Text style={styles.nutritionLabel}>Sodium</Text>
                <Text style={styles.nutritionValue}>{food.sodium}mg</Text>
              </View>
              <View style={styles.divider} />
            </>
          )}
          
          {food.cholesterol !== null && food.cholesterol !== undefined && (
            <>
              <View style={styles.nutritionRow}>
                <Text style={styles.nutritionLabel}>Cholesterol</Text>
                <Text style={styles.nutritionValue}>{food.cholesterol}mg</Text>
              </View>
              <View style={styles.divider} />
            </>
          )}
        </View>
      </View>
      
      {/* Action Buttons */}
      <View style={styles.actionButtons}>
        <TouchableOpacity 
          style={styles.logButton}
          onPress={handleLogFood}
        >
          <Ionicons name="add-circle-outline" size={20} color="#fff" />
          <Text style={styles.logButtonText}>Log Food</Text>
        </TouchableOpacity>
        
        <TouchableOpacity style={styles.favoriteButton}>
          <Ionicons name="heart-outline" size={20} color="#FF5252" />
          <Text style={styles.favoriteButtonText}>Add to Favorites</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#666',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  errorText: {
    fontSize: 16,
    color: '#666',
    textAlign: 'center',
    marginVertical: 20,
  },
  backButton: {
    backgroundColor: '#4CAF50',
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 8,
  },
  backButtonText: {
    color: '#fff',
    fontWeight: 'bold',
  },
  foodImage: {
    width: '100%',
    height: 200,
  },
  foodImagePlaceholder: {
    width: '100%',
    height: 200,
    backgroundColor: '#f1f1f1',
    justifyContent: 'center',
    alignItems: 'center',
  },
  infoContainer: {
    padding: 20,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
  },
  foodName: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 5,
  },
  foodBrand: {
    fontSize: 16,
    color: '#666',
    marginBottom: 10,
  },
  servingInfo: {
    marginBottom: 10,
  },
  servingText: {
    fontSize: 14,
    color: '#666',
  },
  badgesContainer: {
    flexDirection: 'row',
  },
  verifiedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#e8f5e9',
    paddingVertical: 5,
    paddingHorizontal: 10,
    borderRadius: 15,
    marginRight: 8,
  },
  verifiedText: {
    marginLeft: 3,
    color: '#4CAF50',
    fontSize: 12,
    fontWeight: '500',
  },
  categoryBadge: {
    backgroundColor: '#f1f1f1',
    paddingVertical: 5,
    paddingHorizontal: 10,
    borderRadius: 15,
  },
  categoryText: {
    color: '#666',
    fontSize: 12,
    fontWeight: '500',
  },
  nutritionSummary: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    marginTop: 15,
    padding: 15,
  },
  nutrientContainer: {
    flex: 1,
    alignItems: 'center',
  },
  nutrientValue: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  nutrientLabel: {
    fontSize: 14,
    color: '#666',
    marginTop: 5,
  },
  verticalDivider: {
    width: 1,
    backgroundColor: '#eee',
    marginHorizontal: 10,
  },
  detailedNutrition: {
    margin: 15,
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 15,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 1,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 15,
  },
  nutritionTable: {
    marginBottom: 10,
  },
  nutritionRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 10,
  },
  subNutritionRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
    paddingLeft: 20,
  },
  nutritionLabel: {
    fontSize: 16,
  },
  subNutritionLabel: {
    fontSize: 14,
    color: '#666',
  },
  nutritionValue: {
    fontSize: 16,
    fontWeight: '500',
  },
  divider: {
    height: 1,
    backgroundColor: '#eee',
  },
  actionButtons: {
    flexDirection: 'row',
    padding: 15,
    marginBottom: 30,
  },
  logButton: {
    flex: 1,
    backgroundColor: '#4CAF50',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    borderRadius: 8,
    marginRight: 10,
  },
  logButtonText: {
    color: '#fff',
    fontWeight: 'bold',
    marginLeft: 5,
  },
  favoriteButton: {
    flex: 1,
    backgroundColor: '#fff',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#FF5252',
  },
  favoriteButtonText: {
    color: '#FF5252',
    fontWeight: 'bold',
    marginLeft: 5,
  },
});
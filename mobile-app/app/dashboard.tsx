import { 
  View, 
  Text, 
  ScrollView, 
  StyleSheet, 
  SafeAreaView,
  RefreshControl,
  ActivityIndicator,
  Image,
  TouchableOpacity,
  Alert
} from 'react-native';
import CategoryCard from '../components/CategoryCard';
import BottomNav from '../components/BottomNav';
import { useEffect, useState } from 'react';
import { apiService, Professional, Category } from '../services/api';
import { useRouter } from 'expo-router';

export default function Dashboard() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [professionals, setProfessionals] = useState<Professional[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pairingInProgress, setPairingInProgress] = useState<string | null>(null);
  const router = useRouter();

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch categories from backend
      const categoriesResponse = await apiService.getCategories();
      
      // Transform backend categories to match your component props
      const transformedCategories = categoriesResponse.map((cat: Category) => {
        const categoryConfig: { [key: string]: { icon: string; color: string } } = {
          'Legal Advice': { icon: '⚖️', color: '#1E40AF' },
          'Mental Health': { icon: '🧠', color: '#059669' },
          'Career Guidance': { icon: '💼', color: '#7C3AED' },
          'Medical Help': { icon: '🏥', color: '#DC2626' },
          'Finance': { icon: '💰', color: '#D97706' },
          'Technology': { icon: '💻', color: '#0369A1' },
          'Education': { icon: '🎓', color: '#7C3AED' },
          'Business': { icon: '📊', color: '#059669' },
        };

        const config = categoryConfig[cat.name] || { icon: '💼', color: '#6B7280' };

        const calculateAvgResponse = (sessionCount: number): string => {
          if (sessionCount > 1000) return '1 min';
          if (sessionCount > 500) return '2 min';
          if (sessionCount > 100) return '3 min';
          return '5 min';
        };

        return {
          id: cat.id.toString(),
          title: cat.name,
          icon: config.icon,
          color: config.color,
          available: cat.professional_count || 0,
          rate: `KSH ${cat.base_price || 0}/min`,
          avgResponse: calculateAvgResponse(cat.session_count || 0),
        };
      });

      setCategories(transformedCategories);

      // Fetch all professionals
      await loadProfessionals();

    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      setError('Unable to load data. Please check your connection and try again.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const loadProfessionals = async () => {
    try {
      const professionalsResponse = await apiService.getProfessionalList({ 
        status: 'approved', 
        available: true 
      });
      
      console.log('🔍 FULL PROFESSIONALS API RESPONSE:', JSON.stringify(professionalsResponse, null, 2));
      
      if (professionalsResponse.professionals && professionalsResponse.professionals.length > 0) {
        // Log the first professional to see the actual structure
        console.log('👤 FIRST PROFESSIONAL STRUCTURE:', JSON.stringify(professionalsResponse.professionals[0], null, 2));
        
        setProfessionals(professionalsResponse.professionals);
      } else {
        console.log('❌ No professionals found in API response');
        setProfessionals([]);
      }
    } catch (error) {
      console.error('Failed to load professionals:', error);
      setProfessionals([]);
    }
  };

  // AI Pairing Algorithm - MATCH BY CATEGORY ID (Most Reliable)
  const findBestProfessional = (categoryId: string, categoryTitle: string): Professional | null => {
    console.log('🔍 Finding professional for category ID:', categoryId, 'Title:', categoryTitle);
    console.log('📊 Available professionals:', professionals.length);
    
    // Convert categoryId to number for comparison
    const targetCategoryId = parseInt(categoryId);

    // FIXED: Find professionals that match the category by ID (most reliable)
    const categoryProfessionals = professionals.filter(prof => {
      // Extract category IDs from all possible category relationships
      const professionalCategoryIds = new Set<number>();

      // 1. Check primary_category ID
      if (prof.primary_category) {
        if (typeof prof.primary_category === 'object' && prof.primary_category.id) {
          professionalCategoryIds.add(prof.primary_category.id);
        } else if (typeof prof.primary_category === 'number') {
          professionalCategoryIds.add(prof.primary_category);
        }
      }

      // 2. Check category ID (legacy field)
      if (prof.category) {
        if (typeof prof.category === 'object' && prof.category.id) {
          professionalCategoryIds.add(prof.category.id);
        } else if (typeof prof.category === 'number') {
          professionalCategoryIds.add(prof.category);
        }
      }

      // 3. Check categories array IDs
      if (prof.categories && Array.isArray(prof.categories)) {
        prof.categories.forEach((cat: any) => {
          if (cat && typeof cat === 'object' && cat.id) {
            professionalCategoryIds.add(cat.id);
          } else if (typeof cat === 'number') {
            professionalCategoryIds.add(cat);
          }
        });
      }

      // Check if any of the professional's category IDs match the target category ID
      const hasCategoryMatch = professionalCategoryIds.has(targetCategoryId);

      console.log(`Professional ${prof.name}:`, {
        categoryIds: Array.from(professionalCategoryIds),
        targetCategoryId,
        hasCategoryMatch,
        primary_category: prof.primary_category,
        category: prof.category,
        categories: prof.categories
      });
      
      return hasCategoryMatch && 
             prof.available !== false &&
             prof.status === 'approved';
    });

    console.log(`📈 Found ${categoryProfessionals.length} professionals for category ID ${categoryId}`);

    if (categoryProfessionals.length === 0) {
      console.log('❌ No available professionals found for this category ID');
      return null;
    }

    // AI Scoring Algorithm
    const scoredProfessionals = categoryProfessionals.map(prof => {
      let score = 0;
      const scoringDetails: string[] = [];

      // 1. Rating (40% weight)
      const ratingScore = (prof.average_rating || 4.0) * 10;
      score += ratingScore;
      scoringDetails.push(`Rating: ${prof.average_rating || 4.0} (${ratingScore}pts)`);

      // 2. Response Time (25% weight) - based on session count
      const responseTimeScore = calculateResponseTimeScore(prof.total_sessions || 0) * 25;
      score += responseTimeScore;
      scoringDetails.push(`Response: ${calculateResponseTime(prof.total_sessions || 0)} (${responseTimeScore}pts)`);

      // 3. Experience (15% weight)
      const expYears = extractExperience(prof.experience);
      const experienceScore = Math.min(expYears, 10) * 1.5;
      score += experienceScore;
      scoringDetails.push(`Experience: ${expYears} years (${experienceScore}pts)`);

      // 4. Success Rate (10% weight)
      const successRate = calculateSuccessRate(prof);
      const successScore = successRate * 10;
      score += successScore;
      scoringDetails.push(`Success: ${successRate}% (${successScore}pts)`);

      // 5. Session Count (5% weight)
      const sessionScore = Math.min((prof.total_sessions || 0) / 20, 5);
      score += sessionScore;
      scoringDetails.push(`Sessions: ${prof.total_sessions || 0} (${sessionScore}pts)`);

      // 6. Online Status Bonus (5% weight)
      if (prof.online_status) {
        score += 5;
        scoringDetails.push('Online: +5pts');
      }

      console.log(`📊 ${prof.name} total score: ${score}`, scoringDetails);
      
      return { 
        professional: prof, 
        score,
        details: scoringDetails.join(', ')
      };
    });

    // Sort by score and select the best one
    scoredProfessionals.sort((a, b) => b.score - a.score);
    const bestMatch = scoredProfessionals[0];

    console.log('🎯 AI selected professional:', {
      name: bestMatch.professional.name,
      score: bestMatch.score,
      details: bestMatch.details
    });

    return bestMatch.professional;
  };

  // Helper functions for scoring
  const calculateResponseTimeScore = (sessionCount: number): number => {
    if (sessionCount > 1000) return 1.0;
    if (sessionCount > 500) return 0.9;
    if (sessionCount > 100) return 0.8;
    return 0.6;
  };

  const calculateResponseTime = (sessionCount: number): string => {
    if (sessionCount > 1000) return '1 min';
    if (sessionCount > 500) return '2 min';
    if (sessionCount > 100) return '3 min';
    return '5 min';
  };

  const calculateSuccessRate = (prof: Professional): number => {
    const baseRate = (prof.average_rating || 4.0) * 20;
    const sessionBonus = Math.min((prof.total_sessions || 0) * 0.1, 10);
    return Math.min(baseRate + sessionBonus, 95);
  };

  const extractExperience = (experience: string | undefined): number => {
    if (!experience) return 1;
    const match = experience.match(/(\d+)/);
    return match ? parseInt(match[1]) : 1;
  };

  const handleCategoryPress = async (category: any) => {
    try {
      setPairingInProgress(category.id);
      
      console.log(`🔍 Starting AI pairing for: ${category.title} (ID: ${category.id})`);
      console.log('📊 Available professionals count:', professionals.length);
      
      // Find the best professional using AI algorithm
      const bestProfessional = findBestProfessional(category.id, category.title);

      if (!bestProfessional) {
        Alert.alert(
          'No Professionals Available',
          `Sorry, there are no available ${category.title} professionals at the moment. Please try again later.`,
          [{ text: 'OK' }]
        );
        setPairingInProgress(null);
        return;
      }

      console.log('🎯 AI Selected Professional:', bestProfessional.name);
      
      // Create session data
      const sessionData = {
        categoryId: category.id,
        categoryName: category.title,
        professionalId: bestProfessional.id,
        professionalName: bestProfessional.name,
        rate: category.rate,
        timestamp: new Date().toISOString(),
      };

      // Try to lock other professionals in this category
      try {
        await apiService.lockProfessionals({
          category: category.title,
          selected_professional_id: bestProfessional.id.toString()
        });
        console.log(`🔒 Locked other professionals in ${category.title}`);
      } catch (lockError) {
        console.log('⚠️ Professional locking not available, continuing...');
      }

      // Navigate to session screen with the paired professional
      router.push({
        pathname: '/session',
        params: {
          session: JSON.stringify(sessionData),
          professional: JSON.stringify(bestProfessional),
          category: JSON.stringify(category)
        }
      });

    } catch (error) {
      console.error('Pairing error:', error);
      Alert.alert('Error', 'Failed to connect with professional. Please try again.');
    } finally {
      setPairingInProgress(null);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadDashboardData();
  };

  const handleLogout = async () => {
    try {
      router.push('/logout');
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  if (loading && !refreshing) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#2563EB" />
          <Text style={styles.loadingText}>Loading DirectConnect...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView 
        style={styles.scroll} 
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        <View style={styles.header}>
          <View style={styles.headerTop}>
            <View style={styles.logoContainer}>
              <Image 
                source={require('../assets/images/logo.png')} 
                style={styles.logo}
                resizeMode="contain"
              />
            </View>
            <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
              <Text style={styles.logoutText}>Logout</Text>
            </TouchableOpacity>
          </View>
          
          <View style={styles.taglineContainer}>
            <Text style={styles.tagline}>"Skip the search, get the answer."</Text>
          </View>
        </View>

        {error && (
          <View style={styles.errorContainer}>
            <Text style={styles.errorText}>{error}</Text>
            <Text style={styles.errorSubtext}>Pull down to refresh</Text>
          </View>
        )}

        <View style={styles.categories}>
          {categories.length > 0 ? (
            categories.map((category) => (
              <TouchableOpacity 
                key={category.id}
                onPress={() => handleCategoryPress(category)}
                disabled={pairingInProgress !== null}
              >
                <CategoryCard 
                  {...category} 
                  isPairing={pairingInProgress === category.id}
                />
              </TouchableOpacity>
            ))
          ) : (
            <View style={styles.emptyState}>
              <Text style={styles.emptyStateText}>No categories available</Text>
              <Text style={styles.emptyStateSubtext}>
                Check back later for available services
              </Text>
            </View>
          )}
        </View>

        {pairingInProgress && (
          <View style={styles.pairingOverlay}>
            <ActivityIndicator size="large" color="#FFFFFF" />
            <Text style={styles.pairingText}>
              🤖 AI is finding your perfect match...
            </Text>
          </View>
        )}

      </ScrollView>
      <BottomNav />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F9FAFB'
  },
  scroll: {
    flex: 1,
    padding: 20
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#6B7280',
  },
  header: {
    marginBottom: 20,
  },
  headerTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  logoContainer: {
    flex: 1,
    alignItems: 'center',
  },
  logo: {
    width: 220,
    height: 110,
  },
  logoutButton: {
    backgroundColor: '#EF4444',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    position: 'absolute',
    right: 0,
  },
  logoutText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
  },
  taglineContainer: {
    alignItems: 'center',
  },
  tagline: {
    fontSize: 18,
    fontWeight: '800',
    color: '#111827',
    textAlign: 'center',
    fontStyle: 'italic',
  },
  errorContainer: {
    backgroundColor: '#FEF2F2',
    padding: 16,
    borderRadius: 8,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#FECACA',
  },
  errorText: {
    color: '#DC2626',
    fontSize: 14,
    marginBottom: 4,
    textAlign: 'center',
  },
  errorSubtext: {
    color: '#EF4444',
    fontSize: 12,
    textAlign: 'center',
  },
  categories: {
    marginBottom: 20
  },
  emptyState: {
    alignItems: 'center',
    padding: 40,
  },
  emptyStateText: {
    fontSize: 16,
    color: '#6B7280',
    marginBottom: 8,
  },
  emptyStateSubtext: {
    fontSize: 14,
    color: '#9CA3AF',
    textAlign: 'center',
  },
  pairingOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000,
  },
  pairingText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '600',
    marginTop: 16,
    textAlign: 'center',
  },
});
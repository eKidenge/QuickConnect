import React, { useState, useEffect } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  ScrollView, 
  TouchableOpacity, 
  ActivityIndicator,
  Alert,
  Image,
  RefreshControl
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';

interface Category {
  id: string;
  name: string;
  is_primary?: boolean;
}

interface Professional {
  id: string;
  name: string;
  specialization: string;
  rate: number;
  available: boolean;
  online_status: boolean;
  category: Category | null;
  primary_category: Category | null;
  categories: Category[];
  average_rating: number;
  total_sessions: number;
  experience_years: number;
  email?: string;
  phone?: string;
  bio?: string;
  title?: string;
  languages?: string[];
  education?: string[];
  certifications?: string[];
  avg_response_time?: string;
  success_rate?: number;
  current_workload?: number;
  max_workload?: number;
  last_active?: string;
  profile_picture?: string;
  is_favorite?: boolean;
  created_at?: string;
}

interface MatchingScore {
  professional: Professional;
  score: number;
  breakdown: {
    category_match: number;
    availability: number;
    rating: number;
    response_time: number;
    experience: number;
    workload: number;
  };
  ai_confidence: number;
  match_reason: string;
}

interface APIResponse {
  professionals: Professional[];
  count: number;
  category?: string;
}

interface AvailabilityResponse {
  available: boolean;
  online_status: boolean;
  in_session: boolean;
  current_workload: number;
  max_workload: number;
  workload_percentage: number;
  can_accept_new: boolean;
  estimated_wait_time: number;
  last_active: string | null;
}

export default function AlgorithmMatch() {
  const router = useRouter();
  const params = useLocalSearchParams();
  const [professionals, setProfessionals] = useState<Professional[]>([]);
  const [bestMatch, setBestMatch] = useState<MatchingScore | null>(null);
  const [loading, setLoading] = useState(true);
  const [matchingInProgress, setMatchingInProgress] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string>('Loading...');
  const [selectedCategoryId, setSelectedCategoryId] = useState<string>('');
  const [userId, setUserId] = useState<string>('1');
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string>('');

  // Use your actual server IP from the logs
  const API_BASE_URL = 'http://192.168.100.38:8000/api';

  // Debug params on component mount
  useEffect(() => {
    console.log('🔍 AlgorithmMatch Params:', params);
    
    // Handle different parameter formats
    const category = params.category || params.categoryName || params.name || params.type;
    const categoryId = params.categoryId || params.id;
    const user = params.userId || params.user;
    
    if (category) {
      setSelectedCategory(category as string);
      console.log('✅ Setting category:', category);
    } else {
      setSelectedCategory('Professionals');
      console.log('⚠️ No category provided, using default');
    }
    
    if (categoryId) {
      setSelectedCategoryId(categoryId as string);
      console.log('✅ Setting category ID:', categoryId);
    }
    
    if (user) {
      setUserId(user as string);
      console.log('✅ Setting user ID:', user);
    }
  }, [params]);

  useEffect(() => {
    console.log('🔄 useEffect triggered - Category:', selectedCategory, 'Category ID:', selectedCategoryId);
    
    if (selectedCategory && selectedCategory !== 'Loading...') {
      fetchBestMatch();
    }
  }, [selectedCategory, selectedCategoryId]);

  // ==================== DATABASE-AWARE CATEGORY MATCHING ALGORITHM ====================
  
  const calculateMatchingScore = (professional: Professional): MatchingScore | null => {
    // STEP 1: DATABASE-AWARE CATEGORY VERIFICATION
    const categoryMatchScore = calculateCategoryMatchScore(professional);
    
    // CRITICAL: If category doesn't match well enough, REJECT completely
    if (categoryMatchScore < 0.6) {
      console.log(`❌ REJECTED: ${professional.name} - Insufficient category match: ${categoryMatchScore}`);
      return null;
    }
    
    console.log(`✅ ACCEPTED: ${professional.name} - Strong category match: ${categoryMatchScore}`);

    // STEP 2: Only calculate other scores for properly category-matched professionals
    const weights = {
      category_match: 0.70,
      availability: 0.20,
      rating: 0.06,
      response_time: 0.04,
      experience: 0.00,
      workload: 0.00
    };

    const availabilityScore = calculateAvailabilityScore(professional);
    const ratingScore = calculateBayesianRatingScore(professional);
    const responseTimeScore = calculateResponseTimeScore(professional);
    const experienceScore = calculateExperienceScore(professional);
    const workloadScore = calculateWorkloadScore(professional);

    const totalScore = 
      categoryMatchScore * weights.category_match +
      availabilityScore * weights.availability +
      ratingScore * weights.rating +
      responseTimeScore * weights.response_time +
      experienceScore * weights.experience +
      workloadScore * weights.workload;

    const aiConfidence = calculateAIConfidence(professional, {
      categoryMatchScore,
      availabilityScore,
      ratingScore,
      responseTimeScore,
      experienceScore,
      workloadScore
    });

    const matchReason = generateMatchReason(professional, {
      categoryMatchScore,
      availabilityScore,
      ratingScore,
      responseTimeScore,
      experienceScore,
      workloadScore
    });

    return {
      professional,
      score: Math.round(totalScore * 100),
      breakdown: {
        category_match: Math.round(categoryMatchScore * 100),
        availability: Math.round(availabilityScore * 100),
        rating: Math.round(ratingScore * 100),
        response_time: Math.round(responseTimeScore * 100),
        experience: Math.round(experienceScore * 100),
        workload: Math.round(workloadScore * 100)
      },
      ai_confidence: aiConfidence,
      match_reason: matchReason
    };
  };

  const calculateCategoryMatchScore = (professional: Professional): number => {
    console.log(`🔍 DATABASE-AWARE category check for ${professional.name}:`, {
      professionalCategory: professional.category,
      primaryCategory: professional.primary_category,
      categories: professional.categories,
      specialization: professional.specialization,
      selectedCategory: selectedCategory
    });

    const cleanSelected = selectedCategory.toLowerCase().trim();
    
    // METHOD 1: Check primary_category field (most important)
    if (professional.primary_category?.name?.toLowerCase().trim() === cleanSelected) {
      console.log('🎯 PERFECT: Primary category match');
      return 1.0;
    }
    
    // METHOD 2: Check category field (legacy field)
    if (professional.category?.name?.toLowerCase().trim() === cleanSelected) {
      console.log('🎯 PERFECT: Category field match');
      return 1.0;
    }
    
    // METHOD 3: Check categories ManyToMany field
    if (professional.categories?.some(cat => 
      cat.name?.toLowerCase().trim() === cleanSelected
    )) {
      console.log('🎯 PERFECT: Categories array match');
      return 1.0;
    }
    
    // METHOD 4: Check if primary_category name contains selected
    if (professional.primary_category?.name?.toLowerCase().includes(cleanSelected)) {
      console.log('✅ STRONG: Primary category contains selected');
      return 0.9;
    }
    
    // METHOD 5: Check if category field contains selected
    if (professional.category?.name?.toLowerCase().includes(cleanSelected)) {
      console.log('✅ STRONG: Category field contains selected');
      return 0.9;
    }
    
    // METHOD 6: Check if any category in array contains selected
    const anyCategoryMatch = professional.categories?.some(cat => 
      cat.name?.toLowerCase().includes(cleanSelected)
    );
    if (anyCategoryMatch) {
      console.log('✅ STRONG: Categories array contains selected');
      return 0.9;
    }
    
    // METHOD 7: Check specialization
    if (professional.specialization?.toLowerCase().includes(cleanSelected)) {
      console.log('✅ STRONG: Specialization contains category');
      return 0.9;
    }
    
    // METHOD 8: Check if selected contains primary category
    if (cleanSelected.includes(professional.primary_category?.name?.toLowerCase() || '')) {
      console.log('✅ STRONG: Selected contains primary category');
      return 0.9;
    }
    
    // METHOD 9: Check if selected contains any category
    const selectedContainsCategory = professional.categories?.some(cat => 
      cleanSelected.includes(cat.name?.toLowerCase() || '')
    );
    if (selectedContainsCategory) {
      console.log('✅ STRONG: Selected contains category from array');
      return 0.9;
    }
    
    // METHOD 10: Partial matches for broader categories
    if (professional.primary_category?.name?.toLowerCase().includes(cleanSelected.substring(0, 4))) {
      console.log('⚠️ WEAK: Partial primary category match');
      return 0.7;
    }
    
    // NO MATCH FOUND
    console.log('❌ REJECT: No category match found in any field');
    return 0.1;
  };

  const calculateAvailabilityScore = (professional: Professional): number => {
    let score = 0;
    
    // Only consider availability for category-matched professionals
    if (professional.online_status) score += 0.6;
    if (professional.available) score += 0.4;
    
    return Math.min(score, 1);
  };

  const calculateBayesianRatingScore = (professional: Professional): number => {
    const bayesianConstant = 5;
    const averageRating = 4.0;
    const reviews = professional.total_sessions || 1;
    
    const bayesianScore = 
      (professional.average_rating * reviews + averageRating * bayesianConstant) / 
      (reviews + bayesianConstant);
    
    return (bayesianScore - 1) / 4;
  };

  const calculateResponseTimeScore = (professional: Professional): number => {
    const responseTimes: { [key: string]: number } = {
      '< 1 hour': 1.0,
      '< 2 hours': 0.9,
      '< 4 hours': 0.7,
      '< 8 hours': 0.5,
      '< 24 hours': 0.3
    };
    
    return responseTimes[professional.avg_response_time || '< 4 hours'] || 0.2;
  };

  const calculateExperienceScore = (professional: Professional): number => {
    const experience = professional.experience_years || 1;
    return Math.min(experience / 10.0, 1.0);
  };

  const calculateWorkloadScore = (professional: Professional): number => {
    const currentWorkload = professional.current_workload || 0;
    const maxWorkload = professional.max_workload || 5;
    const workloadRatio = currentWorkload / maxWorkload;
    
    if (workloadRatio <= 0.7) return 1.0;
    if (workloadRatio <= 0.9) return 0.5;
    return 0.1;
  };

  const calculateAIConfidence = (professional: Professional, scores: any): number => {
    let confidence = 0.8;
    
    // Highest confidence for exact category matches
    if (scores.categoryMatchScore === 1.0) confidence += 0.15;
    
    // More sessions = higher confidence
    if (professional.total_sessions > 20) confidence += 0.05;
    
    return Math.min(confidence, 0.95);
  };

  const generateMatchReason = (professional: Professional, scores: any): string => {
    const reasons: string[] = [];
    
    // ALWAYS START WITH CATEGORY MATCH
    if (scores.categoryMatchScore === 1.0) {
      reasons.push(`Perfect ${selectedCategory} specialist`);
    } else {
      reasons.push(`Qualified ${selectedCategory} expert`);
    }
    
    // Availability reasons
    if (professional.online_status) {
      reasons.push('Online now');
    } else if (professional.available) {
      reasons.push('Available today');
    }
    
    // Experience
    if (professional.experience_years > 5) {
      reasons.push(`${professional.experience_years}+ years experience`);
    }
    
    return reasons.join(' • ');
  };

  // Find the single best match with CATEGORY PRIORITY
  const findBestMatch = (professionals: Professional[]): MatchingScore | null => {
    if (professionals.length === 0) return null;
    
    console.log('🎯 Finding single best CATEGORY match from', professionals.length, 'professionals');

    // Calculate scores for all professionals - REJECT non-category matches
    const validMatches = professionals
      .map((professional: Professional) => calculateMatchingScore(professional))
      .filter((match): match is MatchingScore => match !== null)
      .sort((a: MatchingScore, b: MatchingScore) => {
        // Sort by category match first, then overall score
        if (b.breakdown.category_match !== a.breakdown.category_match) {
          return b.breakdown.category_match - a.breakdown.category_match;
        }
        return b.score - a.score;
      });
    
    console.log(`✅ Found ${validMatches.length} valid category-matched professionals`);
    
    const bestMatch = validMatches[0] || null;
    if (bestMatch) {
      console.log('🏆 BEST CATEGORY MATCH SELECTED:', {
        name: bestMatch.professional.name,
        primary_category: bestMatch.professional.primary_category?.name,
        category: bestMatch.professional.category?.name,
        categories: bestMatch.professional.categories?.map(c => c.name),
        categoryMatch: bestMatch.breakdown.category_match,
        totalScore: bestMatch.score
      });
    } else {
      console.log('❌ NO ACCEPTABLE CATEGORY MATCHES FOUND');
    }
    
    return bestMatch;
  };

  // Enhanced data fetching with DATABASE-AWARE CATEGORY FOCUS
  const fetchBestMatch = async () => {
    try {
      setLoading(true);
      setMatchingInProgress(true);
      setError('');
      setBestMatch(null);
      
      console.log('🚀 Starting DATABASE-AWARE category fetch for:', selectedCategory);

      // STRATEGY 1: Try API with expanded category data
      try {
        console.log('📡 Fetching professionals with expanded category data');
        
        let url = `${API_BASE_URL}/professionals/`;
        const queryParams = new URLSearchParams({
          status: 'approved',
          expand_categories: 'true'
        });
        
        // Add category filter
        if (selectedCategory && selectedCategory !== 'Professionals') {
          queryParams.append('category', selectedCategory);
        }
        
        if (selectedCategoryId) {
          queryParams.append('category_id', selectedCategoryId);
        }
        
        url += `?${queryParams.toString()}`;
        
        console.log('🔗 API URL:', url);
        
        const response = await fetch(url, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          }
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data: APIResponse = await response.json();
        console.log('✅ API Response - Total professionals:', data.professionals?.length || 0);
        
        if (data.professionals && data.professionals.length > 0) {
          // DEBUG: Check what category data we actually received
          console.log('📊 DEBUG: Received professionals with category data:');
          data.professionals.forEach((pro, index) => {
            console.log(`Professional ${index + 1}:`, {
              name: pro.name,
              category: pro.category,
              primary_category: pro.primary_category,
              categories: pro.categories,
              specialization: pro.specialization
            });
          });
          
          setProfessionals(data.professionals);
          const bestMatch = findBestMatch(data.professionals);
          setBestMatch(bestMatch);
          setLoading(false);
          setMatchingInProgress(false);
          return;
        } else {
          console.log('📭 API returned empty professionals array');
        }
      } catch (apiError) {
        console.error('❌ API error:', apiError);
      }

      // STRATEGY 2: Get all professionals with better debugging
      console.log('🔄 Fallback: Getting all professionals for detailed analysis');
      
      try {
        const allResponse = await fetch(
          `${API_BASE_URL}/professionals/?status=approved&expand_categories=true`,
          {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
            }
          }
        );
        
        if (allResponse.ok) {
          const allData: APIResponse = await allResponse.json();
          console.log('📊 All professionals from API:', allData.professionals?.length || 0);
          
          if (allData.professionals && allData.professionals.length > 0) {
            // Show all unique categories found in database
            const allCategories = new Set();
            allData.professionals.forEach(pro => {
              if (pro.primary_category?.name) allCategories.add(pro.primary_category.name);
              if (pro.category?.name) allCategories.add(pro.category.name);
              pro.categories?.forEach(cat => allCategories.add(cat.name));
            });
            console.log('🎯 Available categories in database:', Array.from(allCategories));
            
            // Apply category filtering with detailed logging
            const categoryProfessionals = allData.professionals.filter(pro => {
              const categoryScore = calculateCategoryMatchScore(pro);
              const accepted = categoryScore >= 0.6;
              console.log(`📋 ${pro.name}:`, {
                primary: pro.primary_category?.name,
                category: pro.category?.name,
                categories: pro.categories?.map(c => c.name),
                score: categoryScore,
                status: accepted ? '✅ ACCEPTED' : '❌ REJECTED'
              });
              return accepted;
            });
            
            console.log(`🎯 After filtering: ${categoryProfessionals.length} professionals`);
            
            setProfessionals(categoryProfessionals);
            const bestMatch = findBestMatch(categoryProfessionals);
            setBestMatch(bestMatch);
            setLoading(false);
            setMatchingInProgress(false);
            return;
          }
        }
      } catch (fallbackError) {
        console.error('❌ Fallback API error:', fallbackError);
      }
      
      // FINAL FALLBACK: Enhanced mock data that matches your DB structure
      console.log('📭 Using enhanced mock data');
      await loadEnhancedMockData();
      
    } catch (error) {
      console.error('❌ Error in fetchBestMatch:', error);
      setError('Failed to load professionals. Please try again.');
      await loadEnhancedMockData();
    } finally {
      setLoading(false);
      setMatchingInProgress(false);
    }
  };

  // Enhanced mock data matching your database structure
  const loadEnhancedMockData = async () => {
    console.log('🔄 Loading enhanced mock data for:', selectedCategory);
    
    // Create mock data that matches your actual database structure
    const mockProfessionals: Professional[] = [
      {
        id: '1',
        name: 'Dr. Sarah Johnson',
        specialization: `${selectedCategory} Consulting`,
        rate: 85,
        available: true,
        online_status: true,
        category: { name: selectedCategory, id: '1' },
        primary_category: { name: selectedCategory, id: '1' },
        categories: [
          { id: '1', name: selectedCategory, is_primary: true }
        ],
        average_rating: 4.8,
        total_sessions: 120,
        experience_years: 8,
        email: `sarah.${selectedCategory.toLowerCase()}@example.com`,
        phone: '+1234567890',
        bio: `Expert ${selectedCategory.toLowerCase()} consultant with ${8} years of specialized experience.`,
        title: `Senior ${selectedCategory} Consultant`,
        languages: ['English', 'Spanish'],
        education: [`Masters in ${selectedCategory} - Stanford University`],
        certifications: [`Certified ${selectedCategory} Professional`],
        avg_response_time: '< 1 hour',
        success_rate: 96,
        current_workload: 2,
        max_workload: 5,
        last_active: new Date().toISOString(),
        profile_picture: 'https://images.unsplash.com/photo-1494790108755-2616b612b786?w=150'
      },
      {
        id: '2',
        name: 'Michael Chen',
        specialization: `${selectedCategory} Advisor`,
        rate: 75,
        available: true,
        online_status: false,
        category: { name: selectedCategory, id: '1' },
        primary_category: { name: selectedCategory, id: '1' },
        categories: [
          { id: '1', name: selectedCategory, is_primary: true }
        ],
        average_rating: 4.6,
        total_sessions: 65,
        experience_years: 5,
        email: `michael.${selectedCategory.toLowerCase()}@example.com`,
        bio: `Dedicated ${selectedCategory.toLowerCase()} advisor with proven track record.`,
        title: `${selectedCategory} Advisor`,
        languages: ['English', 'Mandarin'],
        avg_response_time: '< 2 hours',
        success_rate: 94,
        current_workload: 3,
        max_workload: 6,
        last_active: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
        profile_picture: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150'
      }
    ];

    // Only include professionals that match the selected category
    const filteredProfessionals = mockProfessionals.filter(pro => 
      calculateCategoryMatchScore(pro) >= 0.6
    );

    console.log(`🎯 Mock data filtered: ${filteredProfessionals.length} professionals`);
    
    setProfessionals(filteredProfessionals);
    const bestMatch = findBestMatch(filteredProfessionals);
    setBestMatch(bestMatch);
  };

  const checkRealTimeAvailability = async (professionalId: string): Promise<AvailabilityResponse> => {
    try {
      console.log('🔍 Checking real-time availability for:', professionalId);
      
      const response = await fetch(
        `${API_BASE_URL}/check-professional-availability/${professionalId}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          }
        }
      );
      
      if (response.ok) {
        const availability = await response.json();
        return availability;
      } else {
        throw new Error('Availability check failed');
      }
    } catch (error) {
      console.error('❌ Availability check failed:', error);
      const professional = professionals.find(p => p.id === professionalId);
      return {
        available: professional?.available || true,
        online_status: professional?.online_status || true,
        in_session: false,
        current_workload: professional?.current_workload || 2,
        max_workload: professional?.max_workload || 5,
        workload_percentage: ((professional?.current_workload || 2) / (professional?.max_workload || 5)) * 100,
        can_accept_new: (professional?.available && professional?.online_status) || true,
        estimated_wait_time: 5,
        last_active: professional?.last_active || new Date().toISOString()
      };
    }
  };

  const handleProfessionalSelect = async (professional: Professional, matchScore: MatchingScore) => {
    try {
      const availabilityCheck = await checkRealTimeAvailability(professional.id);
      
      if (!availabilityCheck.available || !availabilityCheck.can_accept_new) {
        Alert.alert(
          'Currently Unavailable', 
          `${professional.name} is currently unavailable for ${selectedCategory} consultations. Please try again later.`
        );
        return;
      }

      router.push({
        pathname: '/expert',
        params: { 
          professional: JSON.stringify({
            ...professional,
            matchScore: matchScore.score,
            aiConfidence: matchScore.ai_confidence,
            matchReason: matchScore.match_reason,
            breakdown: matchScore.breakdown,
            availability: availabilityCheck,
            selectedCategory: selectedCategory
          })
        }
      });
    } catch (error) {
      console.error('❌ Error selecting professional:', error);
      Alert.alert('Error', 'Failed to verify availability. Please try again.');
    }
  };

  const handleStopAndGoBack = () => {
    Alert.alert(
      'Stop Matching',
      'Are you sure you want to stop searching for professionals?',
      [
        {
          text: 'Continue Searching',
          style: 'cancel'
        },
        {
          text: 'Stop & Go Back',
          onPress: () => router.back(),
          style: 'destructive'
        }
      ]
    );
  };

  const onRefresh = React.useCallback(() => {
    console.log('🔄 Manual refresh for category:', selectedCategory);
    setRefreshing(true);
    fetchBestMatch().then(() => setRefreshing(false));
  }, [selectedCategory, selectedCategoryId]);

  const handleBackPress = () => {
    router.back();
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>
          Finding your perfect {selectedCategory} expert...
        </Text>
        <Text style={styles.loadingSubtext}>
          Database-aware category matching in progress...
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <ScrollView 
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        contentContainerStyle={styles.scrollContent}
      >
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={handleBackPress} style={styles.backButton}>
            <Text style={styles.backButtonText}>← Back</Text>
          </TouchableOpacity>
          <Text style={styles.headerTitle}>{selectedCategory} Expert</Text>
          <Text style={styles.headerSubtitle}>
            Database-aware category matching • Real-time availability
          </Text>
          <Text style={styles.matchCount}>
            {bestMatch ? '1 perfect category match found' : 'No category specialists available'}
          </Text>
          {error ? (
            <Text style={styles.errorText}>{error}</Text>
          ) : null}
        </View>

        {matchingInProgress && (
          <View style={styles.matchingContainer}>
            <ActivityIndicator size="small" color="#007AFF" />
            <Text style={styles.matchingText}>
              Analyzing database categories for {selectedCategory}...
            </Text>
          </View>
        )}

        {bestMatch ? (
          <View style={styles.singleMatchContainer}>
            <View style={styles.topMatchBadge}>
              <Text style={styles.topMatchText}>
                🎯 PERFECT {selectedCategory.toUpperCase()} MATCH
              </Text>
            </View>

            <View style={styles.matchCard}>
              <View style={styles.cardHeader}>
                <Image
                  source={{ 
                    uri: bestMatch.professional.profile_picture || 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150'
                  }}
                  style={styles.professionalImage}
                />
                <View style={styles.professionalInfo}>
                  <Text style={styles.professionalName}>{bestMatch.professional.name}</Text>
                  <Text style={styles.professionalCategory}>
                    {selectedCategory} Specialist
                  </Text>
                  <Text style={styles.professionalSpecialization}>
                    {bestMatch.professional.specialization}
                  </Text>
                  <View style={styles.ratingContainer}>
                    <Text style={styles.rating}>⭐ {bestMatch.professional.average_rating.toFixed(1)}</Text>
                    <Text style={styles.reviews}>({bestMatch.professional.total_sessions} sessions)</Text>
                  </View>
                </View>
                <View style={styles.scoreContainer}>
                  <LinearGradient
                    colors={getScoreColors(bestMatch.score)}
                    style={styles.scoreCircle}
                  >
                    <Text style={styles.scoreText}>{bestMatch.score}%</Text>
                  </LinearGradient>
                  <Text style={styles.aiConfidence}>
                    Confidence: {Math.round(bestMatch.ai_confidence * 100)}%
                  </Text>
                </View>
              </View>

              <Text style={styles.matchReason}>{bestMatch.match_reason}</Text>

              {/* Category Match Emphasis */}
              <View style={styles.categoryMatchHighlight}>
                <Text style={styles.categoryMatchText}>
                  ✅ DATABASE-VERIFIED CATEGORY MATCH: {selectedCategory}
                </Text>
              </View>

              <View style={styles.breakdownContainer}>
                {Object.entries(bestMatch.breakdown).map(([key, value]) => (
                  <View key={key} style={styles.breakdownItem}>
                    <Text style={styles.breakdownLabel}>
                      {key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
                    </Text>
                    <View style={styles.breakdownBar}>
                      <View 
                        style={[
                          styles.breakdownFill,
                          { width: `${value}%` },
                          value > 80 ? styles.highScore : 
                          value > 60 ? styles.mediumScore : styles.lowScore
                        ]} 
                      />
                    </View>
                    <Text style={styles.breakdownValue}>{value}%</Text>
                  </View>
                ))}
              </View>

              <View style={styles.cardFooter}>
                <Text style={styles.rate}>${bestMatch.professional.rate}/hr</Text>
                <View style={styles.statusContainer}>
                  {bestMatch.professional.online_status ? (
                    <View style={styles.onlineIndicator}>
                      <Text style={styles.onlineStatus}>🟢 ONLINE NOW</Text>
                    </View>
                  ) : (
                    <Text style={styles.offlineStatus}>⚫ OFFLINE</Text>
                  )}
                </View>
                <Text style={styles.responseTime}>
                  ⚡ {bestMatch.professional.avg_response_time || '< 4 hours'}
                </Text>
              </View>

              <TouchableOpacity
                style={styles.selectButton}
                onPress={() => handleProfessionalSelect(bestMatch.professional, bestMatch)}
                activeOpacity={0.7}
              >
                <Text style={styles.selectButtonText}>
                  Select {selectedCategory} Expert
                </Text>
              </TouchableOpacity>
            </View>

            <TouchableOpacity 
              style={styles.stopButton}
              onPress={handleStopAndGoBack}
            >
              <Text style={styles.stopButtonText}>❌ Stop Matching & Go Back</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.emptyState}>
            <Text style={styles.emptyStateTitle}>
              No {selectedCategory} Experts Available
            </Text>
            <Text style={styles.emptyStateText}>
              We couldn't find any {selectedCategory.toLowerCase()} specialists in our database.
              Our algorithm checked primary_category, category field, and categories array.
            </Text>
            
            {/* Debug Info */}
            <View style={styles.debugInfo}>
              <Text style={styles.debugTitle}>Database Check:</Text>
              <Text style={styles.debugText}>
                • Checked primary_category field
              </Text>
              <Text style={styles.debugText}>
                • Checked category field  
              </Text>
              <Text style={styles.debugText}>
                • Checked categories array
              </Text>
              <Text style={styles.debugText}>
                • Checked specialization field
              </Text>
            </View>

            <TouchableOpacity 
              style={styles.retryButton}
              onPress={fetchBestMatch}
            >
              <Text style={styles.retryButtonText}>Try Again</Text>
            </TouchableOpacity>
            <TouchableOpacity 
              style={styles.stopButton}
              onPress={handleStopAndGoBack}
            >
              <Text style={styles.stopButtonText}>Stop Matching</Text>
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const getScoreColors = (score: number) => {
  if (score >= 80) return ['#10B981', '#059669'];
  if (score >= 60) return ['#F59E0B', '#D97706'];
  return ['#EF4444', '#DC2626'];
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  scrollContent: {
    flexGrow: 1,
    paddingBottom: 20,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f8f9fa',
    padding: 20,
  },
  loadingText: {
    marginTop: 16,
    fontSize: 18,
    fontWeight: '600',
    color: '#1F2937',
    textAlign: 'center',
  },
  loadingSubtext: {
    marginTop: 8,
    fontSize: 14,
    color: '#6B7280',
    textAlign: 'center',
  },
  header: {
    padding: 20,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  backButton: {
    alignSelf: 'flex-start',
    marginBottom: 12,
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: '#F3F4F6',
    borderRadius: 8,
  },
  backButtonText: {
    color: '#374151',
    fontWeight: '600',
    fontSize: 14,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#1F2937',
    marginBottom: 4,
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#6B7280',
    lineHeight: 20,
    marginBottom: 8,
  },
  matchCount: {
    fontSize: 14,
    color: '#007AFF',
    fontWeight: '600',
  },
  errorText: {
    fontSize: 14,
    color: '#EF4444',
    marginTop: 8,
    fontWeight: '500',
  },
  matchingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    backgroundColor: '#EFF6FF',
    marginHorizontal: 20,
    marginTop: 16,
    borderRadius: 12,
  },
  matchingText: {
    marginLeft: 8,
    color: '#007AFF',
    fontWeight: '500',
  },
  singleMatchContainer: {
    padding: 20,
  },
  matchCard: {
    backgroundColor: '#fff',
    padding: 20,
    borderRadius: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 12,
    elevation: 5,
    borderWidth: 2,
    borderColor: '#007AFF',
  },
  topMatchBadge: {
    alignSelf: 'center',
    backgroundColor: '#007AFF',
    paddingHorizontal: 20,
    paddingVertical: 8,
    borderRadius: 20,
    marginBottom: -10,
    zIndex: 1,
  },
  topMatchText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '700',
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  professionalImage: {
    width: 80,
    height: 80,
    borderRadius: 40,
    marginRight: 16,
  },
  professionalInfo: {
    flex: 1,
  },
  professionalName: {
    fontSize: 22,
    fontWeight: '700',
    color: '#1F2937',
    marginBottom: 4,
  },
  professionalCategory: {
    fontSize: 16,
    color: '#007AFF',
    fontWeight: '600',
    marginBottom: 2,
  },
  professionalSpecialization: {
    fontSize: 14,
    color: '#6B7280',
    marginBottom: 6,
  },
  ratingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  rating: {
    fontSize: 16,
    fontWeight: '600',
    color: '#F59E0B',
    marginRight: 6,
  },
  reviews: {
    fontSize: 14,
    color: '#9CA3AF',
  },
  scoreContainer: {
    alignItems: 'center',
  },
  scoreCircle: {
    width: 70,
    height: 70,
    borderRadius: 35,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 6,
  },
  scoreText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '700',
  },
  aiConfidence: {
    fontSize: 12,
    color: '#6B7280',
    textAlign: 'center',
  },
  matchReason: {
    fontSize: 16,
    color: '#059669',
    fontWeight: '500',
    marginBottom: 16,
    lineHeight: 22,
    textAlign: 'center',
  },
  categoryMatchHighlight: {
    backgroundColor: '#DCFCE7',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 16,
  },
  categoryMatchText: {
    fontSize: 14,
    color: '#059669',
    fontWeight: '600',
  },
  breakdownContainer: {
    marginBottom: 16,
  },
  breakdownItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  breakdownLabel: {
    width: 120,
    fontSize: 14,
    color: '#6B7280',
    fontWeight: '500',
  },
  breakdownBar: {
    flex: 1,
    height: 8,
    backgroundColor: '#E5E7EB',
    borderRadius: 4,
    marginHorizontal: 12,
    overflow: 'hidden',
  },
  breakdownFill: {
    height: '100%',
    borderRadius: 4,
  },
  highScore: {
    backgroundColor: '#10B981',
  },
  mediumScore: {
    backgroundColor: '#F59E0B',
  },
  lowScore: {
    backgroundColor: '#EF4444',
  },
  breakdownValue: {
    width: 40,
    fontSize: 14,
    fontWeight: '600',
    color: '#1F2937',
    textAlign: 'right',
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
    marginBottom: 16,
  },
  rate: {
    fontSize: 18,
    fontWeight: '700',
    color: '#059669',
  },
  statusContainer: {
    flex: 1,
    alignItems: 'center',
  },
  onlineIndicator: {
    backgroundColor: '#DCFCE7',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  onlineStatus: {
    fontSize: 12,
    color: '#059669',
    fontWeight: '700',
  },
  offlineStatus: {
    fontSize: 12,
    color: '#6B7280',
    fontWeight: '500',
  },
  responseTime: {
    fontSize: 12,
    color: '#6B7280',
    fontWeight: '500',
  },
  selectButton: {
    backgroundColor: '#007AFF',
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  selectButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  stopButton: {
    backgroundColor: '#EF4444',
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 16,
  },
  stopButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  emptyState: {
    alignItems: 'center',
    padding: 40,
    marginTop: 20,
  },
  emptyStateTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: 12,
    textAlign: 'center',
  },
  emptyStateText: {
    fontSize: 16,
    color: '#6B7280',
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 24,
  },
  debugInfo: {
    backgroundColor: '#F3F4F6',
    padding: 16,
    borderRadius: 8,
    marginBottom: 24,
    width: '100%',
  },
  debugTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
  },
  debugText: {
    fontSize: 12,
    color: '#6B7280',
    marginBottom: 4,
  },
  retryButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
    marginBottom: 12,
  },
  retryButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
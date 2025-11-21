import React, { useState, useEffect } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  ScrollView, 
  Image, 
  TouchableOpacity,
  Alert,
  ActivityIndicator
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';

interface Professional {
  id: string;
  name: string;
  specialization: string;
  rate: number;
  available: boolean;
  online_status: boolean;
  category: string;
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
  categories?: Array<{
    id: string;
    name: string;
    is_primary: boolean;
  }>;
  // Additional fields from matching algorithm
  matchScore?: number;
  aiConfidence?: number;
  matchReason?: string;
  breakdown?: any;
  availability?: any;
}

export default function ExpertProfile() {
  const params = useLocalSearchParams();
  const router = useRouter();
  const [professional, setProfessional] = useState<Professional | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (params.professional) {
      try {
        console.log('📊 Parsing professional data...');
        const professionalData = JSON.parse(params.professional as string);
        console.log('✅ Professional data loaded:', professionalData.name);
        setProfessional(professionalData);
      } catch (error) {
        console.error('❌ Error parsing professional data:', error);
        Alert.alert('Error', 'Failed to load professional profile');
      } finally {
        setLoading(false);
      }
    } else {
      console.error('❌ No professional data provided');
      Alert.alert('Error', 'No professional data available');
      setLoading(false);
    }
  }, [params.professional]);

  const handleConnectOption = async (option: 'chat' | 'audio' | 'video') => {
    if (!professional) return;

    try {
      console.log(`🚀 Initiating ${option} session with ${professional.name}`);

      // Create a session first
      const sessionResponse = await fetch('http://192.168.100.38:8000/api/sessions/create/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          professional_id: professional.id,
          client_id: '1', // Replace with actual user ID
          session_type: option,
          category: professional.category
        }),
      });

      if (sessionResponse.ok) {
        const sessionData = await sessionResponse.json();
        console.log('✅ Session created:', sessionData);

        // Navigate to payment screen with professional and session data
        router.push({
          pathname: '/payment',
          params: { 
            professional: JSON.stringify(professional),
            session: JSON.stringify(sessionData),
            consultationType: option
          }
        });
      } else {
        throw new Error('Failed to create session');
      }
    } catch (error) {
      console.error('❌ Error creating session:', error);
      Alert.alert('Error', 'Failed to initiate session. Please try again.');
    }
  };

  const addToFavorites = async () => {
    if (!professional) return;

    try {
      const response = await fetch(`http://192.168.100.38:8000/api/manage-favorites/${professional.id}/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: '1', // Replace with actual user ID
        }),
      });

      if (response.ok) {
        const data = await response.json();
        Alert.alert('Success', data.message);
        // Update local state
        setProfessional(prev => prev ? { ...prev, is_favorite: true } : null);
      }
    } catch (error) {
      console.error('Error adding to favorites:', error);
      Alert.alert('Error', 'Failed to add to favorites');
    }
  };

  const removeFromFavorites = async () => {
    if (!professional) return;

    try {
      const response = await fetch(`http://192.168.100.38:8000/api/manage-favorites/${professional.id}/`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: '1', // Replace with actual user ID
        }),
      });

      if (response.ok) {
        const data = await response.json();
        Alert.alert('Success', data.message);
        // Update local state
        setProfessional(prev => prev ? { ...prev, is_favorite: false } : null);
      }
    } catch (error) {
      console.error('Error removing from favorites:', error);
      Alert.alert('Error', 'Failed to remove from favorites');
    }
  };

  const getSkillsFromProfessional = (pro: Professional): string[] => {
    const skills: string[] = [];
    
    if (pro.specialization) {
      skills.push(pro.specialization);
    }
    
    if (pro.bio) {
      // Extract key skills from bio
      const skillKeywords = ['consulting', 'development', 'design', 'strategy', 'management', 'analysis', 'planning'];
      skillKeywords.forEach(keyword => {
        if (pro.bio?.toLowerCase().includes(keyword)) {
          skills.push(keyword.charAt(0).toUpperCase() + keyword.slice(1));
        }
      });
    }
    
    if (pro.categories && pro.categories.length > 0) {
      pro.categories.forEach(cat => {
        if (!skills.includes(cat.name)) {
          skills.push(cat.name);
        }
      });
    }
    
    return skills.length > 0 ? skills : ['Professional', 'Expert', 'Consultant'];
  };

  const getSpecializations = (pro: Professional): string[] => {
    const specializations: string[] = [];
    
    if (pro.specialization) {
      specializations.push(pro.specialization);
    }
    
    if (pro.categories && pro.categories.length > 0) {
      pro.categories.forEach(cat => {
        if (cat.is_primary && !specializations.includes(cat.name)) {
          specializations.push(cat.name);
        }
      });
    }
    
    return specializations.length > 0 ? specializations : [pro.category || 'General Consulting'];
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Loading professional profile...</Text>
      </View>
    );
  }

  if (!professional) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.errorText}>No professional data found</Text>
        <TouchableOpacity 
          style={styles.backButton}
          onPress={() => router.back()}
        >
          <Text style={styles.backButtonText}>Go Back</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const skills = getSkillsFromProfessional(professional);
  const specializations = getSpecializations(professional);
  const successRate = professional.success_rate || Math.min((professional.total_sessions / (professional.total_sessions + 10)) * 100, 95);
  const responseTime = professional.avg_response_time || '< 4 hours';

  return (
    <View style={styles.container}>
      {/* Header */}
      <LinearGradient
        colors={['#007AFF', '#0056CC']}
        style={styles.header}
      >
        <TouchableOpacity 
          style={styles.backButtonHeader}
          onPress={() => router.back()}
        >
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Expert Profile</Text>
        <TouchableOpacity 
          style={styles.favoriteButton}
          onPress={professional.is_favorite ? removeFromFavorites : addToFavorites}
        >
          <Ionicons 
            name={professional.is_favorite ? "heart" : "heart-outline"} 
            size={24} 
            color="#fff" 
          />
        </TouchableOpacity>
      </LinearGradient>

      <ScrollView style={styles.scrollContent}>
        {/* Expert Profile Card */}
        <View style={styles.profileCard}>
          <View style={styles.profileHeader}>
            <Image
              source={{ uri: professional.profile_picture || 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150' }}
              style={styles.profileImage}
            />
            <View style={styles.profileInfo}>
              <Text style={styles.expertName}>{professional.name}</Text>
              <Text style={styles.expertTitle}>
                {professional.title || professional.specialization || professional.category} Specialist
              </Text>
              <View style={styles.ratingContainer}>
                <Ionicons name="star" size={16} color="#F59E0B" />
                <Text style={styles.rating}>{professional.average_rating.toFixed(1)}</Text>
                <Text style={styles.reviews}>({professional.total_sessions} sessions)</Text>
              </View>
              <View style={styles.statusContainer}>
                <View style={[
                  styles.statusDot,
                  professional.online_status ? styles.onlineDot : styles.offlineDot
                ]} />
                <Text style={styles.statusText}>
                  {professional.online_status ? 'Online Now' : `Last Active ${professional.last_active ? 'Recently' : ''}`}
                </Text>
              </View>
            </View>
          </View>

          {/* Match Score if available */}
          {professional.matchScore && (
            <View style={styles.matchContainer}>
              <LinearGradient
                colors={['#10B981', '#059669']}
                style={styles.matchBadge}
              >
                <Text style={styles.matchScore}>{professional.matchScore}% Match</Text>
                <Text style={styles.matchSubtext}>AI Recommended</Text>
              </LinearGradient>
              {professional.matchReason && (
                <Text style={styles.matchReason}>{professional.matchReason}</Text>
              )}
            </View>
          )}

          {/* Rate and Availability */}
          <View style={styles.rateContainer}>
            <Text style={styles.rate}>${professional.rate}/hour</Text>
            <Text style={styles.availability}>
              {professional.available ? '🟢 Available' : '🔴 Busy'}
            </Text>
          </View>
        </View>

        {/* Expertise Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Expertise & Skills</Text>
          <View style={styles.skillsContainer}>
            {skills.map((skill, index) => (
              <View key={index} style={styles.skillTag}>
                <Text style={styles.skillText}>{skill}</Text>
              </View>
            ))}
          </View>
        </View>

        {/* Professional Details */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Professional Details</Text>
          
          <View style={styles.detailRow}>
            <Ionicons name="briefcase" size={20} color="#6B7280" />
            <Text style={styles.detailLabel}>Experience:</Text>
            <Text style={styles.detailValue}>{professional.experience_years}+ years</Text>
          </View>

          <View style={styles.detailRow}>
            <Ionicons name="checkmark-circle" size={20} color="#6B7280" />
            <Text style={styles.detailLabel}>Success Rate:</Text>
            <Text style={styles.detailValue}>{Math.round(successRate)}%</Text>
          </View>

          <View style={styles.detailRow}>
            <Ionicons name="time" size={20} color="#6B7280" />
            <Text style={styles.detailLabel}>Response Time:</Text>
            <Text style={styles.detailValue}>{responseTime}</Text>
          </View>

          <View style={styles.detailRow}>
            <Ionicons name="document-text" size={20} color="#6B7280" />
            <Text style={styles.detailLabel}>Total Sessions:</Text>
            <Text style={styles.detailValue}>{professional.total_sessions}+</Text>
          </View>

          {professional.current_workload && professional.max_workload && (
            <View style={styles.detailRow}>
              <Ionicons name="speedometer" size={20} color="#6B7280" />
              <Text style={styles.detailLabel}>Current Workload:</Text>
              <Text style={styles.detailValue}>
                {professional.current_workload}/{professional.max_workload}
              </Text>
            </View>
          )}
        </View>

        {/* About Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>About {professional.name}</Text>
          <Text style={styles.bio}>
            {professional.bio || `Experienced ${professional.category} specialist with ${professional.experience_years} years of proven expertise. Successfully completed ${professional.total_sessions} sessions with a ${Math.round(successRate)}% satisfaction rate. Known for ${responseTime.toLowerCase()} response times and professional approach.`}
          </Text>
        </View>

        {/* Specializations */}
        {specializations.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Specializations</Text>
            <View style={styles.specializationsContainer}>
              {specializations.map((spec, index) => (
                <View key={index} style={styles.specTag}>
                  <Ionicons name="ribbon" size={16} color="#007AFF" />
                  <Text style={styles.specText}>{spec}</Text>
                </View>
              ))}
            </View>
          </View>
        )}

        {/* Languages */}
        {professional.languages && professional.languages.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Languages</Text>
            <View style={styles.languagesContainer}>
              {professional.languages.map((language, index) => (
                <View key={index} style={styles.languageTag}>
                  <Ionicons name="language" size={16} color="#007AFF" />
                  <Text style={styles.languageText}>{language}</Text>
                </View>
              ))}
            </View>
          </View>
        )}

        {/* Education & Certifications */}
        {(professional.education || professional.certifications) && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Qualifications</Text>
            
            {professional.education && professional.education.map((edu, index) => (
              <View key={`edu-${index}`} style={styles.qualificationItem}>
                <Ionicons name="school" size={16} color="#007AFF" />
                <Text style={styles.qualificationText}>{edu}</Text>
              </View>
            ))}
            
            {professional.certifications && professional.certifications.map((cert, index) => (
              <View key={`cert-${index}`} style={styles.qualificationItem}>
                <Ionicons name="medal" size={16} color="#007AFF" />
                <Text style={styles.qualificationText}>{cert}</Text>
              </View>
            ))}
          </View>
        )}

        {/* Spacer for bottom buttons */}
        <View style={styles.spacer} />
      </ScrollView>

      {/* Connect Options Footer */}
      <View style={styles.footer}>
        <Text style={styles.footerTitle}>Connect via</Text>
        <View style={styles.connectButtonsContainer}>
          <TouchableOpacity 
            style={styles.connectButton}
            onPress={() => handleConnectOption('chat')}
          >
            <LinearGradient
              colors={['#10B981', '#059669']}
              style={styles.buttonGradient}
            >
              <Ionicons name="chatbubble-ellipses" size={24} color="#fff" />
              <Text style={styles.buttonText}>Chat</Text>
              <Text style={styles.buttonSubtext}>Text consultation</Text>
            </LinearGradient>
          </TouchableOpacity>

          <TouchableOpacity 
            style={styles.connectButton}
            onPress={() => handleConnectOption('audio')}
          >
            <LinearGradient
              colors={['#F59E0B', '#D97706']}
              style={styles.buttonGradient}
            >
              <Ionicons name="call" size={24} color="#fff" />
              <Text style={styles.buttonText}>Voice Call</Text>
              <Text style={styles.buttonSubtext}>Audio consultation</Text>
            </LinearGradient>
          </TouchableOpacity>

          <TouchableOpacity 
            style={styles.connectButton}
            onPress={() => handleConnectOption('video')}
          >
            <LinearGradient
              colors={['#EF4444', '#DC2626']}
              style={styles.buttonGradient}
            >
              <Ionicons name="videocam" size={24} color="#fff" />
              <Text style={styles.buttonText}>Video Call</Text>
              <Text style={styles.buttonSubtext}>Video consultation</Text>
            </LinearGradient>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#6B7280',
    textAlign: 'center',
  },
  errorText: {
    fontSize: 16,
    color: '#6B7280',
    marginBottom: 20,
  },
  backButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 8,
  },
  backButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  header: {
    paddingTop: 60,
    paddingBottom: 20,
    paddingHorizontal: 20,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  backButtonHeader: {
    padding: 8,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
    textAlign: 'center',
    flex: 1,
  },
  favoriteButton: {
    padding: 8,
  },
  scrollContent: {
    flex: 1,
  },
  profileCard: {
    backgroundColor: '#fff',
    margin: 20,
    marginTop: -40,
    padding: 20,
    borderRadius: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 5,
  },
  profileHeader: {
	flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  profileImage: {
    width: 80,
    height: 80,
    borderRadius: 40,
    marginRight: 16,
  },
  profileInfo: {
    flex: 1,
  },
  expertName: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#1F2937',
    marginBottom: 4,
  },
  expertTitle: {
    fontSize: 16,
    color: '#6B7280',
    marginBottom: 8,
  },
  ratingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  rating: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1F2937',
    marginLeft: 4,
    marginRight: 8,
  },
  reviews: {
    fontSize: 12,
    color: '#9CA3AF',
  },
  statusContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 6,
  },
  onlineDot: {
    backgroundColor: '#10B981',
  },
  offlineDot: {
    backgroundColor: '#6B7280',
  },
  statusText: {
    fontSize: 12,
    color: '#6B7280',
  },
  matchContainer: {
    alignItems: 'center',
    marginTop: 8,
    marginBottom: 12,
  },
  matchBadge: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    alignItems: 'center',
    marginBottom: 8,
  },
  matchScore: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
  },
  matchSubtext: {
    color: 'rgba(255,255,255,0.8)',
    fontSize: 10,
  },
  matchReason: {
    fontSize: 12,
    color: '#059669',
    textAlign: 'center',
    fontStyle: 'italic',
  },
  rateContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
  },
  rate: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#059669',
  },
  availability: {
    fontSize: 14,
    color: '#059669',
    fontWeight: '600',
  },
  section: {
    backgroundColor: '#fff',
    marginHorizontal: 20,
    marginBottom: 16,
    padding: 20,
    borderRadius: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1F2937',
    marginBottom: 12,
  },
  skillsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  skillTag: {
    backgroundColor: '#EFF6FF',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#DBEAFE',
  },
  skillText: {
    fontSize: 12,
    color: '#1E40AF',
    fontWeight: '500',
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  detailLabel: {
    fontSize: 14,
    color: '#6B7280',
    marginLeft: 8,
    marginRight: 8,
    width: 120,
  },
  detailValue: {
    fontSize: 14,
    color: '#1F2937',
    fontWeight: '500',
    flex: 1,
  },
  bio: {
    fontSize: 14,
    color: '#6B7280',
    lineHeight: 20,
  },
  specializationsContainer: {
    gap: 8,
  },
  specTag: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F0F9FF',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E0F2FE',
  },
  specText: {
    fontSize: 12,
    color: '#0369A1',
    fontWeight: '500',
    marginLeft: 6,
  },
  languagesContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  languageTag: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FEF7CD',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#FDE68A',
  },
  languageText: {
    fontSize: 12,
    color: '#92400E',
    fontWeight: '500',
    marginLeft: 4,
  },
  qualificationItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  qualificationText: {
    fontSize: 14,
    color: '#6B7280',
    marginLeft: 8,
    flex: 1,
  },
  spacer: {
    height: 120,
  },
  footer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: '#fff',
    padding: 20,
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 5,
  },
  footerTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#1F2937',
    marginBottom: 12,
    textAlign: 'center',
  },
  connectButtonsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 8,
  },
  connectButton: {
    flex: 1,
    borderRadius: 12,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  buttonGradient: {
    padding: 16,
    alignItems: 'center',
    borderRadius: 12,
  },
  buttonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
    marginTop: 8,
    marginBottom: 2,
  },
  buttonSubtext: {
    color: 'rgba(255,255,255,0.8)',
    fontSize: 10,
    textAlign: 'center',
  },
});
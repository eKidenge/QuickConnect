import { View, Text, StyleSheet, SafeAreaView, TouchableOpacity, Alert, ActivityIndicator } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState, useEffect } from 'react';
import { Ionicons } from '@expo/vector-icons';

interface SessionData {
  id: string;
  professionalId: string;
  professionalName: string;
  duration: number;
  cost: number;
  consultationType: string;
  endTime: string;
  rating?: number;
  review?: string;
}

export default function SessionCompleteScreen() {
  const router = useRouter();
  const params = useLocalSearchParams();
  const [rating, setRating] = useState(0);
  const [review, setReview] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [session, setSession] = useState<SessionData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    initializeSessionData();
  }, [params]);

  const initializeSessionData = async () => {
    try {
      setLoading(true);
      
      // If coming from session end, fetch session details
      if (params.sessionId) {
        const response = await fetch(`/api/sessions/${params.sessionId}`);
        const sessionData = await response.json();
        
        if (sessionData.success) {
          setSession(sessionData.session);
        } else {
          throw new Error('Failed to load session details');
        }
      } else if (params.cost && params.duration && params.professionalId) {
        // Create session data from params
        setSession({
          id: `temp_${Date.now()}`,
          professionalId: params.professionalId as string,
          professionalName: params.professionalName as string || 'Professional',
          duration: parseInt(params.duration as string),
          cost: parseInt(params.cost as string),
          consultationType: params.consultationType as string || 'consultation',
          endTime: new Date().toISOString()
        });
      }
    } catch (error) {
      console.error('Session data loading error:', error);
      Alert.alert('Error', 'Failed to load session details');
    } finally {
      setLoading(false);
    }
  };

  const submitRating = async () => {
    if (!session || rating === 0) {
      Alert.alert('Rating Required', 'Please select a rating before proceeding.');
      return;
    }

    try {
      setSubmitting(true);

      // Submit rating to database
		const response = await fetch('/api/sessions/rate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sessionId: session.id,
          professionalId: session.professionalId,
          rating: rating,
          review: review,
          clientId: 'current-user-id' // Replace with actual client ID
        })
      });

      const result = await response.json();

      if (result.success) {
        // Update local session with rating
        setSession(prev => prev ? { ...prev, rating, review } : null);
        
        Alert.alert(
          'Thank You!',
          'Your feedback helps improve our service.',
          [{ text: 'Continue', onPress: handlePayment }]
        );
      } else {
        throw new Error(result.message || 'Failed to submit rating');
      }
    } catch (error) {
      console.error('Rating submission error:', error);
      Alert.alert('Error', 'Failed to submit rating. You can still proceed to payment.');
      handlePayment();
    } finally {
      setSubmitting(false);
    }
  };

  const handlePayment = () => {
    if (!session) {
      Alert.alert('Error', 'Session information missing');
      return;
    }

    router.push({
      pathname: '/payment',
      params: { 
        amount: session.cost.toString(),
        professional: JSON.stringify({
          id: session.professionalId,
          name: session.professionalName
        }),
        consultationType: session.consultationType,
        sessionId: session.id
      }
    });
  };

  const skipRatingAndPay = () => {
    Alert.alert(
      'Skip Rating?',
      'You can rate the professional later from your session history.',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Skip & Pay', onPress: handlePayment }
      ]
    );
  };

  const calculateCostBreakdown = () => {
    if (!session) return { professionalFee: 0, platformFee: 0, total: 0 };
    
    const professionalFee = session.cost * 0.85; // 85% to professional
    const platformFee = session.cost * 0.15; // 15% platform fee
    const total = session.cost;
    
    return { professionalFee, platformFee, total };
  };

  const formatDuration = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    
    if (hours > 0) {
      return `${hours}h ${mins}m`;
    }
    return `${mins}m`;
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#007AFF" />
          <Text style={styles.loadingText}>Loading session summary...</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (!session) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.errorContainer}>
          <Ionicons name="alert-circle" size={64} color="#DC2626" />
          <Text style={styles.errorTitle}>Session Not Found</Text>
          <Text style={styles.errorText}>
            Unable to load session details. Please check your session history.
          </Text>
          <TouchableOpacity 
            style={styles.homeButton}
            onPress={() => router.push('/dashboard')}
          >
            <Text style={styles.homeButtonText}>Go to Dashboard</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  const costBreakdown = calculateCostBreakdown();

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        {/* Success Icon & Title */}
        <View style={styles.successHeader}>
          <View style={styles.successIcon}>
            <Ionicons name="checkmark-circle" size={80} color="#10B981" />
          </View>
          <Text style={styles.title}>Session Complete!</Text>
          <Text style={styles.subtitle}>
            Thank you for your consultation with {session.professionalName}
          </Text>
        </View>

        {/* Session Summary */}
        <View style={styles.summaryCard}>
          <Text style={styles.summaryTitle}>Session Summary</Text>
          
          <View style={styles.summaryRow}>
            <View style={styles.summaryItem}>
              <Ionicons name="time" size={20} color="#6B7280" />
              <Text style={styles.summaryLabel}>Duration</Text>
              <Text style={styles.summaryValue}>{formatDuration(session.duration)}</Text>
            </View>
            
            <View style={styles.summaryItem}>
              <Ionicons name="chatbubble" size={20} color="#6B7280" />
              <Text style={styles.summaryLabel}>Type</Text>
              <Text style={styles.summaryValue}>
                {session.consultationType.charAt(0).toUpperCase() + session.consultationType.slice(1)}
              </Text>
            </View>
          </View>

          {/* Cost Breakdown */}
          <View style={styles.costSection}>
            <Text style={styles.costTitle}>Cost Breakdown</Text>
            
            <View style={styles.costRow}>
              <Text style={styles.costLabel}>Professional Fee</Text>
              <Text style={styles.costValue}>KSH {costBreakdown.professionalFee.toFixed(0)}</Text>
            </View>
            
            <View style={styles.costRow}>
              <Text style={styles.costLabel}>Platform Fee</Text>
              <Text style={styles.costValue}>KSH {costBreakdown.platformFee.toFixed(0)}</Text>
            </View>
            
            <View style={styles.divider} />
            
            <View style={styles.costRow}>
              <Text style={styles.totalLabel}>Total Amount</Text>
              <Text style={styles.totalValue}>KSH {costBreakdown.total.toFixed(0)}</Text>
            </View>
          </View>
        </View>

        {/* Rating Section */}
        <View style={styles.ratingCard}>
          <Text style={styles.ratingTitle}>Rate Your Experience</Text>
          <Text style={styles.ratingSubtitle}>
            How was your session with {session.professionalName}?
          </Text>

          {/* Star Rating */}
          <View style={styles.starsContainer}>
            {[1, 2, 3, 4, 5].map((star) => (
              <TouchableOpacity 
                key={star} 
                onPress={() => setRating(star)}
                style={styles.starButton}
              >
                <Ionicons 
                  name={star <= rating ? "star" : "star-outline"} 
                  size={32} 
                  color={star <= rating ? "#F59E0B" : "#D1D5DB"} 
                />
              </TouchableOpacity>
            ))}
          </View>

          {/* Rating Labels */}
          <View style={styles.ratingLabels}>
            <Text style={styles.ratingLabel}>Poor</Text>
            <Text style={styles.ratingLabel}>Fair</Text>
            <Text style={styles.ratingLabel}>Good</Text>
            <Text style={styles.ratingLabel}>Very Good</Text>
            <Text style={styles.ratingLabel}>Excellent</Text>
          </View>

          {/* Quick Review (Optional) */}
          <View style={styles.reviewSection}>
            <Text style={styles.reviewLabel}>Quick Review (Optional)</Text>
            <TouchableOpacity 
              style={styles.reviewButton}
              onPress={() => router.push({
                pathname: '/write-review',
                params: { 
                  sessionId: session.id,
                  professionalId: session.professionalId 
                }
              })}
            >
              <Text style={styles.reviewButtonText}>
                {review ? 'Edit Review' : 'Write a Review'}
              </Text>
              <Ionicons name="chevron-forward" size={16} color="#6B7280" />
            </TouchableOpacity>
          </View>
        </View>

        {/* Action Buttons */}
        <View style={styles.actionsContainer}>
          <TouchableOpacity 
            style={[
              styles.primaryButton,
              rating === 0 && styles.primaryButtonDisabled
            ]}
            onPress={submitRating}
            disabled={submitting || rating === 0}
          >
            {submitting ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <>
                <Ionicons name="card" size={20} color="#fff" />
                <Text style={styles.primaryButtonText}>
                  Rate & Proceed to Payment
                </Text>
              </>
            )}
          </TouchableOpacity>

          <TouchableOpacity 
            style={styles.secondaryButton}
            onPress={skipRatingAndPay}
            disabled={submitting}
          >
            <Text style={styles.secondaryButtonText}>
              Skip Rating & Pay Now
            </Text>
          </TouchableOpacity>

          <TouchableOpacity 
            style={styles.tertiaryButton}
            onPress={() => router.push('/dashboard')}
          >
            <Text style={styles.tertiaryButtonText}>
              Pay Later
            </Text>
          </TouchableOpacity>
        </View>

        {/* Support Info */}
        <View style={styles.supportInfo}>
          <Ionicons name="help-circle" size={16} color="#6B7280" />
          <Text style={styles.supportText}>
            Need help? Contact support@consultpro.com
          </Text>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { 
    flex: 1, 
    backgroundColor: '#F9FAFB' 
  },
  content: { 
    flex: 1, 
    padding: 20, 
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#6B7280',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  errorTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#DC2626',
    marginTop: 16,
    marginBottom: 8,
  },
  errorText: {
    fontSize: 16,
    color: '#6B7280',
    textAlign: 'center',
    marginBottom: 24,
  },
  homeButton: {
    backgroundColor: '#2563EB',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  homeButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  successHeader: {
    alignItems: 'center',
    marginBottom: 24,
  },
  successIcon: {
    marginBottom: 16,
  },
  title: { 
    fontSize: 28, 
    fontWeight: '800', 
    color: '#111827', 
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#6B7280',
    textAlign: 'center',
  },
  summaryCard: { 
    width: '100%', 
    backgroundColor: '#fff', 
    borderRadius: 16, 
    padding: 20, 
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  summaryTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 16,
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  summaryItem: {
    alignItems: 'center',
    flex: 1,
  },
  summaryLabel: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 8,
    marginBottom: 4,
  },
  summaryValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
  },
  costSection: {
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
    paddingTop: 16,
  },
  costTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 12,
  },
  costRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  costLabel: {
    fontSize: 14,
    color: '#6B7280',
  },
  costValue: {
    fontSize: 14,
    color: '#6B7280',
    fontWeight: '500',
  },
  divider: {
    height: 1,
    backgroundColor: '#E5E7EB',
    marginVertical: 12,
  },
  totalLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
  },
  totalValue: {
    fontSize: 18,
    fontWeight: '700',
    color: '#059669',
  },
  ratingCard: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 20,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  ratingTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 4,
  },
  ratingSubtitle: {
    fontSize: 14,
    color: '#6B7280',
    marginBottom: 20,
  },
  starsContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginBottom: 12,
  },
  starButton: {
    padding: 8,
  },
  ratingLabels: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  ratingLabel: {
    fontSize: 12,
    color: '#6B7280',
    textAlign: 'center',
    flex: 1,
  },
  reviewSection: {
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
    paddingTop: 16,
  },
  reviewLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 8,
  },
  reviewButton: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#F9FAFB',
    padding: 16,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  reviewButtonText: {
    fontSize: 14,
    color: '#6B7280',
  },
  actionsContainer: {
    gap: 12,
    marginBottom: 20,
  },
  primaryButton: {
    backgroundColor: '#2563EB',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 12,
    gap: 8,
  },
  primaryButtonDisabled: {
    backgroundColor: '#9CA3AF',
  },
  primaryButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  secondaryButton: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#E5E7EB',
  },
  secondaryButtonText: {
    color: '#111827',
    fontSize: 16,
    fontWeight: '600',
  },
  tertiaryButton: {
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  tertiaryButtonText: {
    color: '#6B7280',
    fontSize: 16,
    fontWeight: '600',
  },
  supportInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    backgroundColor: '#F3F4F6',
    borderRadius: 8,
    gap: 6,
  },
  supportText: {
    fontSize: 12,
    color: '#6B7280',
  },
});
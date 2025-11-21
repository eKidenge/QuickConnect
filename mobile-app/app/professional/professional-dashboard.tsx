import React, { useState, useEffect, useCallback } from 'react';
import { 
  View, 
  Text, 
  ScrollView, 
  StyleSheet, 
  SafeAreaView, 
  TouchableOpacity, 
  Switch, 
  ActivityIndicator,
  Alert,
  RefreshControl,
  Animated,
  Dimensions
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';
import { BlurView } from 'expo-blur';
import { Ionicons } from '@expo/vector-icons';

const { width } = Dimensions.get('window');

interface DashboardStats {
  today_earnings: number;
  today_sessions: number;
  total_sessions: number;
  average_rating: number;
  monthly_earnings: number;
  pending_requests: number;
  response_rate: number;
  completion_rate: number;
}

interface PendingRequest {
  id: string;
  client_name: string;
  category: string;
  mode: 'chat' | 'audio' | 'video';
  created_at: string;
  client_id: string;
  urgency?: 'low' | 'medium' | 'high';
}

interface ApiConfig {
  baseUrl: string;
  timeout: number;
  retries: number;
}

const API_CONFIG: ApiConfig = {
  baseUrl: process.env.EXPO_PUBLIC_API_URL || 'http://192.168.100.38:8000',
  timeout: 10000,
  retries: 3
};

export default function ProfessionalDashboardScreen() {
  const router = useRouter();
  const { 
    user, 
    professional, 
    logout, 
    setProfessionalOnline, 
    updateProfessionalAvailability,
    isProfessional,
    isProfessionalApproved 
  } = useAuth();
  
  const [isOnline, setIsOnline] = useState(professional?.online_status || false);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [pendingRequests, setPendingRequests] = useState<PendingRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fadeAnim = useState(new Animated.Value(0))[0];
  const slideAnim = useState(new Animated.Value(50))[0];

  const handleLogout = () => {
    router.push('/logout');
  };

  // Enhanced API client with better error handling and debugging
  const apiClient = useCallback(async (endpoint: string, options: RequestInit = {}) => {
    let lastError: Error;
    
    // Debug logging for online status calls
    if (endpoint.includes('online-status') || endpoint.includes('availability')) {
      console.log('🔍 API Call Debug:', {
        url: `${API_CONFIG.baseUrl}${endpoint}`,
        method: options.method || 'GET',
        body: options.body
      });
    }
    
    for (let attempt = 0; attempt < API_CONFIG.retries; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.timeout);

        const response = await fetch(`${API_CONFIG.baseUrl}${endpoint}`, {
          ...options,
          signal: controller.signal,
          headers: {
            'Content-Type': 'application/json',
            ...(user?.token ? { 'Authorization': `Token ${user.token}` } : {}),
            ...options.headers,
          },
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          if (response.status === 401) {
            await logout();
            router.replace('/login');
            throw new Error('Authentication failed');
          }
          if (response.status === 403) {
            throw new Error('Access denied');
          }
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.error || errorData.message || `HTTP ${response.status}`);
        }

        return await response.json();
      } catch (error) {
        lastError = error as Error;
        console.log(`API attempt ${attempt + 1} failed:`, error);
        if (attempt === API_CONFIG.retries - 1) throw lastError;
        await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)));
      }
    }
    
    throw lastError!;
  }, [user?.token, logout, router]);

  const fetchDashboardData = useCallback(async (showLoading = true) => {
    if (!professional?.id) {
      setError('Professional profile not found. Please complete your professional profile setup.');
      if (showLoading) setLoading(false);
      setRefreshing(false);
      return;
    }

    try {
      setError(null);
      if (showLoading) setLoading(true);

      console.log('Fetching dashboard data for professional:', professional.id);
      
      // CORRECTED: Use exact endpoints matching Django URLs
      const [statsData, requestsData] = await Promise.all([
        apiClient(`/api/professional/dashboard-stats/${professional.id}/`),
        apiClient(`/api/professional/pending-requests/${professional.id}/`)
      ]);

      console.log('Dashboard data fetched:', { statsData, requestsData });

      setStats(statsData);
      setPendingRequests(requestsData.requests || []);

      // Animate content in
      Animated.parallel([
        Animated.timing(fadeAnim, {
          toValue: 1,
          duration: 600,
          useNativeDriver: true,
        }),
        Animated.timing(slideAnim, {
          toValue: 0,
          duration: 600,
          useNativeDriver: true,
        }),
      ]).start();

    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to load dashboard data';
      setError(errorMessage);
      
      if (!refreshing && showLoading) {
        Alert.alert('Connection Error', errorMessage, [
          { text: 'Try Again', onPress: () => fetchDashboardData(true) },
          { text: 'Cancel', style: 'cancel' }
        ]);
      }
    } finally {
      if (showLoading) setLoading(false);
      setRefreshing(false);
    }
  }, [professional?.id, apiClient, fadeAnim, slideAnim, refreshing]);

  const fetchPendingRequests = useCallback(async () => {
    if (!professional?.id || !isOnline) return;

    try {
      const data = await apiClient(`/api/professional/pending-requests/${professional.id}/`);
      setPendingRequests(data.requests || []);
    } catch (error) {
      console.error('Error fetching pending requests:', error);
    }
  }, [professional?.id, isOnline, apiClient]);

  // FIXED: Corrected online status update function with proper endpoints
  const handleOnlineStatusChange = async (value: boolean) => {
    if (!professional?.id) {
      Alert.alert('Profile Required', 'Please complete your professional profile first.');
      return;
    }

    setUpdatingStatus(true);
    try {
      // Optimistic update
      setIsOnline(value);
      
      console.log(`🔄 Updating online status to: ${value} for professional: ${professional.id}`);
      
      // CORRECTED: Use exact endpoints matching Django URLs
      await Promise.all([
        // Update online status - CORRECTED ENDPOINT
        apiClient(`/api/professional/online-status/${professional.id}/`, {
          method: 'PATCH',
          body: JSON.stringify({
            is_online: value,
          }),
        }),
        // Update availability - CORRECTED ENDPOINT
        apiClient(`/api/professional/availability/${professional.id}/`, {
          method: 'PATCH',
          body: JSON.stringify({
            is_available: value,
          }),
        })
      ]);

      // Also update through AuthContext if available
      if (setProfessionalOnline) {
        await setProfessionalOnline(value);
      }
      if (updateProfessionalAvailability) {
        await updateProfessionalAvailability(value);
      }

      if (value) {
        // Refresh data when going online
        fetchPendingRequests();
      }

      console.log(`✅ Successfully updated online status to: ${value}`);
    } catch (error) {
      console.error('❌ Error updating online status:', error);
      // Revert on error
      setIsOnline(!value);
      const errorMessage = error instanceof Error ? error.message : 'Network error';
      
      // More specific error handling
      if (errorMessage.includes('404')) {
        Alert.alert(
          'Configuration Error', 
          'Online status update endpoint not found. Please contact support.'
        );
      } else {
        Alert.alert('Error', `Failed to update online status: ${errorMessage}`);
      }
    } finally {
      setUpdatingStatus(false);
    }
  };

  const handleAcceptRequest = async (requestId: string) => {
    if (!professional?.id) {
      Alert.alert('Profile Required', 'Please complete your professional profile first.');
      return;
    }

    try {
      const data = await apiClient(`/api/session/accept/${requestId}/`, {
        method: 'POST',
        body: JSON.stringify({
          professional_id: professional.id,
        }),
      });

      // Remove from local state
      setPendingRequests(prev => prev.filter(req => req.id !== requestId));
      setStats(prev => prev ? { ...prev, pending_requests: (prev.pending_requests || 0) - 1 } : null);
      
      // Navigate to session
      router.push({
		pathname: '/professional-session',
        params: { 
          sessionId: data.session_id,
          clientId: data.client_id,
          mode: data.mode
        }
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Network error';
      Alert.alert('Error', errorMessage);
    }
  };

  const handleDeclineRequest = async (requestId: string) => {
    if (!professional?.id) {
      Alert.alert('Profile Required', 'Please complete your professional profile first.');
      return;
    }

    try {
      await apiClient(`/api/session/decline/${requestId}/`, {
        method: 'POST',
        body: JSON.stringify({
          professional_id: professional.id,
        }),
      });

      // Remove from local state
      setPendingRequests(prev => prev.filter(req => req.id !== requestId));
      setStats(prev => prev ? { ...prev, pending_requests: (prev.pending_requests || 0) - 1 } : null);
    } catch (error) {
      console.error('Error declining request:', error);
      // Still remove from local state for better UX
      setPendingRequests(prev => prev.filter(req => req.id !== requestId));
    }
  };

  const handleWithdrawEarnings = () => {
    if (!professional?.id) {
      Alert.alert('Profile Required', 'Please complete your professional profile first.');
      return;
    }
    router.push('/withdraw-earnings');
  };

  const handleViewAnalytics = () => {
    if (!professional?.id) {
      Alert.alert('Profile Required', 'Please complete your professional profile first.');
      return;
    }
    router.push('/professional-analytics');
  };

  const handleSettings = () => {
    router.push('/professional-settings');
  };

  const handleGoOnline = () => {
    if (!professional?.id) {
      Alert.alert('Profile Required', 'Please complete your professional profile first.');
      return;
    }
    router.push('/professional/incoming');
  };

  const handleSetupProfile = () => {
    router.push('/professional-setup');
  };

  const handleViewEarnings = () => {
    if (!professional?.id) {
      Alert.alert('Profile Required', 'Please complete your professional profile first.');
      return;
    }
    router.push(`/professional-earnings/${professional.id}`);
  };

  const handleViewSessions = () => {
    if (!professional?.id) {
      Alert.alert('Profile Required', 'Please complete your professional profile first.');
      return;
    }
    router.push(`/professional-sessions/${professional.id}`);
  };

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchDashboardData(false);
  }, [fetchDashboardData]);

  // Initial load effect
  useEffect(() => {
    if (professional?.id) {
      console.log('Professional ID found, fetching dashboard data...');
      fetchDashboardData(true);
    } else {
      console.log('No professional ID found, setting loading to false');
      setLoading(false);
    }
  }, [professional?.id, fetchDashboardData]);

  // Polling effect for pending requests
  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (isOnline && professional?.id) {
      console.log('Starting polling for pending requests...');
      fetchPendingRequests();
      interval = setInterval(fetchPendingRequests, 15000);
    }

    return () => {
      if (interval) {
        console.log('Clearing polling interval');
        clearInterval(interval);
      }
    };
  }, [isOnline, professional?.id, fetchPendingRequests]);

  const formatCurrency = (amount: number) => {
    return `KSH ${amount?.toFixed(0)?.replace(/\B(?=(\d{3})+(?!\d))/g, ',') || '0'}`;
  };

  const getModeIcon = (mode: string) => {
    switch (mode) {
      case 'chat': return '💬';
      case 'audio': return '🎤';
      case 'video': return '📹';
      default: return '❓';
    }
  };

  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case 'high': return '#EF4444';
      case 'medium': return '#F59E0B';
      case 'low': return '#10B981';
      default: return '#6B7280';
    }
  };

  const renderStatsCard = (value: string, label: string, icon: string, color: string) => (
    <View style={[styles.statCard, { borderLeftColor: color }]}>
      <Text style={styles.statIcon}>{icon}</Text>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );

  // Show profile setup if user is professional but no profile exists
  if (isProfessional && !professional) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.setupContainer}>
          <Ionicons name="person-add-outline" size={80} color="#6366F1" />
          <Text style={styles.setupTitle}>Professional Profile Required</Text>
          <Text style={styles.setupText}>
            You need to set up your professional profile before accessing the dashboard.
          </Text>
          <TouchableOpacity style={styles.setupButton} onPress={handleSetupProfile}>
            <Text style={styles.setupButtonText}>Set Up Profile</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  if (loading && !refreshing) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#6366F1" />
          <Text style={styles.loadingText}>Loading your dashboard...</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (error && !stats) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.errorContainer}>
          <Ionicons name="wifi-outline" size={64} color="#9CA3AF" />
          <Text style={styles.errorTitle}>Connection Error</Text>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity style={styles.retryButton} onPress={() => fetchDashboardData(true)}>
            <Text style={styles.retryButtonText}>Try Again</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <BlurView intensity={80} tint="light" style={styles.header}>
        <View style={styles.headerContent}>
          <View style={styles.headerInfo}>
            <Text style={styles.title}>Professional Dashboard</Text>
            <Text style={styles.subtitle}>
              {professional?.name || user?.first_name || 'Professional'} • {professional?.specialization || 'Not specified'}
            </Text>
          </View>
          <View style={styles.headerActions}>
            <View style={styles.statusToggle}>
              <Text style={[styles.statusLabel, isOnline && styles.statusOnline]}>
                {isOnline ? '🟢 Online' : '⚫ Offline'}
              </Text>
              <Switch 
                value={isOnline} 
                onValueChange={handleOnlineStatusChange}
                disabled={updatingStatus || !professional}
                trackColor={{ false: '#D1D5DB', true: '#10B981' }}
                thumbColor={isOnline ? '#FFFFFF' : '#FFFFFF'}
              />
              {updatingStatus && (
                <ActivityIndicator size="small" color="#6366F1" style={styles.statusLoader} />
              )}
            </View>
            <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
              <Text style={styles.logoutText}>Logout</Text>
            </TouchableOpacity>
          </View>
        </View>
      </BlurView>

      <ScrollView 
        style={styles.scroll} 
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl 
            refreshing={refreshing} 
            onRefresh={onRefresh}
            colors={['#6366F1']}
            tintColor="#6366F1"
          />
        }
      >
        <Animated.View 
          style={[
            styles.animatedContent,
            {
              opacity: fadeAnim,
              transform: [{ translateY: slideAnim }]
            }
          ]}
        >
          {/* Earnings Card */}
          <View style={styles.earningsCard}>
            <View style={styles.earningsHeader}>
              <Text style={styles.earningsTitle}>Today's Earnings</Text>
              <Ionicons name="trending-up" size={20} color="#BFDBFE" />
            </View>
            <Text style={styles.earningsAmount}>
              {formatCurrency(stats?.today_earnings || 0)}
            </Text>
            <View style={styles.earningsFooter}>
              <Text style={styles.earningsSubtext}>
                {stats?.today_sessions || 0} session{stats?.today_sessions !== 1 ? 's' : ''} completed
              </Text>
              {stats?.response_rate && (
                <View style={styles.earningsBadge}>
                  <Text style={styles.earningsBadgeText}>
                    {(stats.response_rate).toFixed(0)}% response rate
                  </Text>
                </View>
              )}
            </View>
          </View>

          {/* Stats Grid */}
          <ScrollView 
            horizontal 
            showsHorizontalScrollIndicator={false}
            style={styles.statsScroll}
            contentContainerStyle={styles.statsScrollContent}
          >
            {renderStatsCard(
              String(stats?.total_sessions || 0), 
              'Total Sessions', 
              '📊', 
              '#6366F1'
            )}
            {renderStatsCard(
              stats?.average_rating ? `${stats.average_rating.toFixed(1)} ⭐` : 'N/A', 
              'Average Rating', 
              '⭐', 
              '#F59E0B'
            )}
            {renderStatsCard(
              formatCurrency(stats?.monthly_earnings || 0), 
              'Monthly Earnings', 
              '💰', 
              '#10B981'
            )}
            {renderStatsCard(
              `${(stats?.completion_rate || 0).toFixed(0)}%`, 
              'Completion Rate', 
              '✅', 
              '#8B5CF6'
            )}
          </ScrollView>

          {/* Pending Requests Section */}
          {isOnline && (
            <View style={styles.section}>
              <View style={styles.sectionHeader}>
                <Text style={styles.sectionTitle}>Pending Requests</Text>
                <View style={styles.badgeContainer}>
                  <Text style={styles.sectionBadge}>
                    {pendingRequests.length}
                  </Text>
                </View>
              </View>
              
              {pendingRequests.length === 0 ? (
                <View style={styles.emptyState}>
                  <Ionicons name="time-outline" size={48} color="#9CA3AF" />
                  <Text style={styles.emptyText}>No pending requests</Text>
                  <Text style={styles.emptySubtext}>
                    You'll see new requests here when clients need your help
                  </Text>
                </View>
              ) : (
                pendingRequests.map((request) => (
                  <View 
                    key={request.id} 
                    style={[
                      styles.requestCard,
                      { borderLeftColor: getUrgencyColor(request.urgency || 'medium') }
                    ]}
                  >
                    <View style={styles.requestHeader}>
                      <View style={styles.requestInfo}>
                        <Text style={styles.requestName}>{request.client_name}</Text>
                        <View style={styles.requestMeta}>
                          <Text style={styles.requestType}>
                            {getModeIcon(request.mode)} {request.mode.charAt(0).toUpperCase() + request.mode.slice(1)}
                          </Text>
                          <Text style={styles.requestCategory}>• {request.category}</Text>
                        </View>
                      </View>
                      <Text style={styles.requestTime}>
                        {new Date(request.created_at).toLocaleTimeString([], { 
                          hour: '2-digit', 
                          minute: '2-digit' 
                        })}
                      </Text>
                    </View>
                    <View style={styles.requestActions}>
                      <TouchableOpacity 
                        style={[styles.actionButton, styles.declineBtn]}
                        onPress={() => handleDeclineRequest(request.id)}
                      >
                        <Ionicons name="close" size={16} color="#6B7280" />
                        <Text style={styles.declineText}>Decline</Text>
                      </TouchableOpacity>
                      <TouchableOpacity 
                        style={[styles.actionButton, styles.acceptBtn]}
                        onPress={() => handleAcceptRequest(request.id)}
                      >
                        <Ionicons name="checkmark" size={16} color="#fff" />
                        <Text style={styles.acceptText}>Accept</Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                ))
              )}
              
              {isOnline && pendingRequests.length > 0 && (
                <TouchableOpacity 
                  style={styles.goOnlineBtn}
                  onPress={handleGoOnline}
                >
                  <Ionicons name="radio-button-on" size={20} color="#fff" />
                  <Text style={styles.goOnlineText}>Go to Live Requests</Text>
                </TouchableOpacity>
              )}
            </View>
          )}

          {/* Quick Actions */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Quick Actions</Text>
            
            <TouchableOpacity style={styles.actionCard} onPress={handleWithdrawEarnings}>
              <View style={[styles.actionIcon, { backgroundColor: '#ECFDF5' }]}>
                <Ionicons name="cash-outline" size={24} color="#10B981" />
              </View>
              <View style={styles.actionTextContainer}>
                <Text style={styles.actionText}>Withdraw Earnings</Text>
                <Text style={styles.actionSubtext}>
                  Available: {formatCurrency(stats?.today_earnings || 0)}
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#9CA3AF" />
            </TouchableOpacity>
            
            <TouchableOpacity style={styles.actionCard} onPress={handleViewAnalytics}>
              <View style={[styles.actionIcon, { backgroundColor: '#EFF6FF' }]}>
                <Ionicons name="analytics-outline" size={24} color="#3B82F6" />
              </View>
              <View style={styles.actionTextContainer}>
                <Text style={styles.actionText}>View Analytics</Text>
                <Text style={styles.actionSubtext}>Detailed performance insights</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#9CA3AF" />
            </TouchableOpacity>

            <TouchableOpacity style={styles.actionCard} onPress={handleViewEarnings}>
              <View style={[styles.actionIcon, { backgroundColor: '#FEF3C7' }]}>
                <Ionicons name="wallet-outline" size={24} color="#D97706" />
              </View>
              <View style={styles.actionTextContainer}>
                <Text style={styles.actionText}>Earnings Details</Text>
                <Text style={styles.actionSubtext}>View detailed earnings breakdown</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#9CA3AF" />
            </TouchableOpacity>

            <TouchableOpacity style={styles.actionCard} onPress={handleViewSessions}>
              <View style={[styles.actionIcon, { backgroundColor: '#E0E7FF' }]}>
                <Ionicons name="calendar-outline" size={24} color="#4F46E5" />
              </View>
              <View style={styles.actionTextContainer}>
                <Text style={styles.actionText}>Session History</Text>
                <Text style={styles.actionSubtext}>View all your sessions</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#9CA3AF" />
            </TouchableOpacity>
            
            <TouchableOpacity style={styles.actionCard} onPress={handleSettings}>
              <View style={[styles.actionIcon, { backgroundColor: '#F3F4F6' }]}>
                <Ionicons name="settings-outline" size={24} color="#6B7280" />
              </View>
              <View style={styles.actionTextContainer}>
                <Text style={styles.actionText}>Professional Settings</Text>
                <Text style={styles.actionSubtext}>Update your profile and preferences</Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color="#9CA3AF" />
            </TouchableOpacity>
          </View>

          {/* Professional Status */}
          <View style={styles.statusCard}>
            <Text style={styles.statusCardTitle}>Professional Status</Text>
            <View style={styles.statusItem}>
              <Text style={styles.statusLabel}>Verification Status</Text>
              <Text style={[
                styles.statusValue, 
                professional?.is_approved ? styles.statusApproved : styles.statusPending
              ]}>
                {professional?.is_approved ? 'Verified' : 'Pending Review'}
              </Text>
            </View>
            <View style={styles.statusItem}>
              <Text style={styles.statusLabel}>Specialization</Text>
              <Text style={styles.statusValue}>{professional?.specialization || 'Not set'}</Text>
            </View>
            <View style={[styles.statusItem, styles.statusItemLast]}>
              <Text style={styles.statusLabel}>Session Rate</Text>
              <Text style={styles.statusValue}>KSH {professional?.rate || 0}/min</Text>
            </View>
          </View>
        </Animated.View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { 
    flex: 1, 
    backgroundColor: '#F9FAFB' 
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 16,
  },
  loadingText: {
    fontSize: 16,
    color: '#6B7280',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
    gap: 16,
  },
  errorTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#374151',
  },
  errorText: {
    fontSize: 14,
    color: '#6B7280',
    textAlign: 'center',
    lineHeight: 20,
  },
  retryButton: {
    backgroundColor: '#6366F1',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 12,
    marginTop: 8,
  },
  retryButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  setupContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
    gap: 24,
  },
  setupTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#111827',
    textAlign: 'center',
  },
  setupText: {
    fontSize: 16,
    color: '#6B7280',
    textAlign: 'center',
    lineHeight: 24,
  },
  setupButton: {
    backgroundColor: '#6366F1',
    paddingHorizontal: 32,
    paddingVertical: 16,
    borderRadius: 12,
    width: '100%',
    alignItems: 'center',
  },
  setupButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  header: {
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(229, 231, 235, 0.5)',
  },
  headerContent: {
    padding: 20,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  headerInfo: {
    flex: 1,
  },
  headerActions: {
    alignItems: 'flex-end',
    gap: 12,
  },
  title: { 
    fontSize: 24, 
    fontWeight: '800', 
    color: '#111827', 
    marginBottom: 4 
  },
  subtitle: {
    fontSize: 14,
    color: '#6B7280',
  },
  statusToggle: { 
    alignItems: 'center',
    gap: 8,
  },
  statusLabel: { 
    fontSize: 14, 
    fontWeight: '600', 
    color: '#6B7280' 
  },
  statusOnline: {
    color: '#10B981',
  },
  statusLoader: {
    position: 'absolute',
    bottom: -20,
  },
  logoutButton: {
    backgroundColor: '#FF3B30',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
  },
  logoutText: {
    color: 'white',
    fontWeight: '600',
    fontSize: 12,
  },
  scroll: { 
    flex: 1, 
  },
  animatedContent: {
    padding: 20,
  },
  earningsCard: { 
    backgroundColor: '#4F46E5', 
    borderRadius: 20, 
    padding: 24, 
    marginBottom: 20,
    shadowColor: '#4F46E5',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.25,
    shadowRadius: 16,
    elevation: 8,
  },
  earningsHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  earningsTitle: { 
    fontSize: 16, 
    color: '#C7D2FE', 
    fontWeight: '600',
  },
  earningsAmount: { 
    fontSize: 36, 
    fontWeight: '800', 
    color: '#fff', 
    marginBottom: 16 
  },
  earningsFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  earningsSubtext: { 
    fontSize: 14, 
    color: '#C7D2FE',
    flex: 1,
  },
  earningsBadge: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  earningsBadgeText: {
    fontSize: 12,
    color: '#fff',
    fontWeight: '600',
  },
  statsScroll: {
    marginBottom: 20,
  },
  statsScrollContent: {
    gap: 12,
    paddingRight: 20,
  },
  statCard: { 
    backgroundColor: '#fff', 
    padding: 20, 
    borderRadius: 16, 
    width: 140,
    borderLeftWidth: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  statIcon: {
    fontSize: 20,
    marginBottom: 8,
  },
  statValue: { 
    fontSize: 20, 
    fontWeight: '800', 
    color: '#111827', 
    marginBottom: 4 
  },
  statLabel: { 
    fontSize: 12, 
    color: '#6B7280', 
    fontWeight: '500',
  },
  section: { 
    marginBottom: 24 
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  sectionTitle: { 
    fontSize: 20, 
    fontWeight: '700', 
    color: '#111827'
  },
  badgeContainer: {
    backgroundColor: '#EF4444',
    borderRadius: 12,
    minWidth: 24,
    height: 24,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 8,
  },
  sectionBadge: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '700',
  },
  requestCard: { 
    backgroundColor: '#fff', 
    borderRadius: 16, 
    padding: 16, 
    marginBottom: 12,
    borderLeftWidth: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 2,
  },
  requestHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  requestInfo: {
    flex: 1,
  },
  requestName: { 
    fontSize: 16, 
    fontWeight: '700', 
    color: '#111827', 
    marginBottom: 4 
  },
  requestMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  requestType: { 
    fontSize: 13, 
    color: '#6366F1',
    fontWeight: '500',
  },
  requestCategory: {
    fontSize: 13,
    color: '#6B7280',
  },
  requestTime: {
    fontSize: 12,
    color: '#9CA3AF',
    fontWeight: '500',
  },
  requestActions: { 
    flexDirection: 'row', 
    gap: 8 
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    padding: 12,
    borderRadius: 12,
  },
  acceptBtn: { 
    backgroundColor: '#10B981',
  },
  acceptText: { 
    color: '#fff', 
    fontWeight: '600',
    fontSize: 14,
  },
  declineBtn: { 
    backgroundColor: '#F3F4F6',
  },
  declineText: { 
    color: '#6B7280', 
    fontWeight: '600',
    fontSize: 14,
  },
  actionCard: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    backgroundColor: '#fff', 
    padding: 16, 
    borderRadius: 16, 
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 2,
  },
  actionIcon: {
    width: 48,
    height: 48,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  actionTextContainer: {
	flex: 1,
  },
  actionText: { 
    fontSize: 16, 
    fontWeight: '600', 
    color: '#111827' 
  },
  actionSubtext: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 2,
  },
  emptyState: {
    backgroundColor: '#fff',
    padding: 40,
    borderRadius: 16,
    alignItems: 'center',
    gap: 12,
  },
  emptyText: {
    fontSize: 16,
    color: '#6B7280',
    fontWeight: '600',
  },
  emptySubtext: {
    fontSize: 14,
    color: '#9CA3AF',
    textAlign: 'center',
    lineHeight: 20,
  },
  goOnlineBtn: {
    backgroundColor: '#6366F1',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    padding: 16,
    borderRadius: 16,
    marginTop: 8,
    shadowColor: '#6366F1',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  goOnlineText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },
  statusCard: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 20,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 2,
  },
  statusCardTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 16,
  },
  statusItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  statusItemLast: {
    borderBottomWidth: 0,
  },
  statusLabel: {
    fontSize: 14,
    color: '#6B7280',
    fontWeight: '500',
  },
  statusValue: {
    fontSize: 14,
    fontWeight: '600',
  },
  statusApproved: {
    color: '#10B981',
  },
  statusPending: {
    color: '#F59E0B',
  },
});
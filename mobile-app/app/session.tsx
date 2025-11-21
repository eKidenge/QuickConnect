// app/session.tsx
import { View, Text, StyleSheet, SafeAreaView, TouchableOpacity, Alert, ActivityIndicator } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { Ionicons } from '@expo/vector-icons';

interface Professional {
  id: string;
  name: string;
  rating: number;
  experience: number;
  sessionCount: number;
  rate: string;
  category: string;
  isOnline: boolean;
  profileImage: string;
  responseTime: string;
}

interface Session {
  id: string;
  professionalId: string;
  clientId: string;
  consultationType: 'chat' | 'voice' | 'video';
  status: 'active' | 'completed' | 'cancelled';
  startTime: string;
  endTime: string | null;
  rate: string;
  categoryName: string;
  paymentStatus: 'paid' | 'pending' | 'failed';
}

export default function SessionScreen() {
  const router = useRouter();
  const params = useLocalSearchParams();
  const [session, setSession] = useState<Session | null>(null);
  const [professional, setProfessional] = useState<Professional | null>(null);
  const [loading, setLoading] = useState(true);
  const [startingChat, setStartingChat] = useState(false);
  const [startingCall, setStartingCall] = useState(false);
  const [sessionTimer, setSessionTimer] = useState(0);
  const [isSessionActive, setIsSessionActive] = useState(false);

  useEffect(() => {
    initializeSession();
  }, [params]);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isSessionActive) {
      interval = setInterval(() => {
        setSessionTimer(prev => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isSessionActive]);

  const initializeSession = async () => {
    try {
      setLoading(true);
      
      if (params.professional && params.consultationType) {
        const professionalData = JSON.parse(params.professional as string);
        const consultationType = params.consultationType as 'chat' | 'voice' | 'video';
        
        setProfessional(professionalData);

        // Create a new session in database
        const sessionResponse = await fetch('/api/sessions/create', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            professionalId: professionalData.id,
            consultationType: consultationType,
            rate: professionalData.rate,
            categoryName: professionalData.category
          })
        });

        const sessionData = await sessionResponse.json();
        
        if (sessionData.success) {
          setSession(sessionData.session);
          setIsSessionActive(true);
          
          // Send notification to professional
          await notifyProfessional(professionalData.id, sessionData.session.id, consultationType);
        } else {
          throw new Error('Failed to create session');
        }
      }
    } catch (error) {
      console.error('Session initialization error:', error);
      Alert.alert('Error', 'Failed to start session. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const notifyProfessional = async (professionalId: string, sessionId: string, type: string) => {
    try {
      await fetch('/api/notifications/send', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          professionalId: professionalId,
          sessionId: sessionId,
          type: type,
          message: `New ${type} consultation request`
        })
      });
    } catch (error) {
      console.error('Notification error:', error);
    }
  };

  const startChatSession = async () => {
    try {
      setStartingChat(true);
      
      if (!session) {
        Alert.alert('Error', 'Session not initialized');
        return;
      }

      // Update session status to active in database
      const response = await fetch('/api/sessions/update', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sessionId: session.id,
          status: 'active',
          action: 'start_chat'
        })
      });

      const result = await response.json();

      if (result.success) {
        // Navigate to real chat interface
        router.push({
          pathname: '/chat-interface',
          params: {
            sessionId: session.id,
            professional: JSON.stringify(professional),
            consultationType: 'chat'
          }
        });
      } else {
        throw new Error('Failed to start chat session');
      }
    } catch (error) {
      console.error('Chat session error:', error);
      Alert.alert('Error', 'Failed to start chat. Please try again.');
    } finally {
      setStartingChat(false);
    }
  };

  const startVoiceCall = async () => {
    try {
      setStartingCall(true);
      
      if (!session) {
        Alert.alert('Error', 'Session not initialized');
        return;
      }

      // Check if professional is available for voice call
      const availabilityCheck = await fetch(`/api/professionals/${professional?.id}/availability?type=voice`);
      const availability = await availabilityCheck.json();

      if (!availability.available) {
        Alert.alert('Not Available', 'Professional is not available for voice calls at the moment.');
        return;
      }

      // Update session for voice call
      const response = await fetch('/api/sessions/update', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sessionId: session.id,
          status: 'active',
          action: 'start_voice_call'
        })
      });

      const result = await response.json();

      if (result.success) {
        // Initiate voice call connection
        const callResponse = await fetch('/api/calls/initiate-voice', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            sessionId: session.id,
            professionalId: professional?.id,
            clientId: 'current-user-id' // Replace with actual client ID
          })
        });

        const callData = await callResponse.json();

        if (callData.success) {
          // Navigate to voice call interface
          router.push({
            pathname: '/voice-call',
            params: {
              sessionId: session.id,
              professional: JSON.stringify(professional),
              callData: JSON.stringify(callData.call)
            }
          });
        } else {
          throw new Error('Failed to initiate voice call');
        }
      } else {
        throw new Error('Failed to update session for voice call');
      }
    } catch (error) {
      console.error('Voice call error:', error);
      Alert.alert('Error', 'Failed to start voice call. Please try again.');
    } finally {
      setStartingCall(false);
    }
  };

  const startVideoCall = async () => {
    try {
      setStartingCall(true);
      
      if (!session) {
        Alert.alert('Error', 'Session not initialized');
        return;
      }

      // Check if professional is available for video call
      const availabilityCheck = await fetch(`/api/professionals/${professional?.id}/availability?type=video`);
      const availability = await availabilityCheck.json();

      if (!availability.available) {
        Alert.alert('Not Available', 'Professional is not available for video calls at the moment.');
        return;
      }

      // Update session for video call
      const response = await fetch('/api/sessions/update', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sessionId: session.id,
          status: 'active',
          action: 'start_video_call'
        })
      });

      const result = await response.json();

      if (result.success) {
        // Initiate video call connection
        const callResponse = await fetch('/api/calls/initiate-video', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            sessionId: session.id,
            professionalId: professional?.id,
            clientId: 'current-user-id' // Replace with actual client ID
          })
        });

        const callData = await callResponse.json();

        if (callData.success) {
          // Navigate to video call interface
          router.push({
            pathname: '/video-call',
            params: {
              sessionId: session.id,
              professional: JSON.stringify(professional),
              callData: JSON.stringify(callData.call)
            }
          });
        } else {
          throw new Error('Failed to initiate video call');
        }
      } else {
        throw new Error('Failed to update session for video call');
      }
    } catch (error) {
      console.error('Video call error:', error);
      Alert.alert('Error', 'Failed to start video call. Please try again.');
    } finally {
      setStartingCall(false);
    }
  };

  const endSession = async () => {
    try {
      if (!session) return;

      Alert.alert(
        'End Session',
        'Are you sure you want to end this session?',
        [
          { text: 'Cancel', style: 'cancel' },
          { 
            text: 'End Session', 
            style: 'destructive',
            onPress: async () => {
              const response = await fetch('/api/sessions/end', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                  sessionId: session.id,
                  endTime: new Date().toISOString()
                })
              });

              const result = await response.json();
              
              if (result.success) {
                setIsSessionActive(false);
                Alert.alert('Session Ended', 'Your consultation session has been completed.');
                router.push('/');
              }
            }
          }
        ]
      );
    } catch (error) {
      console.error('End session error:', error);
      Alert.alert('Error', 'Failed to end session.');
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#007AFF" />
          <Text style={styles.loadingText}>Starting your session...</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (!session || !professional) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.errorContainer}>
          <Ionicons name="alert-circle" size={64} color="#DC2626" />
          <Text style={styles.errorText}>Session not found</Text>
          <TouchableOpacity 
            style={styles.retryButton}
            onPress={initializeSession}
          >
            <Text style={styles.retryButtonText}>Try Again</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#1F2937" />
        </TouchableOpacity>
        <View style={styles.headerCenter}>
          <Text style={styles.title}>Consultation Session</Text>
          {isSessionActive && (
            <Text style={styles.timer}>Session Time: {formatTime(sessionTimer)}</Text>
          )}
        </View>
        <TouchableOpacity onPress={endSession} style={styles.endButton}>
          <Text style={styles.endButtonText}>End</Text>
        </TouchableOpacity>
      </View>

      {/* Content */}
      <View style={styles.content}>
        <View style={styles.successSection}>
          <Ionicons name="checkmark-circle" size={80} color="#10B981" />
          <Text style={styles.successTitle}>You're Connected!</Text>
          <Text style={styles.successSubtitle}>
            Session with {professional.name} is ready
          </Text>
        </View>

        {/* Professional Card */}
        <View style={styles.professionalCard}>
          <View style={styles.professionalHeader}>
            <View style={styles.professionalInfo}>
              <Text style={styles.professionalName}>{professional.name}</Text>
              <Text style={styles.professionalCategory}>{professional.category} Specialist</Text>
              
              <View style={styles.stats}>
                <View style={styles.stat}>
                  <Ionicons name="star" size={16} color="#F59E0B" />
                  <Text style={styles.statText}>{professional.rating}</Text>
                </View>
                <View style={styles.stat}>
                  <Ionicons name="briefcase" size={16} color="#2563EB" />
                  <Text style={styles.statText}>{professional.experience} yrs</Text>
                </View>
                <View style={styles.stat}>
                  <Ionicons name="people" size={16} color="#059669" />
                  <Text style={styles.statText}>{professional.sessionCount}+ sessions</Text>
                </View>
              </View>
            </View>
            
            <View style={styles.statusIndicator}>
              <View style={[
                styles.statusDot,
                professional.isOnline ? styles.onlineDot : styles.offlineDot
              ]} />
              <Text style={styles.statusText}>
                {professional.isOnline ? 'Online' : 'Offline'}
              </Text>
            </View>
          </View>

          <View style={styles.sessionInfo}>
            <Text style={styles.sessionType}>
              {session.consultationType.charAt(0).toUpperCase() + session.consultationType.slice(1)} Consultation
            </Text>
            <Text style={styles.rate}>{professional.rate}</Text>
          </View>
        </View>

        {/* Connection Options */}
        <View style={styles.connectionSection}>
          <Text style={styles.connectionTitle}>Start Consultation</Text>
          
          {/* Chat Button */}
          <TouchableOpacity 
            style={[styles.optionButton, styles.chatButton]}
            onPress={startChatSession}
            disabled={startingChat}
          >
            {startingChat ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <>
                <Ionicons name="chatbubble-ellipses" size={24} color="#fff" />
                <Text style={styles.optionButtonText}>Start Chat Session</Text>
              </>
            )}
          </TouchableOpacity>

          {/* Voice Call Button */}
          <TouchableOpacity 
            style={[styles.optionButton, styles.voiceButton]}
            onPress={startVoiceCall}
            disabled={startingCall}
          >
            {startingCall ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <>
                <Ionicons name="call" size={24} color="#fff" />
                <Text style={styles.optionButtonText}>Start Voice Call</Text>
              </>
            )}
          </TouchableOpacity>

          {/* Video Call Button */}
          <TouchableOpacity 
            style={[styles.optionButton, styles.videoButton]}
            onPress={startVideoCall}
            disabled={startingCall}
          >
            {startingCall ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <>
                <Ionicons name="videocam" size={24} color="#fff" />
                <Text style={styles.optionButtonText}>Start Video Call</Text>
              </>
            )}
          </TouchableOpacity>
        </View>

        {/* Session Details */}
        <View style={styles.detailsSection}>
          <Text style={styles.detailsTitle}>Session Details</Text>
          <View style={styles.detailItem}>
            <Ionicons name="time" size={16} color="#6B7280" />
            <Text style={styles.detailLabel}>Started:</Text>
            <Text style={styles.detailValue}>
              {new Date(session.startTime).toLocaleTimeString()}
            </Text>
          </View>
          <View style={styles.detailItem}>
            <Ionicons name="card" size={16} color="#6B7280" />
            <Text style={styles.detailLabel}>Payment:</Text>
            <Text style={[styles.detailValue, styles.paidText]}>Paid</Text>
          </View>
          <View style={styles.detailItem}>
            <Ionicons name="shield-checkmark" size={16} color="#6B7280" />
            <Text style={styles.detailLabel}>Security:</Text>
            <Text style={styles.detailValue}>End-to-end encrypted</Text>
          </View>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F9FAFB',
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
  errorText: {
    fontSize: 18,
    color: '#DC2626',
    marginTop: 16,
    marginBottom: 24,
  },
  retryButton: {
    backgroundColor: '#2563EB',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 20,
    backgroundColor: '#FFFFFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  backButton: {
    padding: 8,
  },
  headerCenter: {
    alignItems: 'center',
    flex: 1,
  },
  title: {
    fontSize: 18,
    fontWeight: '700',
    color: '#111827',
  },
  timer: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 4,
  },
  endButton: {
    padding: 8,
  },
  endButtonText: {
    color: '#DC2626',
    fontSize: 16,
    fontWeight: '600',
  },
  content: {
    flex: 1,
    padding: 20,
  },
  successSection: {
    alignItems: 'center',
    marginBottom: 24,
  },
  successTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: '#059669',
    marginTop: 16,
    marginBottom: 8,
  },
  successSubtitle: {
    fontSize: 16,
    color: '#6B7280',
    textAlign: 'center',
  },
  professionalCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 20,
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  professionalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 16,
  },
  professionalInfo: {
    flex: 1,
  },
  professionalName: {
    fontSize: 20,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 4,
  },
  professionalCategory: {
    fontSize: 16,
    color: '#6B7280',
    marginBottom: 12,
  },
  stats: {
    flexDirection: 'row',
    gap: 16,
  },
  stat: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  statText: {
    fontSize: 14,
    color: '#6B7280',
    fontWeight: '500',
  },
  statusIndicator: {
    alignItems: 'center',
  },
  statusDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginBottom: 4,
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
  sessionInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
  },
  sessionType: {
    fontSize: 16,
    color: '#1F2937',
    fontWeight: '600',
  },
  rate: {
    fontSize: 18,
    fontWeight: '700',
    color: '#DC2626',
  },
  connectionSection: {
    marginBottom: 24,
  },
  connectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 16,
  },
  optionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    gap: 8,
  },
  chatButton: {
    backgroundColor: '#2563EB',
  },
  voiceButton: {
    backgroundColor: '#059669',
  },
  videoButton: {
    backgroundColor: '#DC2626',
  },
  optionButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  detailsSection: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
  },
  detailsTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 12,
  },
  detailItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
    gap: 8,
  },
  detailLabel: {
    fontSize: 14,
    color: '#6B7280',
    marginLeft: 4,
    width: 80,
  },
  detailValue: {
    fontSize: 14,
    color: '#1F2937',
    fontWeight: '500',
    flex: 1,
  },
  paidText: {
    color: '#059669',
  },
});
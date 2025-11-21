import React, { useState, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, TextInput, Alert, ScrollView, ActivityIndicator } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useProfessional } from '../../contexts/ProfessionalContext';

interface Message {
  id: string;
  content: string;
  sender: 'client' | 'professional';
  timestamp: string;
}

interface Session {
  id: string;
  client_id: string;
  client_name: string;
  professional_id: string;
  category: string;
  mode: 'chat' | 'audio' | 'video';
  status: 'active' | 'ended' | 'completed';
  created_at: string;
}

export default function ProfessionalSessionScreen() {
  const router = useRouter();
  const params = useLocalSearchParams();
  const { professional } = useProfessional();
  
  const sessionId = params.sessionId as string;
  const BASE_URL = 'http://192.168.100.38:8000'; // Your Django server

  const [session, setSession] = useState<Session | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [ending, setEnding] = useState(false);
  const [sending, setSending] = useState(false);
  
  const scrollViewRef = useRef<ScrollView>(null);

  // Load existing session data
  const loadSession = async () => {
    try {
      console.log(`Loading session ${sessionId}...`);
      const response = await fetch(`${BASE_URL}/sessions/${sessionId}/`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data = await response.json();
      
      setSession(data.session);
      setMessages(data.messages || []);
      
    } catch (error) {
      console.error('Error loading session:', error);
      Alert.alert('Error', 'Failed to load session. Please check your connection.');
      router.back();
    } finally {
      setLoading(false);
    }
  };

  // Poll for new messages
  const pollMessages = async () => {
    if (!sessionId || session?.status === 'completed') return;

    try {
      const response = await fetch(`${BASE_URL}/sessions/${sessionId}/messages/`);
      
      if (response.ok) {
        const data = await response.json();
        setMessages(data.messages || []);
      }
    } catch (error) {
      console.error('Error polling messages:', error);
    }
  };

  useEffect(() => {
    loadSession();

    // Poll for new messages every 3 seconds
    const messageInterval = setInterval(pollMessages, 3000);

    return () => clearInterval(messageInterval);
  }, [sessionId]);

  useEffect(() => {
    // Auto-scroll to bottom when new messages arrive
    if (messages.length > 0) {
      setTimeout(() => {
        scrollViewRef.current?.scrollToEnd({ animated: true });
      }, 100);
    }
  }, [messages]);

  const sendMessage = async () => {
    if (!newMessage.trim() || !professional || sending) return;

    setSending(true);
    try {
      const response = await fetch(`${BASE_URL}/sessions/${sessionId}/send-message/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: newMessage.trim(),
          sender: 'professional',
          professional_id: professional.id,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setNewMessage('');
        // Refresh messages to include the new one
        setTimeout(pollMessages, 500);
      } else {
        Alert.alert('Error', data.error || 'Failed to send message');
      }
    } catch (error) {
      Alert.alert('Error', 'Network error sending message');
    } finally {
      setSending(false);
    }
  };

  const endSession = async () => {
    if (!professional) return;
    
    setEnding(true);
    try {
      const response = await fetch(`${BASE_URL}/sessions/${sessionId}/end/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ended_by: 'professional',
          professional_id: professional.id,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        Alert.alert(
          'Session Ended',
          'Session has been completed successfully.',
          [{ text: 'OK', onPress: () => router.replace('/professional/professional-dashboard') }]
        );
      } else {
        Alert.alert('Error', data.error || 'Failed to end session');
      }
    } catch (error) {
      Alert.alert('Error', 'Network error ending session');
    } finally {
      setEnding(false);
    }
  };

  const handleEndSession = () => {
    if (session?.status === 'completed') {
      Alert.alert('Session Already Ended', 'This session has already been completed.');
      return;
    }

    Alert.alert(
      'End Session',
      'Are you sure you want to end this session?',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'End Session', onPress: endSession, style: 'destructive' },
      ]
    );
  };

  const handleCall = () => {
    Alert.alert('Coming Soon', 'Audio call functionality will be implemented soon');
  };

  const handleVideo = () => {
    Alert.alert('Coming Soon', 'Video call functionality will be implemented soon');
  };

  const handleKeyPress = (e: any) => {
    if (e.nativeEvent.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#2196F3" />
        <Text style={styles.loadingText}>Loading session...</Text>
      </View>
    );
  }

  if (!session) {
    return (
      <View style={styles.centerContainer}>
        <Text style={styles.errorText}>Session not found</Text>
        <TouchableOpacity style={styles.button} onPress={() => router.back()}>
          <Text style={styles.buttonText}>Go Back</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerInfo}>
          <Text style={styles.clientName}>Client {session.client_id}</Text>
          <Text style={styles.sessionInfo}>
            {session.category} • {session.mode} • {session.status.toUpperCase()}
          </Text>
        </View>
        <TouchableOpacity 
          style={[
            styles.endButton, 
            (ending || session.status === 'completed') && styles.endButtonDisabled
          ]}
          onPress={handleEndSession}
          disabled={ending || session.status === 'completed'}
        >
          <Text style={styles.endButtonText}>
            {ending ? 'Ending...' : session.status === 'completed' ? 'Ended' : 'End Session'}
          </Text>
        </TouchableOpacity>
      </View>

      {/* Communication Controls */}
      {(session.mode === 'audio' || session.mode === 'video') && (
        <View style={styles.communicationControls}>
          <Text style={styles.controlsTitle}>Communication Mode: {session.mode.toUpperCase()}</Text>
          <View style={styles.controlButtons}>
            {session.mode === 'audio' && (
              <TouchableOpacity style={styles.controlButton} onPress={handleCall}>
                <Text style={styles.controlButtonText}>📞 Start Audio Call</Text>
              </TouchableOpacity>
            )}
            {session.mode === 'video' && (
              <TouchableOpacity style={styles.controlButton} onPress={handleVideo}>
                <Text style={styles.controlButtonText}>📹 Start Video Call</Text>
              </TouchableOpacity>
            )}
          </View>
        </View>
      )}

      {/* Chat Messages */}
      <ScrollView 
        ref={scrollViewRef}
        style={styles.messagesContainer}
        contentContainerStyle={styles.messagesContent}
      >
        {messages.length === 0 ? (
          <View style={styles.noMessages}>
            <Text style={styles.noMessagesText}>No messages yet. Start the conversation!</Text>
          </View>
        ) : (
          messages.map((message) => (
            <View
              key={message.id}
              style={[
                styles.messageBubble,
                message.sender === 'professional' ? styles.myMessage : styles.theirMessage,
              ]}
            >
              <Text style={styles.messageText}>{message.content}</Text>
              <Text style={styles.messageTime}>
                {new Date(message.timestamp).toLocaleTimeString([], { 
                  hour: '2-digit', 
                  minute: '2-digit' 
                })}
              </Text>
            </View>
          ))
        )}
      </ScrollView>

      {/* Message Input */}
      {session.status === 'active' && (
        <View style={styles.inputContainer}>
          <TextInput
            style={styles.textInput}
            value={newMessage}
            onChangeText={setNewMessage}
            placeholder="Type your message..."
            placeholderTextColor="#999"
            multiline
            maxLength={500}
            editable={!sending}
          />
          <TouchableOpacity
            style={[
              styles.sendButton, 
              (!newMessage.trim() || sending) && styles.sendButtonDisabled
            ]}
            onPress={sendMessage}
            disabled={!newMessage.trim() || sending}
          >
            {sending ? (
              <ActivityIndicator size="small" color="white" />
            ) : (
              <Text style={styles.sendButtonText}>Send</Text>
            )}
          </TouchableOpacity>
        </View>
      )}

      {session.status === 'completed' && (
        <View style={styles.sessionEndedBanner}>
          <Text style={styles.sessionEndedText}>This session has ended</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  loadingText: {
    fontSize: 16,
    color: '#666',
    marginTop: 10,
  },
  errorText: {
    fontSize: 18,
    color: '#f44336',
    marginBottom: 20,
    textAlign: 'center',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: 'white',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  headerInfo: {
    flex: 1,
  },
  clientName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  sessionInfo: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  endButton: {
    backgroundColor: '#f44336',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 6,
  },
  endButtonDisabled: {
    backgroundColor: '#ffcdd2',
  },
  endButtonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 14,
  },
  communicationControls: {
    backgroundColor: '#e3f2fd',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#bbdefb',
  },
  controlsTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#1976d2',
    marginBottom: 8,
  },
  controlButtons: {
    flexDirection: 'row',
  },
  controlButton: {
    backgroundColor: '#2196f3',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 6,
    marginRight: 8,
  },
  controlButtonText: {
    color: 'white',
    fontWeight: 'bold',
  },
  messagesContainer: {
    flex: 1,
    padding: 16,
  },
  messagesContent: {
    paddingBottom: 16,
  },
  noMessages: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 40,
  },
  noMessagesText: {
    fontSize: 16,
    color: '#999',
    textAlign: 'center',
	},
  messageBubble: {
    maxWidth: '80%',
    padding: 12,
    borderRadius: 16,
    marginBottom: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  myMessage: {
    alignSelf: 'flex-end',
    backgroundColor: '#dcf8c6',
    borderTopRightRadius: 4,
  },
  theirMessage: {
    alignSelf: 'flex-start',
    backgroundColor: 'white',
    borderTopLeftRadius: 4,
  },
  messageText: {
    fontSize: 16,
    color: '#333',
    lineHeight: 20,
  },
  messageTime: {
    fontSize: 10,
    color: '#666',
    marginTop: 4,
    alignSelf: 'flex-end',
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    backgroundColor: 'white',
    padding: 12,
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  textInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 8,
    marginRight: 8,
    maxHeight: 100,
    fontSize: 16,
    backgroundColor: '#f9f9f9',
  },
  sendButton: {
    backgroundColor: '#2196f3',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 20,
    minWidth: 60,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendButtonDisabled: {
    backgroundColor: '#ccc',
  },
  sendButtonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 14,
  },
  sessionEndedBanner: {
    backgroundColor: '#ffebee',
    padding: 16,
    alignItems: 'center',
  },
  sessionEndedText: {
    color: '#c62828',
    fontWeight: 'bold',
  },
  button: {
    backgroundColor: '#2196F3',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
    minWidth: 120,
  },
  buttonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 16,
  },
});
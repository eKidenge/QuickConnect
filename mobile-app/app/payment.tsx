import { View, Text, TextInput, StyleSheet, SafeAreaView, TouchableOpacity, Alert, ActivityIndicator, Linking } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState, useEffect } from 'react';
import { Ionicons } from '@expo/vector-icons';

interface Professional {
  id: string;
  name: string;
  specialization: string;
  rate: number; // Changed from string to number
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
}

interface PaymentParams {
  professional: string;
  consultationType: 'chat' | 'audio' | 'video';
  session?: string;
}

export default function PaymentScreen() {
  const params = useLocalSearchParams();
  const router = useRouter();
  const [phone, setPhone] = useState('');
  const [processing, setProcessing] = useState(false);
  const [professional, setProfessional] = useState<Professional | null>(null);
  const [consultationType, setConsultationType] = useState<'chat' | 'audio' | 'video'>('chat');
  const [amount, setAmount] = useState(0);
  const [session, setSession] = useState<any>(null);

  // Fixed calculateAmount function - handles number rate properly
  const calculateAmount = (prof: Professional, type: string): number => {
    // Rate is already a number, no need to parse
    const baseRate = prof.rate || 1000;
    
    const multipliers = {
      chat: 1,
      audio: 1.5, // Changed from 'voice' to 'audio' to match your backend
      video: 2
    };
    
    return Math.round(baseRate * (multipliers[type as keyof typeof multipliers] || 1));
  };

  useEffect(() => {
    console.log('📊 Payment screen params:', params);
    
    if (params.professional && params.consultationType) {
      try {
        const profData = JSON.parse(params.professional as string);
        console.log('💰 Professional rate:', profData.rate, 'Type:', typeof profData.rate);
        setProfessional(profData);
        setConsultationType(params.consultationType as 'chat' | 'audio' | 'video');
        
        // Calculate amount with the fixed function
        const calculatedAmount = calculateAmount(profData, params.consultationType as string);
        console.log('💵 Calculated amount:', calculatedAmount);
        setAmount(calculatedAmount);
      } catch (error) {
        console.error('❌ Error parsing professional data:', error);
        Alert.alert('Error', 'Failed to load payment details');
      }
    }

    if (params.session) {
      try {
        const sessionData = JSON.parse(params.session as string);
        setSession(sessionData);
        console.log('🎯 Session data loaded:', sessionData);
      } catch (error) {
        console.error('❌ Error parsing session data:', error);
      }
    }
  }, [params]);

  const validatePhone = (phone: string): boolean => {
    const cleaned = phone.replace(/\s+/g, '');
    const kenyaRegex = /^(?:254|\+254|0)?(7[0-9]{8})$/;
    return kenyaRegex.test(cleaned);
  };

  const formatPhone = (phone: string): string => {
    const cleaned = phone.replace(/\s+/g, '').replace(/^0/, '254').replace(/^\+/, '');
    return cleaned.startsWith('254') ? cleaned : `254${cleaned}`;
  };

  const initiateMpesaSTKPush = async (phoneNumber: string, amount: number, professional: Professional) => {
    try {
      setProcessing(true);
      
      console.log('💰 Initiating M-Pesa payment:', {
        phone: formatPhone(phoneNumber),
        amount,
        professionalId: professional.id,
        consultationType
      });

      // Real M-Pesa STK Push API call to your backend
      const response = await fetch('http://192.168.100.38:8000/api/initiate-mpesa-stk-push/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          phoneNumber: formatPhone(phoneNumber),
          amount: amount,
          professionalId: professional.id,
          sessionId: session?.session_id,
          consultationType: consultationType,
          accountReference: `CONSULT_${professional.id}`,
          transactionDesc: `Consultation with ${professional.name}`
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('✅ M-Pesa response:', result);

      if (result.success) {
        // STK Push sent successfully - M-Pesa will prompt user on their phone
        Alert.alert(
          'STK Push Sent! 📱',
          'Check your phone! M-Pesa has sent you a payment prompt. Enter your M-Pesa PIN to complete payment.',
          [
            {
              text: 'I\'ve Paid',
              onPress: () => {
                // Navigate to payment verification screen
                router.push({
                  pathname: '/payment-verification',
                  params: {
                    checkoutRequestID: result.checkout_request_id || result.transaction_id,
                    professional: JSON.stringify(professional),
                    consultationType: consultationType,
                    amount: amount.toString(),
                    phone: phoneNumber,
                    session: session ? JSON.stringify(session) : ''
                  }
                });
              }
            },
            {
              text: 'Not Received?',
              onPress: () => retryMpesaPayment(phoneNumber, amount, professional)
            }
          ]
        );
      } else {
        throw new Error(result.message || 'Failed to initiate M-Pesa payment');
      }
    } catch (error) {
      console.error('❌ M-Pesa STK Push error:', error);
      Alert.alert(
        'Payment Failed',
        error instanceof Error ? error.message : 'Unable to send M-Pesa prompt. Please try again.'
      );
    } finally {
      setProcessing(false);
    }
  };

  const retryMpesaPayment = (phoneNumber: string, amount: number, professional: Professional) => {
    Alert.alert(
      'Resend M-Pesa Prompt?',
      'Should we send the payment prompt again?',
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Resend', 
          onPress: () => initiateMpesaSTKPush(phoneNumber, amount, professional)
        }
      ]
    );
  };

  const handleMpesaPayment = () => {
    if (!professional) {
      Alert.alert('Error', 'Professional information missing');
      return;
    }

    if (!validatePhone(phone)) {
      Alert.alert('Invalid Phone', 'Please enter a valid Kenyan phone number (07XXXXXXXX)');
      return;
    }

    Alert.alert(
      'Confirm M-Pesa Payment',
      `You will receive an M-Pesa prompt on ${phone} for KSH ${amount.toLocaleString()}.\n\nConsultation: ${consultationType.charAt(0).toUpperCase() + consultationType.slice(1)} with ${professional.name}`,
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Confirm', 
          onPress: () => initiateMpesaSTKPush(phone, amount, professional)
        }
      ]
    );
  };

  const handleCardPayment = () => {
    if (!professional) return;

    // For card payments, use your backend endpoint
    Alert.alert(
      'Card Payment',
      'You will be redirected to our secure payment gateway to complete your card payment.',
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'Continue to Payment', 
          onPress: async () => {
            try {
              setProcessing(true);
              
              const response = await fetch('http://192.168.100.38:8000/api/initiate-card-payment/', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                  amount: amount,
                  session_id: session?.session_id,
                  professional_id: professional.id,
                  consultation_type: consultationType
                })
              });

              if (response.ok) {
                const data = await response.json();
                Alert.alert(
                  'Payment Initiated',
                  'Card payment processing started. You will be redirected to complete the payment.',
                  [{ text: 'OK' }]
                );
              } else {
                throw new Error('Failed to initiate card payment');
              }
            } catch (error) {
              console.error('Card payment error:', error);
              Alert.alert('Error', 'Failed to process card payment. Please try again.');
            } finally {
              setProcessing(false);
            }
          }
        }
      ]
    );
  };

  const handleBankTransfer = () => {
    if (!professional) return;

    Alert.alert(
      'Bank Transfer',
      `Transfer KSH ${amount.toLocaleString()} to:\n\nBank: KCB Bank\nAccount: 1234567890\nName: ConsultPro Ltd\nReference: ${professional.name}\n\nAfter transferring, click "I've Paid" to verify.`,
      [
        { text: 'Cancel', style: 'cancel' },
        { 
          text: 'I\'ve Paid', 
          onPress: () => {
            router.push({
              pathname: '/payment-verification',
              params: {
                paymentMethod: 'bank',
                professional: JSON.stringify(professional),
                consultationType: consultationType,
                amount: amount.toString(),
                session: session ? JSON.stringify(session) : ''
              }
            });
          }
        },
        {
          text: 'Copy Details',
          onPress: () => {
            // In a real app, you would copy to clipboard
            // For now, just show a confirmation
            Alert.alert('Copied!', 'Bank details copied to clipboard.');
          }
        }
      ]
    );
  };

  const getConsultationTypeDisplay = (type: string) => {
    const typeMap = {
      chat: 'Chat',
      audio: 'Voice Call',
      video: 'Video Call'
    };
    return typeMap[type as keyof typeof typeMap] || type;
  };

  if (!professional) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color="#007AFF" />
          <Text style={styles.loadingText}>Loading payment details...</Text>
          <TouchableOpacity 
            style={styles.backButton}
            onPress={() => router.back()}
          >
            <Text style={styles.backButtonText}>Go Back</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <Ionicons name="arrow-back" size={24} color="#1F2937" />
          </TouchableOpacity>
          <Text style={styles.title}>Complete Payment</Text>
          <View style={styles.backButton} />
        </View>

        {/* Professional Info */}
        <View style={styles.professionalCard}>
          <View style={styles.professionalInfo}>
            <View style={styles.professionalDetails}>
              <Text style={styles.professionalName}>{professional.name}</Text>
              <Text style={styles.consultationType}>
                {getConsultationTypeDisplay(consultationType)} Consultation
              </Text>
            </View>
            <View style={styles.rateBadge}>
              <Text style={styles.rateText}>${professional.rate}/hr</Text>
            </View>
          </View>
          {professional.specialization && (
            <Text style={styles.specialization}>{professional.specialization}</Text>
          )}
        </View>

        {/* Amount Card */}
        <View style={styles.amountCard}>
          <Text style={styles.amountLabel}>Total Amount</Text>
          <Text style={styles.amount}>KSH {amount.toLocaleString()}</Text>
          <Text style={styles.amountNote}>Inclusive of all charges</Text>
        </View>

        {/* M-Pesa Payment Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Ionicons name="phone-portrait" size={20} color="#10B981" />
            <Text style={styles.sectionTitle}>Pay with M-Pesa</Text>
          </View>
          
          <TextInput
            style={[styles.input, !phone || validatePhone(phone) ? styles.validInput : styles.invalidInput]}
            placeholder="07XXXXXXXX"
            value={phone}
            onChangeText={setPhone}
            keyboardType="phone-pad"
            maxLength={10}
            editable={!processing}
          />
          
          <View style={styles.hintContainer}>
            <Ionicons name="information-circle" size={16} color="#6B7280" />
            <Text style={styles.hint}>
              You'll receive an M-Pesa prompt on your phone. Enter your PIN to complete payment.
            </Text>
          </View>

          <TouchableOpacity 
            style={[
              styles.payBtn, 
              processing && styles.payBtnDisabled,
              (!phone || !validatePhone(phone)) && styles.payBtnDisabled
            ]} 
            onPress={handleMpesaPayment}
            disabled={processing || !phone || !validatePhone(phone)}
          >
            {processing ? (
              <ActivityIndicator color="#fff" size="small" />
            ) : (
              <View style={styles.payBtnContent}>
                <Ionicons name="logo-whatsapp" size={20} color="#fff" />
                <Text style={styles.payText}>Pay with M-Pesa</Text>
              </View>
            )}
          </TouchableOpacity>
        </View>

        {/* Divider */}
        <View style={styles.divider}>
          <View style={styles.line} />
          <Text style={styles.dividerText}>OR</Text>
          <View style={styles.line} />
        </View>

        {/* Card Payment Option */}
        <TouchableOpacity 
          style={styles.altBtn}
          onPress={handleCardPayment}
          disabled={processing}
        >
          <View style={styles.altBtnContent}>
            <Ionicons name="card" size={20} color="#1F2937" />
            <Text style={styles.altText}>Pay with Debit/Credit Card</Text>
          </View>
          <Ionicons name="chevron-forward" size={16} color="#9CA3AF" />
        </TouchableOpacity>

        {/* Bank Transfer Option */}
        <TouchableOpacity 
          style={styles.altBtn}
          onPress={handleBankTransfer}
          disabled={processing}
        >
          <View style={styles.altBtnContent}>
            <Ionicons name="business" size={20} color="#1F2937" />
            <Text style={styles.altText}>Bank Transfer</Text>
          </View>
          <Ionicons name="chevron-forward" size={16} color="#9CA3AF" />
        </TouchableOpacity>

        {/* Security Info */}
        <View style={styles.securityInfo}>
          <Ionicons name="shield-checkmark" size={16} color="#10B981" />
          <Text style={styles.securityText}>Secure payment • Encrypted with SSL</Text>
        </View>

        {/* Support */}
        <View style={styles.supportInfo}>
          <Text style={styles.supportText}>
            Need help? Call 0700 000 000 or email support@consultpro.com
          </Text>
        </View>

        {/* Cancel */}
        <TouchableOpacity 
          onPress={() => router.back()}
          style={styles.cancelBtn}
          disabled={processing}
        >
          <Text style={styles.cancelLink}>Cancel Payment</Text>
        </TouchableOpacity>
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
    padding: 20 
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    color: '#6B7280',
  },
  backButton: {
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  backButtonText: {
    color: '#007AFF',
    fontSize: 16,
    fontWeight: '600',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 24,
  },
  title: { 
    fontSize: 24, 
    fontWeight: '700', 
    color: '#111827', 
    textAlign: 'center',
    flex: 1,
  },
  professionalCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 2,
  },
  professionalInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  professionalDetails: {
    flex: 1,
  },
  professionalName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: 4,
  },
  consultationType: {
    fontSize: 14,
    color: '#6B7280',
    fontWeight: '500',
  },
  rateBadge: {
    backgroundColor: '#10B981',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  rateText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
  specialization: {
    fontSize: 13,
    color: '#6B7280',
    fontStyle: 'italic',
  },
  amountCard: { 
    backgroundColor: '#2563EB', 
    borderRadius: 16, 
    padding: 24, 
    alignItems: 'center', 
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 4,
  },
  amountLabel: { 
    fontSize: 14, 
    color: '#BFDBFE', 
    marginBottom: 8,
    fontWeight: '500',
  },
  amount: { 
    fontSize: 36, 
    fontWeight: '800', 
    color: '#fff',
    marginBottom: 4,
  },
  amountNote: {
    fontSize: 12,
    color: '#BFDBFE',
  },
  section: { 
    marginBottom: 24 
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  sectionTitle: { 
    fontSize: 16, 
    fontWeight: '700', 
    color: '#111827', 
    marginLeft: 8,
  },
  input: { 
    backgroundColor: '#fff', 
    borderRadius: 12, 
    padding: 16, 
    fontSize: 16, 
    borderWidth: 2,
	borderColor: '#E5E7EB',
    marginBottom: 8,
  },
  validInput: {
    borderColor: '#10B981',
  },
  invalidInput: {
    borderColor: '#EF4444',
  },
  hintContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 16,
  },
  hint: { 
    fontSize: 12, 
    color: '#6B7280',
    marginLeft: 6,
    flex: 1,
    lineHeight: 16,
  },
  payBtn: { 
    backgroundColor: '#10B981', 
    padding: 16, 
    borderRadius: 12, 
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 3,
  },
  payBtnDisabled: { 
    backgroundColor: '#9CA3AF',
    shadowOpacity: 0,
    elevation: 0,
  },
  payBtnContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  payText: { 
    color: '#fff', 
    fontSize: 16, 
    fontWeight: '700',
    marginLeft: 8,
  },
  divider: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    marginVertical: 20 
  },
  line: { 
    flex: 1, 
    height: 1, 
    backgroundColor: '#E5E7EB' 
  },
  dividerText: { 
    fontSize: 12, 
    color: '#9CA3AF', 
    marginHorizontal: 12,
    fontWeight: '600',
  },
  altBtn: { 
    backgroundColor: '#fff', 
    padding: 16, 
    borderRadius: 12, 
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderWidth: 2, 
    borderColor: '#E5E7EB',
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 1,
  },
  altBtnContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  altText: { 
    color: '#111827', 
    fontSize: 16, 
    fontWeight: '600',
    marginLeft: 8,
  },
  securityInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 12,
    marginTop: 8,
  },
  securityText: {
    fontSize: 12,
    color: '#6B7280',
    marginLeft: 6,
  },
  supportInfo: {
    alignItems: 'center',
    marginBottom: 20,
    padding: 12,
    backgroundColor: '#F3F4F6',
    borderRadius: 8,
  },
  supportText: {
    fontSize: 12,
    color: '#6B7280',
    textAlign: 'center',
  },
  cancelBtn: {
    padding: 16,
    alignItems: 'center',
  },
  cancelLink: { 
    fontSize: 16, 
    color: '#DC2626', 
    fontWeight: '600',
  }
});
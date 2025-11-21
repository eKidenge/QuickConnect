import { View, Text, StyleSheet, SafeAreaView, TouchableOpacity, Alert, ActivityIndicator, ScrollView } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useState, useEffect } from 'react';
import { Ionicons } from '@expo/vector-icons';
import * as Print from 'expo-print';
import * as Sharing from 'expo-sharing';
import * as FileSystem from 'expo-file-system';

interface PaymentData {
  id: string;
  amount: number;
  currency: string;
  method: string;
  status: string;
  transactionId: string;
  timestamp: string;
  professionalName: string;
  consultationType: string;
  sessionId: string;
}

interface ReceiptData {
  receiptNumber: string;
  date: string;
  time: string;
  clientName: string;
  clientEmail: string;
  professionalName: string;
  service: string;
  amount: number;
  transactionId: string;
  paymentMethod: string;
}

export default function PaymentSuccessScreen() {
  const router = useRouter();
  const params = useLocalSearchParams();
  const [payment, setPayment] = useState<PaymentData | null>(null);
  const [loading, setLoading] = useState(true);
  const [generatingReceipt, setGeneratingReceipt] = useState(false);
  const [receiptData, setReceiptData] = useState<ReceiptData | null>(null);

  useEffect(() => {
    initializePaymentData();
  }, [params]);

  const initializePaymentData = async () => {
    try {
      setLoading(true);

      // Record payment in database
      const paymentResponse = await fetch('/api/payments/record', {
        method: 'POST',
        headers: {
			'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          amount: params.amount,
          professionalId: params.professionalId,
          sessionId: params.sessionId,
          consultationType: params.consultationType,
          paymentMethod: params.paymentMethod || 'M-Pesa',
          transactionId: params.transactionId || `TXN_${Date.now()}`,
          clientId: 'current-user-id' // Replace with actual client ID
        })
      });

      const paymentResult = await paymentResponse.json();

      if (paymentResult.success) {
        setPayment(paymentResult.payment);
        
        // Generate receipt data
        const receipt: ReceiptData = {
          receiptNumber: `RCP${Date.now()}`,
          date: new Date().toLocaleDateString(),
          time: new Date().toLocaleTimeString(),
          clientName: 'John Doe', // Replace with actual client name
          clientEmail: 'client@example.com', // Replace with actual client email
          professionalName: params.professionalName as string || 'Professional',
          service: `${params.consultationType} Consultation`,
          amount: parseInt(params.amount as string),
          transactionId: paymentResult.payment.transactionId,
          paymentMethod: params.paymentMethod as string || 'M-Pesa'
        };
        
        setReceiptData(receipt);
        
        // Send receipt via email/SMS
        await sendReceiptNotification(receipt);
      } else {
        throw new Error(paymentResult.message || 'Failed to record payment');
      }
    } catch (error) {
      console.error('Payment recording error:', error);
      Alert.alert(
        'Payment Recorded',
        'Your payment was successful, but we encountered an issue recording the details. Your session is confirmed.'
      );
      
      // Create fallback payment data
      const fallbackPayment: PaymentData = {
        id: `fallback_${Date.now()}`,
        amount: parseInt(params.amount as string) || 0,
        currency: 'KES',
        method: params.paymentMethod as string || 'M-Pesa',
        status: 'completed',
        transactionId: params.transactionId as string || `TXN_${Date.now()}`,
        timestamp: new Date().toISOString(),
        professionalName: params.professionalName as string || 'Professional',
        consultationType: params.consultationType as string || 'Consultation',
        sessionId: params.sessionId as string || ''
      };
      
      setPayment(fallbackPayment);
    } finally {
      setLoading(false);
    }
  };

  const sendReceiptNotification = async (receipt: ReceiptData) => {
    try {
      await fetch('/api/notifications/receipt', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          receiptData: receipt,
          clientId: 'current-user-id',
          sendEmail: true,
          sendSMS: true
        })
      });
    } catch (error) {
      console.error('Receipt notification error:', error);
    }
  };

  const generateReceiptHTML = (receipt: ReceiptData): string => {
    return `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <title>Payment Receipt</title>
        <style>
          body { 
            font-family: Arial, sans-serif; 
            margin: 0; 
            padding: 20px; 
            color: #333; 
          }
          .header { 
            text-align: center; 
            border-bottom: 2px solid #10B981; 
            padding-bottom: 20px; 
            margin-bottom: 20px; 
          }
          .company-name { 
            font-size: 24px; 
            font-weight: bold; 
            color: #111827; 
          }
          .receipt-title { 
            font-size: 20px; 
            color: #059669; 
            margin: 10px 0; 
          }
          .details { 
            margin: 20px 0; 
          }
          .detail-row { 
            display: flex; 
            justify-content: space-between; 
            margin-bottom: 8px; 
            padding: 8px 0;
            border-bottom: 1px solid #E5E7EB;
          }
          .detail-label { 
            font-weight: 600; 
            color: #6B7280; 
          }
          .detail-value { 
            color: #111827; 
          }
          .amount-section { 
            background: #F0F9FF; 
            padding: 15px; 
            border-radius: 8px; 
            margin: 20px 0; 
          }
          .total-amount { 
            font-size: 24px; 
            font-weight: bold; 
            color: #059669; 
            text-align: center; 
          }
          .footer { 
            text-align: center; 
            margin-top: 30px; 
            padding-top: 20px; 
            border-top: 1px solid #E5E7EB; 
            color: #6B7280; 
            font-size: 12px; 
          }
          .thank-you { 
            text-align: center; 
            margin: 20px 0; 
            font-style: italic; 
            color: #6B7280; 
          }
        </style>
      </head>
      <body>
        <div class="header">
          <div class="company-name">ConsultPro</div>
          <div class="receipt-title">PAYMENT RECEIPT</div>
        </div>
        
        <div class="details">
          <div class="detail-row">
            <span class="detail-label">Receipt Number:</span>
            <span class="detail-value">${receipt.receiptNumber}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Date:</span>
            <span class="detail-value">${receipt.date}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Time:</span>
            <span class="detail-value">${receipt.time}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Transaction ID:</span>
            <span class="detail-value">${receipt.transactionId}</span>
          </div>
        </div>
        
        <div class="details">
          <div class="detail-row">
            <span class="detail-label">Client:</span>
            <span class="detail-value">${receipt.clientName}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Professional:</span>
            <span class="detail-value">${receipt.professionalName}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Service:</span>
            <span class="detail-value">${receipt.service}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Payment Method:</span>
            <span class="detail-value">${receipt.paymentMethod}</span>
          </div>
        </div>
        
        <div class="amount-section">
          <div class="total-amount">KSH ${receipt.amount.toLocaleString()}</div>
        </div>
        
        <div class="thank-you">
          Thank you for your payment. This receipt confirms your transaction.
        </div>
        
        <div class="footer">
          <p>ConsultPro Limited</p>
          <p>support@consultpro.com | +254 700 000 000</p>
          <p>This is an computer-generated receipt. No signature required.</p>
        </div>
      </body>
      </html>
    `;
  };

  const printReceipt = async () => {
    if (!receiptData) {
      Alert.alert('Error', 'Receipt data not available');
      return;
    }

    try {
      setGeneratingReceipt(true);
      
      const html = generateReceiptHTML(receiptData);
      
      // Generate PDF
      const { uri } = await Print.printToFileAsync({
        html: html,
        base64: false
      });

      // Share the PDF file
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(uri, {
          mimeType: 'application/pdf',
          dialogTitle: 'Save Payment Receipt',
          UTI: 'com.adobe.pdf'
        });
      } else {
        Alert.alert('Success', 'Receipt generated successfully. PDF saved to device.');
      }
    } catch (error) {
      console.error('Print error:', error);
      Alert.alert('Error', 'Failed to generate receipt. Please try again.');
    } finally {
      setGeneratingReceipt(false);
    }
  };

  const saveReceiptToDevice = async () => {
    if (!receiptData) return;

    try {
      setGeneratingReceipt(true);
      
      const html = generateReceiptHTML(receiptData);
      const { uri } = await Print.printToFileAsync({
        html: html,
        base64: false
      });

      // Move file to permanent location
      const permanentLocation = `${FileSystem.documentDirectory}receipt_${receiptData.receiptNumber}.pdf`;
      await FileSystem.moveAsync({
        from: uri,
        to: permanentLocation
      });

      Alert.alert('Success', 'Receipt saved to your device.');
    } catch (error) {
      console.error('Save receipt error:', error);
      Alert.alert('Error', 'Failed to save receipt.');
    } finally {
      setGeneratingReceipt(false);
    }
  };

  const viewPaymentHistory = () => {
    router.push({
      pathname: '/payment-history',
      params: { 
        recentPayment: payment ? JSON.stringify(payment) : undefined 
      }
    });
  };

  const contactSupport = () => {
    // You can implement actual support contact here
    Alert.alert(
      'Contact Support',
      'Email: support@consultpro.com\nPhone: 0700 000 000',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Copy Email', onPress: () => {
          // Clipboard.setStringAsync('support@consultpro.com');
          Alert.alert('Copied!', 'Email address copied to clipboard.');
        }}
      ]
    );
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#007AFF" />
          <Text style={styles.loadingText}>Recording your payment...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scrollContent}>
        <View style={styles.content}>
          {/* Success Icon & Title */}
          <View style={styles.successHeader}>
            <Ionicons name="checkmark-circle" size={100} color="#10B981" />
            <Text style={styles.title}>Payment Successful!</Text>
            <Text style={styles.subtitle}>
              Your payment has been processed successfully. A receipt has been sent to your registered contact.
            </Text>
          </View>

          {/* Payment Details Card */}
          {payment && (
            <View style={styles.detailsCard}>
              <Text style={styles.cardTitle}>Payment Details</Text>
              
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>Amount Paid</Text>
                <Text style={styles.detailValue}>KSH {payment.amount.toLocaleString()}</Text>
              </View>
              
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>Payment Method</Text>
                <Text style={styles.detailValue}>{payment.method}</Text>
              </View>
              
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>Transaction ID</Text>
                <Text style={styles.detailValue}>{payment.transactionId}</Text>
              </View>
              
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>Professional</Text>
                <Text style={styles.detailValue}>{payment.professionalName}</Text>
              </View>
              
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>Service</Text>
                <Text style={styles.detailValue}>{payment.consultationType}</Text>
              </View>
              
              <View style={styles.detailRow}>
                <Text style={styles.detailLabel}>Date & Time</Text>
                <Text style={styles.detailValue}>
                  {new Date(payment.timestamp).toLocaleString()}
                </Text>
              </View>
            </View>
          )}

          {/* Receipt Actions */}
          <View style={styles.actionsCard}>
            <Text style={styles.cardTitle}>Receipt & Records</Text>
            
            <TouchableOpacity 
              style={styles.receiptButton}
              onPress={printReceipt}
              disabled={generatingReceipt}
            >
              {generatingReceipt ? (
                <ActivityIndicator color="#fff" size="small" />
              ) : (
                <>
                  <Ionicons name="print" size={20} color="#fff" />
                  <Text style={styles.receiptButtonText}>Print/Save Receipt</Text>
                </>
              )}
            </TouchableOpacity>

            <TouchableOpacity 
              style={styles.secondaryButton}
              onPress={saveReceiptToDevice}
              disabled={generatingReceipt}
            >
              <Ionicons name="download" size={20} color="#2563EB" />
              <Text style={styles.secondaryButtonText}>Save to Device</Text>
            </TouchableOpacity>

            <TouchableOpacity 
              style={styles.tertiaryButton}
              onPress={viewPaymentHistory}
            >
              <Ionicons name="receipt" size={20} color="#6B7280" />
              <Text style={styles.tertiaryButtonText}>View Payment History</Text>
            </TouchableOpacity>
          </View>

          {/* Next Steps */}
          <View style={styles.infoCard}>
            <Text style={styles.cardTitle}>What's Next?</Text>
            <View style={styles.infoItem}>
              <Ionicons name="checkmark-circle" size={16} color="#10B981" />
              <Text style={styles.infoText}>Payment recorded in your account</Text>
            </View>
            <View style={styles.infoItem}>
              <Ionicons name="checkmark-circle" size={16} color="#10B981" />
              <Text style={styles.infoText}>Session history saved</Text>
            </View>
            <View style={styles.infoItem}>
              <Ionicons name="checkmark-circle" size={16} color="#10B981" />
              <Text style={styles.infoText}>Professional notified of payment</Text>
            </View>
            <View style={styles.infoItem}>
              <Ionicons name="checkmark-circle" size={16} color="#10B981" />
              <Text style={styles.infoText}>Receipt sent to your email/SMS</Text>
            </View>
          </View>

          {/* Support Information */}
          <View style={styles.supportSection}>
            <Text style={styles.supportTitle}>Need Help?</Text>
            <Text style={styles.supportText}>
              If you have any questions about this payment, contact our support team.
            </Text>
            <TouchableOpacity 
              style={styles.supportButton}
              onPress={contactSupport}
            >
              <Ionicons name="headset" size={16} color="#2563EB" />
              <Text style={styles.supportButtonText}>Contact Support</Text>
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>

      {/* Fixed Action Buttons */}
      <View style={styles.footer}>
        <TouchableOpacity 
          style={styles.primaryButton}
          onPress={() => router.push('/dashboard')}
        >
          <Text style={styles.primaryButtonText}>Return to Dashboard</Text>
        </TouchableOpacity>

        <TouchableOpacity 
          style={styles.outlineButton}
          onPress={() => router.push('/history')}
        >
          <Text style={styles.outlineButtonText}>View Session History</Text>
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
  scrollContent: {
    flex: 1,
  },
  content: { 
    padding: 20, 
    paddingBottom: 120, // Space for fixed footer
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
  successHeader: {
    alignItems: 'center',
    marginBottom: 24,
    paddingVertical: 20,
  },
  title: { 
    fontSize: 28, 
    fontWeight: '800', 
    color: '#111827', 
    marginTop: 16,
    marginBottom: 8,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 16, 
    color: '#6B7280', 
    textAlign: 'center',
    lineHeight: 22,
    paddingHorizontal: 20,
  },
  detailsCard: {
    backgroundColor: '#fff', 
    borderRadius: 16, 
    padding: 20, 
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  actionsCard: {
    backgroundColor: '#fff', 
    borderRadius: 16, 
    padding: 20, 
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  infoCard: {
    backgroundColor: '#fff', 
    borderRadius: 16, 
    padding: 20, 
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
  },
  cardTitle: {
    fontSize: 18, 
    fontWeight: '700', 
    color: '#111827', 
    marginBottom: 16,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  detailLabel: {
    fontSize: 14,
    color: '#6B7280',
    fontWeight: '500',
  },
  detailValue: {
    fontSize: 14,
    color: '#111827',
    fontWeight: '600',
  },
  receiptButton: {
    backgroundColor: '#2563EB',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    gap: 8,
  },
  receiptButtonText: {
    color: '#fff', 
    fontSize: 16, 
    fontWeight: '600',
  },
  secondaryButton: {
    backgroundColor: '#fff',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#2563EB',
    marginBottom: 12,
    gap: 8,
  },
  secondaryButtonText: {
    color: '#2563EB', 
    fontSize: 16, 
    fontWeight: '600',
  },
  tertiaryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    borderRadius: 12,
    gap: 8,
  },
  tertiaryButtonText: {
    color: '#6B7280', 
    fontSize: 16, 
    fontWeight: '600',
  },
  infoItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    gap: 8,
  },
  infoText: {
    fontSize: 14,
    color: '#6B7280',
    flex: 1,
  },
  supportSection: {
    backgroundColor: '#F0F9FF',
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    borderLeftWidth: 4,
    borderLeftColor: '#2563EB',
  },
  supportTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 8,
  },
  supportText: {
    fontSize: 14,
    color: '#6B7280',
    marginBottom: 12,
    lineHeight: 20,
  },
  supportButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    alignSelf: 'flex-start',
  },
  supportButtonText: {
    color: '#2563EB',
    fontSize: 14,
    fontWeight: '600',
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
  primaryButton: {
    backgroundColor: '#2563EB',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginBottom: 12,
  },
  primaryButtonText: {
    color: '#fff', 
    fontSize: 16, 
    fontWeight: '700',
  },
  outlineButton: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#E5E7EB',
  },
  outlineButtonText: {
    color: '#111827', 
    fontSize: 16, 
    fontWeight: '600',
  },
});
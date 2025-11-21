import React, { useState, useEffect } from 'react';
import { 
  View, 
  Text, 
  TextInput, 
  ScrollView, 
  StyleSheet, 
  SafeAreaView, 
  TouchableOpacity, 
  Alert,
  ActivityIndicator,
  Modal,
  FlatList,
  Platform
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';
import * as DocumentPicker from 'expo-document-picker';
import * as FileSystem from 'expo-file-system';

interface Category {
  id: number;
  name: string;
  description: string;
}

interface ProfessionalFormData {
  name: string;
  email: string;
  phone: string;
  category_id: string;
  category_name: string;
  specialization: string;
  experience: string;
  license_number: string;
  bio: string;
  rate: string;
  password: string;
  confirm_password: string;
  username: string;
}

interface UploadedDocument {
  name: string;
  uri: string;
  type: string;
  base64?: string;
}

export default function ProfessionalSignupScreen() {
  const router = useRouter();
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [uploadedDocuments, setUploadedDocuments] = useState<UploadedDocument[]>([]);
  const [formData, setFormData] = useState<ProfessionalFormData>({
    name: '',
    email: '',
    phone: '',
    category_id: '',
    category_name: '',
    specialization: '',
    experience: '',
    license_number: '',
    bio: '',
    rate: '50',
    password: '',
    confirm_password: '',
    username: ''
  });

  // Fetch categories from database
  const fetchCategories = async () => {
    try {
      const response = await fetch('http://192.168.100.38:8000/api/categories/');
      
      if (response.ok) {
        const data = await response.json();
        setCategories(data.categories || data);
      } else {
        throw new Error('Failed to fetch categories');
      }
    } catch (error) {
      console.error('Error fetching categories:', error);
      Alert.alert('Error', 'Failed to load categories. Please try again.');
    }
  };

  useEffect(() => {
    fetchCategories();
  }, []);

  // Generate username from email when email changes
  useEffect(() => {
    if (formData.email && !formData.username) {
      const username = formData.email.split('@')[0];
      setFormData(prev => ({ ...prev, username }));
    }
  }, [formData.email]);

  const handleDocumentUpload = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg'],
        copyToCacheDirectory: true,
      });

      if (result.canceled === false && result.assets && result.assets.length > 0) {
        const file = result.assets[0];
        
        let base64Data = '';
        
        if (Platform.OS === 'web') {
          const response = await fetch(file.uri);
          const blob = await response.blob();
          base64Data = await new Promise((resolve) => {
            const reader = new FileReader();
            reader.onloadend = () => {
              const base64 = reader.result as string;
              const base64String = base64.includes(',') ? base64.split(',')[1] : base64;
              resolve(base64String);
            };
            reader.readAsDataURL(blob);
          });
        } else {
          base64Data = await FileSystem.readAsStringAsync(file.uri, {
            encoding: FileSystem.EncodingType.Base64,
          });
        }

        const newDocument: UploadedDocument = {
          name: file.name || 'document',
          uri: file.uri,
          type: file.mimeType || 'application/pdf',
          base64: base64Data
        };
        
        setUploadedDocuments(prev => [...prev, newDocument]);
        Alert.alert('Success', 'Document uploaded successfully');
      }
    } catch (error) {
      console.error('Document picker error:', error);
      Alert.alert('Error', 'Failed to upload document. Please try again.');
    }
  };

  const removeDocument = (index: number) => {
    setUploadedDocuments(prev => prev.filter((_, i) => i !== index));
  };

  const validateForm = (): boolean => {
    if (!formData.name.trim()) {
      Alert.alert('Error', 'Please enter your full name');
      return false;
    }
    if (!formData.email.trim() || !/\S+@\S+\.\S+/.test(formData.email)) {
      Alert.alert('Error', 'Please enter a valid email address');
      return false;
    }
    if (!formData.username.trim()) {
      Alert.alert('Error', 'Username is required');
      return false;
    }
    if (!formData.phone.trim()) {
      Alert.alert('Error', 'Please enter your phone number');
      return false;
    }
    if (!formData.password.trim()) {
      Alert.alert('Error', 'Please enter a password');
      return false;
    }
    if (formData.password.length < 6) {
      Alert.alert('Error', 'Password must be at least 6 characters long');
      return false;
    }
    if (formData.password !== formData.confirm_password) {
      Alert.alert('Error', 'Passwords do not match');
      return false;
    }
    if (!formData.category_id) {
      Alert.alert('Error', 'Please select a category');
      return false;
    }
    if (!formData.specialization.trim()) {
      Alert.alert('Error', 'Please enter your specialization');
      return false;
    }
    if (!formData.experience.trim() || isNaN(parseInt(formData.experience)) || parseInt(formData.experience) < 0) {
      Alert.alert('Error', 'Please enter valid years of experience');
      return false;
    }
    if (!formData.license_number.trim()) {
      Alert.alert('Error', 'Please enter your license number');
      return false;
    }
    if (uploadedDocuments.length === 0) {
      Alert.alert('Error', 'Please upload at least one document (license/certificate)');
      return false;
    }
    if (!formData.rate || isNaN(parseFloat(formData.rate)) || parseFloat(formData.rate) <= 0) {
      Alert.alert('Error', 'Please enter a valid rate per minute');
      return false;
    }
    return true;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;

    setLoading(true);
    try {
      // Step 1: Register the user first
      const username = formData.username.trim() || formData.email.split('@')[0];
      
      const registerResponse = await fetch('http://192.168.100.38:8000/api/register/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: username,
          first_name: formData.name.split(' ')[0],
          last_name: formData.name.split(' ').slice(1).join(' ') || '',
          email: formData.email.trim(),
          phone: formData.phone.trim(),
          password: formData.password,
          user_type: 'professional'
        }),
      });

      if (!registerResponse.ok) {
        const errorText = await registerResponse.text();
        let errorMessage = `Registration failed: ${registerResponse.status}`;
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.error || errorData.detail || errorData.message || errorText;
        } catch (e) {
          errorMessage = errorText || `HTTP ${registerResponse.status}`;
        }
        throw new Error(errorMessage);
      }

      const registerData = await registerResponse.json();

      // Step 2: Login to get authentication token
      let loginResponse = await fetch('http://192.168.100.38:8000/api/login/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: username,
          password: formData.password,
        }),
      });

      // If login with username fails, try with email as fallback
      if (!loginResponse.ok) {
        loginResponse = await fetch('http://192.168.100.38:8000/api/login/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            email: formData.email.trim(),
            password: formData.password,
          }),
        });
      }

      if (!loginResponse.ok) {
        const loginErrorText = await loginResponse.text();
        throw new Error('Login failed after registration. Please try logging in manually with your credentials.');
      }

      const loginData = await loginResponse.json();

      const token = loginData.token || loginData.key || loginData.access_token;
      
      if (!token) {
        throw new Error('No authentication token received. Please try logging in manually.');
      }

      // Step 3: Create professional profile
      const professionalData = {
        specialization: formData.specialization.trim(),
        category_id: parseInt(formData.category_id),
        rate: parseFloat(formData.rate),
        bio: formData.bio.trim(),
        experience_years: parseInt(formData.experience),
        license_number: formData.license_number.trim(),
        is_approved: false,
        is_online: true,
        is_available: true
      };

      const profileResponse = await fetch('http://192.168.100.38:8000/api/professionals/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Token ${token}`,
        },
        body: JSON.stringify(professionalData),
      });

      if (!profileResponse.ok) {
        const errorText = await profileResponse.text();
        let errorMessage = `Profile creation failed: ${profileResponse.status}`;
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.error || errorData.detail || errorData.message || errorText;
        } catch (e) {
          errorMessage = errorText || `HTTP ${profileResponse.status}`;
        }
        throw new Error(errorMessage);
      }

      const profileData = await profileResponse.json();

      // Update auth context
      if (login) {
        const authData = {
          ...loginData,
          user: {
            id: registerData.user_id,
            email: formData.email,
            username: username,
            first_name: formData.name.split(' ')[0],
            last_name: formData.name.split(' ').slice(1).join(' ') || '',
            user_type: 'professional'
          }
        };
        await login(authData);
      }

      Alert.alert(
        'Registration Successful!',
        'Your professional account has been created and submitted for admin approval. You will be notified once approved.',
        [
          {
            text: 'Go to Dashboard',
            onPress: () => router.replace('/professional/professional-dashboard')
          }
        ]
      );

    } catch (error) {
      console.error('Registration error:', error);
      Alert.alert(
        'Registration Failed',
        error instanceof Error ? error.message : 'Network error. Please check your connection and try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  const selectCategory = (category: Category) => {
    setFormData({
      ...formData,
      category_id: category.id.toString(),
      category_name: category.name
    });
    setShowCategoryModal(false);
  };

  // Fallback categories if API fails
  const getCategories = () => {
    if (categories.length > 0) return categories;
    
    return [
      { id: 1, name: 'Legal', description: 'Legal advice and consultation' },
      { id: 2, name: 'Medical', description: 'Medical consultation and advice' },
      { id: 3, name: 'Mental Health', description: 'Counseling and psychological support' },
      { id: 4, name: 'Career', description: 'Career guidance and coaching' },
    ];
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <Text style={styles.title}>Create Professional Account</Text>
          <Text style={styles.subtitle}>
            Complete your professional profile to start accepting clients
          </Text>
        </View>

        <View style={styles.form}>
          {/* Account Information */}
          <Text style={styles.sectionTitle}>Account Information</Text>
          
          <Text style={styles.label}>Full Name *</Text>
          <TextInput
            style={styles.input}
            placeholder="Enter your full name"
            value={formData.name}
            onChangeText={(text) => setFormData({...formData, name: text})}
            editable={!loading}
          />

          <Text style={styles.label}>Email *</Text>
          <TextInput
            style={styles.input}
            placeholder="your.email@example.com"
            value={formData.email}
            onChangeText={(text) => setFormData({...formData, email: text})}
            keyboardType="email-address"
            autoCapitalize="none"
            editable={!loading}
          />

          <Text style={styles.label}>Username *</Text>
          <TextInput
            style={styles.input}
            placeholder="Choose a username"
            value={formData.username}
            onChangeText={(text) => setFormData({...formData, username: text})}
            autoCapitalize="none"
            editable={!loading}
          />

          <Text style={styles.label}>Phone Number *</Text>
          <TextInput
            style={styles.input}
            placeholder="0712345678"
            value={formData.phone}
            onChangeText={(text) => setFormData({...formData, phone: text})}
            keyboardType="phone-pad"
            editable={!loading}
          />

          <Text style={styles.label}>Password *</Text>
          <TextInput
            style={styles.input}
            placeholder="Enter password (min 6 characters)"
            value={formData.password}
            onChangeText={(text) => setFormData({...formData, password: text})}
            secureTextEntry
            editable={!loading}
          />

          <Text style={styles.label}>Confirm Password *</Text>
          <TextInput
            style={styles.input}
            placeholder="Confirm your password"
            value={formData.confirm_password}
            onChangeText={(text) => setFormData({...formData, confirm_password: text})}
            secureTextEntry
            editable={!loading}
          />

          {/* Professional Information */}
          <Text style={styles.sectionTitle}>Professional Information</Text>

          <Text style={styles.label}>Professional Bio</Text>
          <TextInput
            style={[styles.input, styles.textArea]}
            placeholder="Brief description of your professional background and expertise..."
            value={formData.bio}
            onChangeText={(text) => setFormData({...formData, bio: text})}
            multiline
            numberOfLines={4}
            editable={!loading}
          />

          <Text style={styles.label}>Category *</Text>
          <TouchableOpacity
            style={styles.categorySelector}
            onPress={() => setShowCategoryModal(true)}
            disabled={loading}
          >
            <Text style={formData.category_name ? styles.categorySelectedText : styles.categoryPlaceholderText}>
              {formData.category_name || 'Select your professional category'}
            </Text>
            <Text style={styles.dropdownIcon}>▼</Text>
          </TouchableOpacity>

          <Text style={styles.label}>Specialization *</Text>
          <TextInput
            style={styles.input}
            placeholder="e.g., Family Law, Pediatrics, Career Counseling"
            value={formData.specialization}
            onChangeText={(text) => setFormData({...formData, specialization: text})}
            editable={!loading}
          />

          <Text style={styles.label}>Years of Experience *</Text>
          <TextInput
            style={styles.input}
            placeholder="e.g., 5"
            value={formData.experience}
            onChangeText={(text) => setFormData({...formData, experience: text})}
            keyboardType="numeric"
            editable={!loading}
          />

          <Text style={styles.label}>License Number *</Text>
          <TextInput
            style={styles.input}
            placeholder="Your professional license/certification number"
            value={formData.license_number}
            onChangeText={(text) => setFormData({...formData, license_number: text})}
            editable={!loading}
          />

          <Text style={styles.label}>Rate per Minute (KSH) *</Text>
          <TextInput
            style={styles.input}
            placeholder="50"
            value={formData.rate}
            onChangeText={(text) => setFormData({...formData, rate: text})}
            keyboardType="numeric"
            editable={!loading}
          />

          {/* Document Upload */}
          <Text style={styles.sectionTitle}>Document Verification</Text>
          <Text style={styles.label}>Upload License/Certificate *</Text>
          <Text style={styles.helperText}>
            Upload your professional license, certification, or any supporting documents (PDF, JPG, PNG)
          </Text>

          <TouchableOpacity 
            style={styles.uploadBtn} 
            onPress={handleDocumentUpload}
            disabled={loading}
          >
            <Text style={styles.uploadText}>📎 Upload Document</Text>
          </TouchableOpacity>

          {/* Uploaded Documents List */}
          {uploadedDocuments.map((doc, index) => (
            <View key={index} style={styles.documentItem}>
              <Text style={styles.documentName} numberOfLines={1}>
                {doc.name}
              </Text>
              <TouchableOpacity 
                onPress={() => removeDocument(index)}
                disabled={loading}
              >
                <Text style={styles.removeDocument}>✕</Text>
              </TouchableOpacity>
            </View>
          ))}

          {uploadedDocuments.length > 0 && (
            <Text style={styles.uploadCount}>
              {uploadedDocuments.length} document{uploadedDocuments.length !== 1 ? 's' : ''} uploaded
            </Text>
          )}

          {/* Submit Button */}
          <TouchableOpacity 
            style={[styles.submitBtn, loading && styles.submitBtnDisabled]} 
            onPress={handleSubmit}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.submitText}>Create Professional Account</Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity 
            style={styles.loginLink}
            onPress={() => router.push('/auth/login')}
          >
            <Text style={styles.loginLinkText}>
              Already have an account? Log in
            </Text>
          </TouchableOpacity>
        </View>
      </ScrollView>

      {/* Category Selection Modal */}
      <Modal
        visible={showCategoryModal}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setShowCategoryModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Select Category</Text>
              <TouchableOpacity 
                onPress={() => setShowCategoryModal(false)}
                style={styles.closeButton}
              >
                <Text style={styles.closeButtonText}>✕</Text>
              </TouchableOpacity>
            </View>
            
            <FlatList
              data={getCategories()}
              keyExtractor={(item) => item.id.toString()}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={[
                    styles.categoryItem,
                    formData.category_id === item.id.toString() && styles.categoryItemSelected
                  ]}
                  onPress={() => selectCategory(item)}
                >
                  <Text style={styles.categoryName}>{item.name}</Text>
                  <Text style={styles.categoryDescription}>{item.description}</Text>
                </TouchableOpacity>
              )}
              ListEmptyComponent={
                <View style={styles.emptyCategories}>
                  <Text style={styles.emptyText}>No categories available</Text>
                </View>
              }
            />
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { 
    flex: 1, 
    backgroundColor: '#F9FAFB' 
  },
  scroll: { 
    flex: 1 
  },
  header: { 
    padding: 20, 
    backgroundColor: '#fff', 
    borderBottomWidth: 1, 
    borderBottomColor: '#E5E7EB' 
  },
  backBtn: { 
    fontSize: 16, 
    color: '#2563EB', 
    fontWeight: '600', 
    marginBottom: 12 
  },
  title: { 
    fontSize: 24, 
    fontWeight: '800', 
    color: '#111827', 
    marginBottom: 8 
  },
  subtitle: { 
    fontSize: 14, 
    color: '#6B7280',
    lineHeight: 20 
  },
  form: { 
    padding: 20 
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#111827',
    marginTop: 24,
    marginBottom: 16,
    paddingBottom: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB'
  },
  label: { 
    fontSize: 14, 
    fontWeight: '600', 
    color: '#111827', 
    marginBottom: 8, 
    marginTop: 16 
  },
  helperText: {
    fontSize: 12,
    color: '#6B7280',
    marginBottom: 12,
    fontStyle: 'italic'
  },
  input: { 
    backgroundColor: '#fff', 
    borderRadius: 8, 
    padding: 12, 
    fontSize: 16, 
    borderWidth: 1, 
    borderColor: '#E5E7EB' 
  },
  textArea: {
    height: 100,
    textAlignVertical: 'top'
  },
  categorySelector: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 12,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  categorySelectedText: {
    fontSize: 16,
    color: '#111827'
  },
  categoryPlaceholderText: {
    fontSize: 16,
    color: '#9CA3AF'
  },
  dropdownIcon: {
    fontSize: 12,
    color: '#6B7280'
  },
  uploadBtn: { 
    backgroundColor: '#fff', 
    padding: 16, 
    borderRadius: 8, 
    alignItems: 'center', 
    borderWidth: 1, 
    borderColor: '#E5E7EB', 
    marginTop: 8 
  },
  uploadText: { 
    fontSize: 14, 
    color: '#2563EB', 
    fontWeight: '600' 
  },
  documentItem: {
    backgroundColor: '#fff',
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    marginTop: 8,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  documentName: {
    flex: 1,
    fontSize: 14,
    color: '#111827',
    marginRight: 8
  },
  removeDocument: {
    color: '#EF4444',
    fontSize: 16,
    fontWeight: 'bold'
  },
  uploadCount: {
    fontSize: 12,
    color: '#6B7280',
    textAlign: 'center',
    marginTop: 8,
    fontStyle: 'italic'
  },
  submitBtn: { 
    backgroundColor: '#2563EB', 
    padding: 16, 
    borderRadius: 12, 
    alignItems: 'center', 
    marginTop: 32,
    marginBottom: 20
  },
  submitBtnDisabled: {
    backgroundColor: '#9CA3AF'
  },
  submitText: { 
    color: '#fff', 
    fontSize: 16, 
    fontWeight: '700' 
  },
  loginLink: {
    alignItems: 'center',
    marginTop: 16,
    marginBottom: 20
  },
  loginLinkText: {
    color: '#2563EB',
    fontSize: 14,
    fontWeight: '600'
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20
  },
  modalContent: {
    backgroundColor: '#fff',
    borderRadius: 12,
    width: '100%',
    maxHeight: '80%',
    ...Platform.select({
      web: {
        boxShadow: '0px 10px 30px rgba(0, 0, 0, 0.3)',
      },
      default: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.25,
        shadowRadius: 3.84,
        elevation: 5,
      }
    })
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB'
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#111827'
  },
  closeButton: {
    padding: 4
  },
  closeButtonText: {
    fontSize: 18,
    color: '#6B7280',
    fontWeight: 'bold'
  },
  categoryItem: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6'
  },
  categoryItemSelected: {
    backgroundColor: '#EFF6FF',
    borderLeftWidth: 4,
    borderLeftColor: '#2563EB'
  },
  categoryName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 4
  },
  categoryDescription: {
    fontSize: 14,
    color: '#6B7280'
  },
  emptyCategories: {
    padding: 20,
    alignItems: 'center'
  },
  emptyText: {
    fontSize: 16,
    color: '#6B7280',
    textAlign: 'center'
  }
});
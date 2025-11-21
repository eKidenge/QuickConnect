import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
	StyleSheet,
  FlatList,
  TouchableOpacity,
  TextInput,
  Alert,
  ActivityIndicator,
  RefreshControl,
  Modal,
  ScrollView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

interface Transaction {
  id: number;
  session_id: number;
  amount: number;
  status: string;
  payment_method: string;
  created_at: string;
  completed_at: string;
  professional_name: string;
  client_name: string;
  session_type: string;
}

interface TransactionFilters {
  status: string;
  payment_method: string;
  search: string;
  date_range: string;
}

export default function TransactionHistory() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
	const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [filters, setFilters] = useState<TransactionFilters>({
    status: 'all',
    payment_method: 'all',
    search: '',
    date_range: 'all',
  });

	const API_BASE_URL = 'http://192.168.100.38:8000/api';

  useEffect(() => {
    loadTransactions();
  }, [filters]);

  const loadTransactions = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        ...(filters.status !== 'all' && { status: filters.status }),
        ...(filters.payment_method !== 'all' && { payment_method: filters.payment_method }),
        ...(filters.search && { search: filters.search }),
        ...(filters.date_range !== 'all' && { date_range: filters.date_range }),
      });

      const response = await fetch(`${API_BASE_URL}/admin/transactions/?${params}`);
      const data = await response.json();

      if (response.ok) {
        setTransactions(data.transactions);
      } else {
        Alert.alert('Error', data.error || 'Failed to load transactions');
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to connect to server');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadTransactions();
  };

  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'completed': return styles.statusCompleted;
      case 'pending': return styles.statusPending;
      case 'failed': return styles.statusFailed;
      case 'refunded': return styles.statusRefunded;
      default: return styles.statusPending;
    }
  };

  const renderTransactionItem = ({ item }: { item: Transaction }) => (
    <TouchableOpacity
      style={styles.transactionCard}
      onPress={() => {
        setSelectedTransaction(item);
        setDetailModalVisible(true);
      }}
    >
      <View style={styles.transactionHeader}>
        <View style={styles.transactionInfo}>
          <Text style={styles.transactionAmount}>${item.amount.toFixed(2)}</Text>
          <Text style={styles.transactionSession}>Session #{item.session_id}</Text>
        </View>
        <View style={[styles.statusBadge, getStatusStyle(item.status)]}>
          <Text style={styles.statusText}>{item.status}</Text>
        </View>
      </View>
      
      <View style={styles.transactionDetails}>
        <Text style={styles.detailText}>
          <Ionicons name="person-outline" size={14} /> {item.professional_name}
        </Text>
        <Text style={styles.detailText}>
          <Ionicons name="card-outline" size={14} /> {item.payment_method}
        </Text>
      </View>
      
      <Text style={styles.transactionDate}>
		{new Date(item.created_at).toLocaleDateString()} • {item.session_type}
      </Text>
    </TouchableOpacity>
  );

  const renderFilters = () => (
    <View style={styles.filterContainer}>
      <TextInput
        style={styles.searchInput}
        placeholder="Search transactions..."
        value={filters.search}
        onChangeText={(text) => setFilters(prev => ({ ...prev, search: text }))}
      />
      
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filterScroll}>
        <View style={styles.filterRow}>
          <TouchableOpacity
            style={[styles.filterButton, filters.status === 'all' && styles.filterButtonActive]}
            onPress={() => setFilters(prev => ({ ...prev, status: 'all' }))}
          >
            <Text style={[styles.filterButtonText, filters.status === 'all' && styles.filterButtonTextActive]}>
              All Status
            </Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            style={[styles.filterButton, filters.status === 'completed' && styles.filterButtonActive]}
            onPress={() => setFilters(prev => ({ ...prev, status: 'completed' }))}
          >
            <Text style={[styles.filterButtonText, filters.status === 'completed' && styles.filterButtonTextActive]}>
              Completed
            </Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            style={[styles.filterButton, filters.status === 'pending' && styles.filterButtonActive]}
            onPress={() => setFilters(prev => ({ ...prev, status: 'pending' }))}
          >
            <Text style={[styles.filterButtonText, filters.status === 'pending' && styles.filterButtonTextActive]}>
              Pending
            </Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            style={[styles.filterButton, filters.status === 'failed' && styles.filterButtonActive]}
            onPress={() => setFilters(prev => ({ ...prev, status: 'failed' }))}
          >
            <Text style={[styles.filterButtonText, filters.status === 'failed' && styles.filterButtonTextActive]}>
              Failed
            </Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </View>
  );

  if (loading && transactions.length === 0) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Loading transactions...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Transaction History</Text>
      
      {renderFilters()}

      <FlatList
        data={transactions}
        renderItem={renderTransactionItem}
        keyExtractor={(item) => item.id.toString()}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Ionicons name="card-outline" size={64} color="#ccc" />
            <Text style={styles.emptyText}>No transactions found</Text>
          </View>
        }
        contentContainerStyle={styles.listContent}
      />

      {/* Transaction Detail Modal */}
      <Modal
        visible={detailModalVisible}
        animationType="slide"
        onRequestClose={() => setDetailModalVisible(false)}
      >
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Transaction Details</Text>
            <TouchableOpacity onPress={() => setDetailModalVisible(false)}>
              <Ionicons name="close" size={24} color="#000" />
            </TouchableOpacity>
          </View>

          {selectedTransaction && (
            <ScrollView style={styles.modalContent}>
              <View style={styles.detailSection}>
                <Text style={styles.detailLabel}>Transaction Information</Text>
                <View style={styles.detailRow}>
                  <Text style={styles.detailKey}>Transaction ID:</Text>
                  <Text style={styles.detailValue}>#{selectedTransaction.id}</Text>
                </View>
                <View style={styles.detailRow}>
                  <Text style={styles.detailKey}>Session ID:</Text>
                  <Text style={styles.detailValue}>#{selectedTransaction.session_id}</Text>
                </View>
                <View style={styles.detailRow}>
                  <Text style={styles.detailKey}>Amount:</Text>
                  <Text style={[styles.detailValue, styles.amountText]}>
                    ${selectedTransaction.amount.toFixed(2)}
                  </Text>
                </View>
                <View style={styles.detailRow}>
                  <Text style={styles.detailKey}>Status:</Text>
                  <View style={[styles.statusBadge, getStatusStyle(selectedTransaction.status)]}>
                    <Text style={styles.statusText}>{selectedTransaction.status}</Text>
                  </View>
                </View>
                <View style={styles.detailRow}>
                  <Text style={styles.detailKey}>Payment Method:</Text>
                  <Text style={styles.detailValue}>{selectedTransaction.payment_method}</Text>
                </View>
              </View>

              <View style={styles.detailSection}>
                <Text style={styles.detailLabel}>Session Details</Text>
                <View style={styles.detailRow}>
                  <Text style={styles.detailKey}>Professional:</Text>
                  <Text style={styles.detailValue}>{selectedTransaction.professional_name}</Text>
                </View>
                <View style={styles.detailRow}>
                  <Text style={styles.detailKey}>Session Type:</Text>
                  <Text style={styles.detailValue}>{selectedTransaction.session_type}</Text>
                </View>
              </View>

              <View style={styles.detailSection}>
                <Text style={styles.detailLabel}>Timestamps</Text>
                <View style={styles.detailRow}>
                  <Text style={styles.detailKey}>Created:</Text>
                  <Text style={styles.detailValue}>
					{new Date(selectedTransaction.created_at).toLocaleString()}
                  </Text>
                </View>
                <View style={styles.detailRow}>
                  <Text style={styles.detailKey}>Completed:</Text>
                  <Text style={styles.detailValue}>
                    {selectedTransaction.completed_at 
						? new Date(selectedTransaction.completed_at).toLocaleString()
                      : 'Not completed'
                    }
                  </Text>
                </View>
              </View>
            </ScrollView>
          )}
        </View>
      </Modal>
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
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    padding: 20,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#666',
  },
  filterContainer: {
    backgroundColor: '#fff',
    padding: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  searchInput: {
    backgroundColor: '#f8f8f8',
    padding: 12,
    borderRadius: 8,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  filterScroll: {
    marginHorizontal: -5,
  },
  filterRow: {
    flexDirection: 'row',
  },
  filterButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: '#f8f8f8',
    marginHorizontal: 4,
  },
  filterButtonActive: {
    backgroundColor: '#007AFF',
  },
  filterButtonText: {
    fontSize: 14,
    color: '#666',
  },
  filterButtonTextActive: {
    color: '#fff',
  },
  listContent: {
    padding: 10,
  },
  transactionCard: {
    backgroundColor: '#fff',
    padding: 15,
    borderRadius: 8,
    marginBottom: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 2,
  },
  transactionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 10,
  },
  transactionInfo: {
    flex: 1,
  },
  transactionAmount: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 4,
  },
  transactionSession: {
    fontSize: 14,
    color: '#666',
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  statusCompleted: {
    backgroundColor: '#d4edda',
  },
  statusPending: {
    backgroundColor: '#fff3cd',
  },
  statusFailed: {
    backgroundColor: '#f8d7da',
  },
  statusRefunded: {
    backgroundColor: '#e2e3e5',
  },
  statusText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#155724',
  },
  transactionDetails: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  detailText: {
    fontSize: 14,
    color: '#666',
  },
  transactionDate: {
    fontSize: 12,
    color: '#999',
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    padding: 40,
  },
  emptyText: {
    fontSize: 16,
    color: '#999',
    marginTop: 10,
  },
  modalContainer: {
    flex: 1,
    backgroundColor: '#fff',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  modalContent: {
    flex: 1,
    padding: 20,
  },
  detailSection: {
    marginBottom: 24,
  },
  detailLabel: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 12,
    color: '#333',
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  detailKey: {
    fontSize: 14,
    fontWeight: '500',
    color: '#666',
  },
  detailValue: {
    fontSize: 14,
    color: '#333',
    fontWeight: '500',
  },
  amountText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#007AFF',
  },
});
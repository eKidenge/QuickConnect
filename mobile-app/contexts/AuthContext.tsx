import React, { createContext, useContext, useState, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { apiService } from '../services/api';

interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  user_type: string;
  is_staff: boolean;
  is_superuser: boolean;
}

interface Professional {
  id: number;
  name: string;
  specialization: string;
  category: string | null;
  status: string;
  is_approved: boolean;
  rate: number;
  available: boolean;
  online_status: boolean;
  email?: string;
  phone?: string;
  experience_years?: number;
  bio?: string;
  average_rating?: number;
  total_sessions?: number;
}

interface Favorite {
  id: number;
  user: number;
  professional: Professional;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  professional: Professional | null;
  token: string | null;
  favorites: Favorite[];
  login: (username: string, password: string) => Promise<void>;
  register: (userData: any) => Promise<void>;
  logout: () => Promise<void>;
  loading: boolean;
  isAuthenticated: boolean;
  isProfessional: boolean;
  isProfessionalApproved: boolean;
  setProfessionalOnline: (online: boolean) => Promise<void>;
  updateProfessionalAvailability: (available: boolean) => Promise<void>;
  refreshProfessionalData: () => Promise<void>;
  // Favorites methods
  addToFavorites: (professionalId: number) => Promise<void>;
  removeFromFavorites: (professionalId: number) => Promise<void>;
  getFavorites: () => Promise<void>;
  refreshFavorites: () => Promise<void>;
  isProfessionalInFavorites: (professionalId: number) => boolean;
  favoritesLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [professional, setProfessional] = useState<Professional | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [favorites, setFavorites] = useState<Favorite[]>([]);
  const [loading, setLoading] = useState(true);
  const [favoritesLoading, setFavoritesLoading] = useState(false);

  const isProfessional = user?.user_type === 'professional';
  const isProfessionalApproved = professional?.is_approved || false;
  const isAuthenticated = !!user && !!token;

  useEffect(() => {
    checkAuthStatus();
  }, []);

  // Load favorites when user authenticates
  useEffect(() => {
    if (isAuthenticated && user?.user_type === 'client') {
      getFavorites();
    }
  }, [isAuthenticated, user?.user_type]);

  const checkAuthStatus = async () => {
    try {
      console.log('🔐 AUTH CONTEXT: Checking authentication state...');
      
      const [storedToken, storedUser, storedProfessional, storedFavorites] = await Promise.all([
        AsyncStorage.getItem('auth_token'),
        AsyncStorage.getItem('user_data'),
        AsyncStorage.getItem('professional_data'),
        AsyncStorage.getItem('user_favorites')
      ]);
      
      console.log('📦 AUTH CONTEXT: Stored data found:', {
        hasToken: !!storedToken,
        hasUser: !!storedUser,
        hasProfessional: !!storedProfessional,
        hasFavorites: !!storedFavorites,
        token: storedToken ? `${storedToken.substring(0, 10)}...` : 'none'
      });

      if (storedToken && storedUser) {
        const userData = JSON.parse(storedUser);
        setToken(storedToken);
        setUser(userData);
        
        console.log('✅ AUTH CONTEXT: User authenticated on app start:', {
          username: userData.username,
          userType: userData.user_type,
          isAuthenticated: true
        });
        
        if (storedProfessional) {
          const professionalData = JSON.parse(storedProfessional);
          console.log('👨‍⚕️ AUTH CONTEXT: Professional data from storage:', professionalData);
          setProfessional(professionalData);
        } else if (userData.user_type === 'professional') {
          console.log('🔄 AUTH CONTEXT: User is professional but no professional data found, fetching...');
          await refreshProfessionalData();
        }

        // Load favorites if user is client
        if (storedFavorites && userData.user_type === 'client') {
          const favoritesData = JSON.parse(storedFavorites);
          console.log('❤️ AUTH CONTEXT: Favorites data from storage:', favoritesData);
          setFavorites(favoritesData);
        }
      } else {
        console.log('❌ AUTH CONTEXT: No authentication data found');
        setToken(null);
        setUser(null);
        setProfessional(null);
        setFavorites([]);
      }
    } catch (error) {
      console.error('❌ AUTH CONTEXT: Auth check failed:', error);
      setToken(null);
      setUser(null);
      setProfessional(null);
      setFavorites([]);
    } finally {
      setLoading(false);
    }
  };

  const refreshProfessionalData = async () => {
    if (!token || !user) return;
    
    try {
      console.log('🔄 AUTH CONTEXT: Refreshing professional data...');
      const professionalData = await apiService.getProfessionalProfile(user.id, token);
      console.log('✅ AUTH CONTEXT: Professional data refreshed:', professionalData);
      
      if (professionalData) {
        setProfessional(professionalData);
        await AsyncStorage.setItem('professional_data', JSON.stringify(professionalData));
      }
    } catch (error) {
      console.error('❌ AUTH CONTEXT: Failed to refresh professional data:', error);
    }
  };

  // Favorites Methods
  const getFavorites = async (): Promise<void> => {
    if (!token || !user || user.user_type !== 'client') return;
    
    try {
      setFavoritesLoading(true);
      console.log('❤️ AUTH CONTEXT: Fetching favorites...');
      
      const favoritesData = await apiService.getFavorites(token);
      console.log('✅ AUTH CONTEXT: Favorites fetched:', favoritesData);
      
      setFavorites(favoritesData);
      await AsyncStorage.setItem('user_favorites', JSON.stringify(favoritesData));
    } catch (error) {
      console.error('❌ AUTH CONTEXT: Failed to fetch favorites:', error);
      // Don't throw error here to avoid breaking the app
    } finally {
      setFavoritesLoading(false);
    }
  };

  const refreshFavorites = async (): Promise<void> => {
    await getFavorites();
  };

  const addToFavorites = async (professionalId: number): Promise<void> => {
    if (!token || !user || user.user_type !== 'client') {
      throw new Error('Only clients can add favorites');
    }
    
    try {
      console.log('❤️ AUTH CONTEXT: Adding to favorites:', professionalId);
      const response = await apiService.addToFavorites(professionalId, token);
      console.log('✅ AUTH CONTEXT: Added to favorites:', response);
      
      // Refresh favorites list
      await getFavorites();
    } catch (error) {
      console.error('❌ AUTH CONTEXT: Failed to add to favorites:', error);
      throw error;
    }
  };

  const removeFromFavorites = async (professionalId: number): Promise<void> => {
    if (!token || !user || user.user_type !== 'client') {
      throw new Error('Only clients can remove favorites');
    }
    
    try {
      console.log('❤️ AUTH CONTEXT: Removing from favorites:', professionalId);
      await apiService.removeFromFavorites(professionalId, token);
      console.log('✅ AUTH CONTEXT: Removed from favorites');
      
      // Update local state immediately for better UX
      setFavorites(prev => prev.filter(fav => fav.professional.id !== professionalId));
      
      // Also update AsyncStorage
      const updatedFavorites = favorites.filter(fav => fav.professional.id !== professionalId);
      await AsyncStorage.setItem('user_favorites', JSON.stringify(updatedFavorites));
    } catch (error) {
      console.error('❌ AUTH CONTEXT: Failed to remove from favorites:', error);
      throw error;
    }
  };

  const isProfessionalInFavorites = (professionalId: number): boolean => {
    return favorites.some(fav => fav.professional.id === professionalId);
  };

  const login = async (username: string, password: string) => {
    try {
      console.log('🔐 AUTH CONTEXT: Attempting login...', { username });
      const response = await apiService.login(username, password);
      
      if (response.success) {
        console.log('✅ AUTH CONTEXT: Login API response:', {
          username: response.user.username,
          userType: response.user.user_type,
          hasProfessional: !!response.professional,
          token: response.token ? `${response.token.substring(0, 10)}...` : 'none'
        });
        
        // Store all data in AsyncStorage first
        await AsyncStorage.setItem('auth_token', response.token);
        await AsyncStorage.setItem('user_data', JSON.stringify(response.user));
        
        if (response.professional) {
          console.log('👨‍⚕️ AUTH CONTEXT: Professional data received:', response.professional);
          await AsyncStorage.setItem('professional_data', JSON.stringify(response.professional));
          setProfessional(response.professional);
        } else if (response.user.user_type === 'professional') {
          console.log('⚠️ AUTH CONTEXT: User is professional type but no professional profile exists');
          setProfessional(null);
          await AsyncStorage.removeItem('professional_data');
        }

        // Clear favorites if user is professional
        if (response.user.user_type === 'professional') {
          setFavorites([]);
          await AsyncStorage.removeItem('user_favorites');
        }
        
        // Update state LAST - this triggers re-renders
        setToken(response.token);
        setUser(response.user);
        
        console.log('✅ AUTH CONTEXT: Login complete - state updated', {
          isAuthenticated: true,
          userType: response.user.user_type,
          username: response.user.username
        });
      } else {
        throw new Error(response.message);
      }
    } catch (error) {
      console.error('❌ AUTH CONTEXT: Login failed:', error);
      throw error;
    }
  };

  const register = async (userData: any) => {
    try {
      const response = await apiService.register(userData);
      return response;
    } catch (error) {
      throw error;
    }
  };

  const logout = async () => {
    try {
      console.log('🚪 AUTH CONTEXT: Logging out...');
      
      // Update online status if professional
      if (professional) {
        try {
          await setProfessionalOnline(false);
        } catch (error) {
          console.error('❌ AUTH CONTEXT: Failed to update online status during logout:', error);
        }
      }
      
      // Clear AsyncStorage
      await AsyncStorage.multiRemove([
        'auth_token', 
        'user_data', 
        'professional_data',
        'user_favorites'
      ]);
      
      // Update state
      setUser(null);
      setProfessional(null);
      setToken(null);
      setFavorites([]);
      
      console.log('✅ AUTH CONTEXT: Logout successful');
    } catch (error) {
      console.error('❌ AUTH CONTEXT: Logout failed:', error);
      throw error;
    }
  };

  const setProfessionalOnline = async (online: boolean) => {
    if (!professional) return;
    
    try {
      const updatedProfessional = { ...professional, online_status: online };
      setProfessional(updatedProfessional);
      await AsyncStorage.setItem('professional_data', JSON.stringify(updatedProfessional));
      
      if (token) {
        await apiService.updateProfessionalStatus(professional.id, { online_status: online }, token);
      }
    } catch (error) {
      console.error('❌ AUTH CONTEXT: Failed to update online status:', error);
      throw error;
    }
  };

  const updateProfessionalAvailability = async (available: boolean) => {
    if (!professional) return;

    try {
      const updatedProfessional = { ...professional, available };
      setProfessional(updatedProfessional);
      await AsyncStorage.setItem('professional_data', JSON.stringify(updatedProfessional));
      
      if (token) {
        await apiService.updateProfessionalStatus(professional.id, { available }, token);
      }
    } catch (error) {
      console.error('❌ AUTH CONTEXT: Failed to update availability:', error);
      throw error;
    }
  };

  const value: AuthContextType = {
    user,
    professional,
    token,
    favorites,
    login,
    register,
    logout,
    loading,
    isAuthenticated,
    isProfessional,
    isProfessionalApproved,
    setProfessionalOnline,
    updateProfessionalAvailability,
    refreshProfessionalData,
    // Favorites methods
    addToFavorites,
    removeFromFavorites,
    getFavorites,
    refreshFavorites,
    isProfessionalInFavorites,
    favoritesLoading,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
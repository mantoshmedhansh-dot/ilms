/**
 * Dashboard Screen
 */

import React, {useEffect, useState, useCallback} from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import {useNavigation} from '@react-navigation/native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

import {useAuthStore} from '../../store/authStore';
import {ordersApi} from '../../api/orders';
import {inventoryApi} from '../../api/inventory';
import {serviceRequestsApi} from '../../api/serviceRequests';

interface DashboardStats {
  orders: {
    total: number;
    pending: number;
    processing: number;
    shipped: number;
  };
  inventory: {
    total_products: number;
    low_stock: number;
    out_of_stock: number;
  };
  service: {
    total: number;
    open: number;
    in_progress: number;
    pending_assignment: number;
  };
}

export function DashboardScreen(): React.JSX.Element {
  const navigation = useNavigation<any>();
  const {user} = useAuthStore();

  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchDashboardData = useCallback(async () => {
    try {
      const [orderStats, inventoryStats, serviceStats] = await Promise.all([
        ordersApi.getStats(),
        inventoryApi.getStats(),
        serviceRequestsApi.getStats(),
      ]);

      setStats({
        orders: orderStats,
        inventory: inventoryStats,
        service: serviceStats,
      });
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setIsLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchDashboardData();
  }, [fetchDashboardData]);

  const navigateToOrders = () => {
    navigation.navigate('OrdersTab');
  };

  const navigateToInventory = () => {
    navigation.navigate('InventoryTab');
  };

  const navigateToService = () => {
    navigation.navigate('ServiceTab');
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#0066CC" />
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }>
      {/* Welcome Section */}
      <View style={styles.welcomeSection}>
        <Text style={styles.welcomeText}>Welcome back,</Text>
        <Text style={styles.userName}>{user?.name || 'User'}</Text>
      </View>

      {/* Quick Stats */}
      <View style={styles.statsGrid}>
        {/* Orders Card */}
        <TouchableOpacity style={styles.statCard} onPress={navigateToOrders}>
          <View style={[styles.iconContainer, {backgroundColor: '#EEF2FF'}]}>
            <Icon name="clipboard-list" size={24} color="#4F46E5" />
          </View>
          <Text style={styles.statValue}>{stats?.orders.total || 0}</Text>
          <Text style={styles.statLabel}>Total Orders</Text>
          <View style={styles.statBadge}>
            <Text style={styles.statBadgeText}>
              {stats?.orders.pending || 0} pending
            </Text>
          </View>
        </TouchableOpacity>

        {/* Inventory Card */}
        <TouchableOpacity style={styles.statCard} onPress={navigateToInventory}>
          <View style={[styles.iconContainer, {backgroundColor: '#FEF3C7'}]}>
            <Icon name="package-variant" size={24} color="#D97706" />
          </View>
          <Text style={styles.statValue}>
            {stats?.inventory.total_products || 0}
          </Text>
          <Text style={styles.statLabel}>Products</Text>
          <View style={[styles.statBadge, {backgroundColor: '#FEE2E2'}]}>
            <Text style={[styles.statBadgeText, {color: '#DC2626'}]}>
              {stats?.inventory.low_stock || 0} low stock
            </Text>
          </View>
        </TouchableOpacity>

        {/* Service Card */}
        <TouchableOpacity style={styles.statCard} onPress={navigateToService}>
          <View style={[styles.iconContainer, {backgroundColor: '#DCFCE7'}]}>
            <Icon name="wrench" size={24} color="#16A34A" />
          </View>
          <Text style={styles.statValue}>{stats?.service.total || 0}</Text>
          <Text style={styles.statLabel}>Service Requests</Text>
          <View style={styles.statBadge}>
            <Text style={styles.statBadgeText}>
              {stats?.service.open || 0} open
            </Text>
          </View>
        </TouchableOpacity>

        {/* Processing Card */}
        <TouchableOpacity style={styles.statCard} onPress={navigateToOrders}>
          <View style={[styles.iconContainer, {backgroundColor: '#F3E8FF'}]}>
            <Icon name="truck-delivery" size={24} color="#9333EA" />
          </View>
          <Text style={styles.statValue}>{stats?.orders.processing || 0}</Text>
          <Text style={styles.statLabel}>Processing</Text>
          <View style={[styles.statBadge, {backgroundColor: '#E0E7FF'}]}>
            <Text style={[styles.statBadgeText, {color: '#4F46E5'}]}>
              {stats?.orders.shipped || 0} shipped
            </Text>
          </View>
        </TouchableOpacity>
      </View>

      {/* Quick Actions */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Quick Actions</Text>
        <View style={styles.actionsGrid}>
          <TouchableOpacity
            style={styles.actionButton}
            onPress={navigateToOrders}>
            <Icon name="plus-circle" size={28} color="#0066CC" />
            <Text style={styles.actionText}>New Order</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.actionButton}
            onPress={navigateToInventory}>
            <Icon name="barcode-scan" size={28} color="#0066CC" />
            <Text style={styles.actionText}>Scan Stock</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.actionButton}
            onPress={navigateToService}>
            <Icon name="headset" size={28} color="#0066CC" />
            <Text style={styles.actionText}>New Request</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.actionButton}>
            <Icon name="file-document" size={28} color="#0066CC" />
            <Text style={styles.actionText}>Reports</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Alerts Section */}
      {(stats?.inventory.out_of_stock || 0) > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Alerts</Text>
          <TouchableOpacity
            style={styles.alertCard}
            onPress={navigateToInventory}>
            <View style={styles.alertIcon}>
              <Icon name="alert-circle" size={24} color="#DC2626" />
            </View>
            <View style={styles.alertContent}>
              <Text style={styles.alertTitle}>Out of Stock Items</Text>
              <Text style={styles.alertMessage}>
                {stats?.inventory.out_of_stock} products are out of stock
              </Text>
            </View>
            <Icon name="chevron-right" size={24} color="#9CA3AF" />
          </TouchableOpacity>
        </View>
      )}

      {(stats?.service.pending_assignment || 0) > 0 && (
        <TouchableOpacity style={styles.alertCard} onPress={navigateToService}>
          <View style={[styles.alertIcon, {backgroundColor: '#FEF3C7'}]}>
            <Icon name="account-clock" size={24} color="#D97706" />
          </View>
          <View style={styles.alertContent}>
            <Text style={styles.alertTitle}>Pending Assignment</Text>
            <Text style={styles.alertMessage}>
              {stats?.service.pending_assignment} service requests need
              technician
            </Text>
          </View>
          <Icon name="chevron-right" size={24} color="#9CA3AF" />
        </TouchableOpacity>
      )}

      <View style={styles.bottomPadding} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F7FA',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F5F7FA',
  },
  welcomeSection: {
    padding: 20,
    paddingTop: 16,
  },
  welcomeText: {
    fontSize: 16,
    color: '#666666',
  },
  userName: {
    fontSize: 24,
    fontWeight: '700',
    color: '#1A1A1A',
  },
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: 12,
  },
  statCard: {
    width: '47%',
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    margin: '1.5%',
    shadowColor: '#000',
    shadowOffset: {width: 0, height: 1},
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  iconContainer: {
    width: 44,
    height: 44,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
  },
  statValue: {
    fontSize: 28,
    fontWeight: '700',
    color: '#1A1A1A',
  },
  statLabel: {
    fontSize: 13,
    color: '#666666',
    marginTop: 4,
  },
  statBadge: {
    backgroundColor: '#F3F4F6',
    borderRadius: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    alignSelf: 'flex-start',
    marginTop: 8,
  },
  statBadgeText: {
    fontSize: 12,
    color: '#6B7280',
    fontWeight: '500',
  },
  section: {
    padding: 20,
    paddingTop: 8,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1A1A1A',
    marginBottom: 12,
  },
  actionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 8,
    shadowColor: '#000',
    shadowOffset: {width: 0, height: 1},
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  actionButton: {
    width: '25%',
    alignItems: 'center',
    padding: 12,
  },
  actionText: {
    fontSize: 12,
    color: '#374151',
    marginTop: 6,
    textAlign: 'center',
  },
  alertCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 8,
    shadowColor: '#000',
    shadowOffset: {width: 0, height: 1},
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  alertIcon: {
    width: 44,
    height: 44,
    borderRadius: 10,
    backgroundColor: '#FEE2E2',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  alertContent: {
    flex: 1,
  },
  alertTitle: {
    fontSize: 15,
    fontWeight: '600',
    color: '#1A1A1A',
  },
  alertMessage: {
    fontSize: 13,
    color: '#666666',
    marginTop: 2,
  },
  bottomPadding: {
    height: 20,
  },
});

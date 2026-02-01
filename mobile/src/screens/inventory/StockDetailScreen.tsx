/**
 * Stock Detail Screen
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
  Alert,
} from 'react-native';
import {RouteProp, useRoute} from '@react-navigation/native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

import {inventoryApi, StockItem, StockMovement} from '../../api/inventory';
import {InventoryStackParamList} from '../../navigation/MainNavigator';

type StockDetailRouteProp = RouteProp<InventoryStackParamList, 'StockDetail'>;

const STOCK_STATUS_COLORS: Record<string, {bg: string; text: string}> = {
  IN_STOCK: {bg: '#DCFCE7', text: '#16A34A'},
  LOW_STOCK: {bg: '#FEF3C7', text: '#D97706'},
  OUT_OF_STOCK: {bg: '#FEE2E2', text: '#DC2626'},
};

const MOVEMENT_TYPE_ICONS: Record<string, {icon: string; color: string}> = {
  IN: {icon: 'arrow-down', color: '#16A34A'},
  OUT: {icon: 'arrow-up', color: '#DC2626'},
  TRANSFER: {icon: 'swap-horizontal', color: '#4F46E5'},
  ADJUSTMENT: {icon: 'pencil', color: '#D97706'},
};

export function StockDetailScreen(): React.JSX.Element {
  const route = useRoute<StockDetailRouteProp>();
  const {sku} = route.params;

  const [stockItem, setStockItem] = useState<StockItem | null>(null);
  const [movements, setMovements] = useState<StockMovement[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [item, movementData] = await Promise.all([
        inventoryApi.getStockBySku(sku),
        inventoryApi.getMovements({sku, size: 10}),
      ]);
      setStockItem(item);
      setMovements(movementData.items);
    } catch (error) {
      console.error('Failed to fetch stock data:', error);
      Alert.alert('Error', 'Failed to load stock details');
    } finally {
      setIsLoading(false);
      setRefreshing(false);
    }
  }, [sku]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchData();
  }, [fetchData]);

  const getStockStatus = (quantity: number, reorderLevel: number) => {
    if (quantity === 0) return 'OUT_OF_STOCK';
    if (quantity <= reorderLevel) return 'LOW_STOCK';
    return 'IN_STOCK';
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#0066CC" />
      </View>
    );
  }

  if (!stockItem) {
    return (
      <View style={styles.errorContainer}>
        <Icon name="alert-circle-outline" size={64} color="#DC2626" />
        <Text style={styles.errorText}>Stock item not found</Text>
      </View>
    );
  }

  const stockStatus = getStockStatus(stockItem.quantity, stockItem.reorder_level);
  const statusStyle =
    STOCK_STATUS_COLORS[stockStatus] || STOCK_STATUS_COLORS.IN_STOCK;

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }>
      {/* Product Header */}
      <View style={styles.header}>
        <View style={styles.headerTop}>
          <Text style={styles.productName}>{stockItem.product_name}</Text>
          <View style={[styles.statusBadge, {backgroundColor: statusStyle.bg}]}>
            <Text style={[styles.statusText, {color: statusStyle.text}]}>
              {stockStatus.replace('_', ' ')}
            </Text>
          </View>
        </View>
        <Text style={styles.sku}>SKU: {sku}</Text>
      </View>

      {/* Stock Metrics */}
      <View style={styles.metricsSection}>
        <View style={styles.metricsGrid}>
          <View style={styles.metricCard}>
            <Icon name="package-variant" size={24} color="#0066CC" />
            <Text style={styles.metricValue}>{stockItem.quantity}</Text>
            <Text style={styles.metricLabel}>Total Stock</Text>
          </View>
          <View style={styles.metricCard}>
            <Icon name="lock" size={24} color="#D97706" />
            <Text style={styles.metricValue}>{stockItem.reserved}</Text>
            <Text style={styles.metricLabel}>Reserved</Text>
          </View>
          <View style={styles.metricCard}>
            <Icon name="check-circle" size={24} color="#16A34A" />
            <Text style={styles.metricValue}>{stockItem.available}</Text>
            <Text style={styles.metricLabel}>Available</Text>
          </View>
          <View style={styles.metricCard}>
            <Icon name="alert" size={24} color="#DC2626" />
            <Text style={styles.metricValue}>{stockItem.reorder_level}</Text>
            <Text style={styles.metricLabel}>Reorder Level</Text>
          </View>
        </View>
      </View>

      {/* Warehouse Info */}
      {stockItem.warehouse_name && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Location</Text>
          <View style={styles.card}>
            <View style={styles.infoRow}>
              <Icon name="warehouse" size={20} color="#6B7280" />
              <View style={styles.infoContent}>
                <Text style={styles.infoLabel}>Warehouse</Text>
                <Text style={styles.infoValue}>{stockItem.warehouse_name}</Text>
              </View>
            </View>
            {stockItem.bin_location && (
              <View style={styles.infoRow}>
                <Icon name="map-marker" size={20} color="#6B7280" />
                <View style={styles.infoContent}>
                  <Text style={styles.infoLabel}>Bin Location</Text>
                  <Text style={styles.infoValue}>{stockItem.bin_location}</Text>
                </View>
              </View>
            )}
          </View>
        </View>
      )}

      {/* Stock Movements */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Recent Movements</Text>
          <TouchableOpacity>
            <Text style={styles.viewAllText}>View All</Text>
          </TouchableOpacity>
        </View>

        {movements.length === 0 ? (
          <View style={styles.emptyMovements}>
            <Icon name="history" size={40} color="#D1D5DB" />
            <Text style={styles.emptyText}>No movements yet</Text>
          </View>
        ) : (
          <View style={styles.card}>
            {movements.map((movement, index) => {
              const typeStyle =
                MOVEMENT_TYPE_ICONS[movement.type] || MOVEMENT_TYPE_ICONS.IN;
              return (
                <View
                  key={movement.id}
                  style={[
                    styles.movementRow,
                    index < movements.length - 1 && styles.movementBorder,
                  ]}>
                  <View
                    style={[
                      styles.movementIcon,
                      {backgroundColor: `${typeStyle.color}20`},
                    ]}>
                    <Icon
                      name={typeStyle.icon}
                      size={16}
                      color={typeStyle.color}
                    />
                  </View>
                  <View style={styles.movementInfo}>
                    <Text style={styles.movementType}>{movement.type}</Text>
                    <Text style={styles.movementDate}>
                      {formatDate(movement.created_at)}
                    </Text>
                    {movement.reference && (
                      <Text style={styles.movementRef}>
                        Ref: {movement.reference}
                      </Text>
                    )}
                  </View>
                  <Text
                    style={[
                      styles.movementQty,
                      {color: movement.type === 'IN' ? '#16A34A' : '#DC2626'},
                    ]}>
                    {movement.type === 'IN' ? '+' : '-'}
                    {movement.quantity}
                  </Text>
                </View>
              );
            })}
          </View>
        )}
      </View>

      {/* Actions */}
      <View style={styles.actionsSection}>
        <TouchableOpacity style={styles.primaryButton}>
          <Icon name="swap-horizontal" size={20} color="#FFFFFF" />
          <Text style={styles.primaryButtonText}>Transfer Stock</Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.secondaryButton}>
          <Icon name="pencil" size={20} color="#0066CC" />
          <Text style={styles.secondaryButtonText}>Adjust Stock</Text>
        </TouchableOpacity>
      </View>

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
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F5F7FA',
  },
  errorText: {
    fontSize: 18,
    color: '#DC2626',
    marginTop: 16,
  },
  header: {
    backgroundColor: '#FFFFFF',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  headerTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 4,
  },
  productName: {
    fontSize: 20,
    fontWeight: '700',
    color: '#1A1A1A',
    flex: 1,
    marginRight: 12,
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '600',
  },
  sku: {
    fontSize: 14,
    color: '#6B7280',
  },
  metricsSection: {
    padding: 16,
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginHorizontal: -6,
  },
  metricCard: {
    width: '47%',
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    margin: '1.5%',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: {width: 0, height: 1},
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  metricValue: {
    fontSize: 28,
    fontWeight: '700',
    color: '#1A1A1A',
    marginTop: 8,
  },
  metricLabel: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 4,
  },
  section: {
    padding: 16,
    paddingTop: 0,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
  },
  viewAllText: {
    fontSize: 14,
    color: '#0066CC',
    fontWeight: '500',
  },
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: {width: 0, height: 1},
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  infoContent: {
    marginLeft: 12,
    flex: 1,
  },
  infoLabel: {
    fontSize: 12,
    color: '#9CA3AF',
  },
  infoValue: {
    fontSize: 15,
    color: '#1A1A1A',
    fontWeight: '500',
  },
  emptyMovements: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 32,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: {width: 0, height: 1},
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  emptyText: {
    fontSize: 14,
    color: '#9CA3AF',
    marginTop: 8,
  },
  movementRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
  },
  movementBorder: {
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  movementIcon: {
    width: 36,
    height: 36,
    borderRadius: 18,
    justifyContent: 'center',
    alignItems: 'center',
  },
  movementInfo: {
    flex: 1,
    marginLeft: 12,
  },
  movementType: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1A1A1A',
  },
  movementDate: {
    fontSize: 12,
    color: '#9CA3AF',
    marginTop: 2,
  },
  movementRef: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 2,
  },
  movementQty: {
    fontSize: 16,
    fontWeight: '700',
  },
  actionsSection: {
    padding: 16,
  },
  primaryButton: {
    backgroundColor: '#0066CC',
    borderRadius: 10,
    padding: 16,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  secondaryButton: {
    backgroundColor: '#FFFFFF',
    borderRadius: 10,
    padding: 16,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#0066CC',
  },
  secondaryButtonText: {
    color: '#0066CC',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  bottomPadding: {
    height: 32,
  },
});

/**
 * Inventory Screen
 */

import React, {useEffect, useState, useCallback} from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  RefreshControl,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
} from 'react-native';
import {useNavigation} from '@react-navigation/native';
import {NativeStackNavigationProp} from '@react-navigation/native-stack';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

import {inventoryApi, StockItem} from '../../api/inventory';
import {InventoryStackParamList} from '../../navigation/MainNavigator';

type InventoryNavigationProp = NativeStackNavigationProp<
  InventoryStackParamList,
  'Inventory'
>;

const STOCK_STATUS_COLORS: Record<string, {bg: string; text: string}> = {
  IN_STOCK: {bg: '#DCFCE7', text: '#16A34A'},
  LOW_STOCK: {bg: '#FEF3C7', text: '#D97706'},
  OUT_OF_STOCK: {bg: '#FEE2E2', text: '#DC2626'},
};

export function InventoryScreen(): React.JSX.Element {
  const navigation = useNavigation<InventoryNavigationProp>();

  const [stockItems, setStockItems] = useState<StockItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFilter, setSelectedFilter] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  const fetchInventory = useCallback(
    async (reset = false) => {
      try {
        const currentPage = reset ? 1 : page;
        const response = await inventoryApi.getStock({
          page: currentPage,
          size: 20,
          search: searchQuery || undefined,
          stock_status: selectedFilter || undefined,
        });

        if (reset) {
          setStockItems(response.items);
          setPage(2);
        } else {
          setStockItems(prev => [...prev, ...response.items]);
          setPage(prev => prev + 1);
        }
        setHasMore(response.items.length === 20);
      } catch (error) {
        console.error('Failed to fetch inventory:', error);
      } finally {
        setIsLoading(false);
        setRefreshing(false);
      }
    },
    [page, searchQuery, selectedFilter],
  );

  useEffect(() => {
    setIsLoading(true);
    fetchInventory(true);
  }, [searchQuery, selectedFilter]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchInventory(true);
  }, [fetchInventory]);

  const onEndReached = () => {
    if (!isLoading && hasMore) {
      fetchInventory(false);
    }
  };

  const navigateToDetail = (sku: string) => {
    navigation.navigate('StockDetail', {sku});
  };

  const getStockStatus = (quantity: number, reorderLevel: number) => {
    if (quantity === 0) return 'OUT_OF_STOCK';
    if (quantity <= reorderLevel) return 'LOW_STOCK';
    return 'IN_STOCK';
  };

  const renderFilterBar = () => {
    const filters = [
      {key: null, label: 'All'},
      {key: 'IN_STOCK', label: 'In Stock'},
      {key: 'LOW_STOCK', label: 'Low Stock'},
      {key: 'OUT_OF_STOCK', label: 'Out of Stock'},
    ];

    return (
      <View style={styles.filterContainer}>
        <FlatList
          horizontal
          showsHorizontalScrollIndicator={false}
          data={filters}
          keyExtractor={item => item.label}
          renderItem={({item}) => (
            <TouchableOpacity
              style={[
                styles.filterChip,
                selectedFilter === item.key && styles.filterChipActive,
              ]}
              onPress={() => setSelectedFilter(item.key)}>
              <Text
                style={[
                  styles.filterChipText,
                  selectedFilter === item.key && styles.filterChipTextActive,
                ]}>
                {item.label}
              </Text>
            </TouchableOpacity>
          )}
        />
      </View>
    );
  };

  const renderStockItem = ({item}: {item: StockItem}) => {
    const stockStatus = getStockStatus(item.quantity, item.reorder_level);
    const statusStyle =
      STOCK_STATUS_COLORS[stockStatus] || STOCK_STATUS_COLORS.IN_STOCK;

    return (
      <TouchableOpacity
        style={styles.stockCard}
        onPress={() => navigateToDetail(item.sku)}>
        <View style={styles.stockHeader}>
          <View style={styles.productInfo}>
            <Text style={styles.productName} numberOfLines={2}>
              {item.product_name}
            </Text>
            <Text style={styles.sku}>SKU: {item.sku}</Text>
          </View>
          <View style={[styles.statusBadge, {backgroundColor: statusStyle.bg}]}>
            <Text style={[styles.statusText, {color: statusStyle.text}]}>
              {stockStatus.replace('_', ' ')}
            </Text>
          </View>
        </View>

        <View style={styles.stockDetails}>
          <View style={styles.stockMetric}>
            <Text style={styles.metricValue}>{item.quantity}</Text>
            <Text style={styles.metricLabel}>In Stock</Text>
          </View>
          <View style={styles.stockMetric}>
            <Text style={styles.metricValue}>{item.reserved}</Text>
            <Text style={styles.metricLabel}>Reserved</Text>
          </View>
          <View style={styles.stockMetric}>
            <Text style={styles.metricValue}>{item.available}</Text>
            <Text style={styles.metricLabel}>Available</Text>
          </View>
          <View style={styles.stockMetric}>
            <Text style={styles.metricValue}>{item.reorder_level}</Text>
            <Text style={styles.metricLabel}>Reorder At</Text>
          </View>
        </View>

        {item.warehouse_name && (
          <View style={styles.warehouseRow}>
            <Icon name="warehouse" size={14} color="#6B7280" />
            <Text style={styles.warehouseName}>{item.warehouse_name}</Text>
          </View>
        )}
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <Icon name="magnify" size={20} color="#9CA3AF" style={styles.searchIcon} />
        <TextInput
          style={styles.searchInput}
          placeholder="Search by SKU or product name..."
          placeholderTextColor="#9CA3AF"
          value={searchQuery}
          onChangeText={setSearchQuery}
        />
        {searchQuery.length > 0 && (
          <TouchableOpacity onPress={() => setSearchQuery('')}>
            <Icon name="close-circle" size={20} color="#9CA3AF" />
          </TouchableOpacity>
        )}
        <TouchableOpacity style={styles.scanButton}>
          <Icon name="barcode-scan" size={24} color="#0066CC" />
        </TouchableOpacity>
      </View>

      {/* Filters */}
      {renderFilterBar()}

      {/* Stock List */}
      {isLoading && stockItems.length === 0 ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#0066CC" />
        </View>
      ) : stockItems.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Icon name="package-variant" size={64} color="#D1D5DB" />
          <Text style={styles.emptyText}>No inventory items found</Text>
          <Text style={styles.emptySubtext}>
            {searchQuery
              ? 'Try adjusting your search'
              : 'Inventory items will appear here'}
          </Text>
        </View>
      ) : (
        <FlatList
          data={stockItems}
          renderItem={renderStockItem}
          keyExtractor={item => item.id}
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
          }
          onEndReached={onEndReached}
          onEndReachedThreshold={0.5}
          ListFooterComponent={
            hasMore ? (
              <ActivityIndicator
                style={styles.footerLoader}
                color="#0066CC"
              />
            ) : null
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F7FA',
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    margin: 16,
    marginBottom: 8,
    paddingHorizontal: 12,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  searchIcon: {
    marginRight: 8,
  },
  searchInput: {
    flex: 1,
    paddingVertical: 12,
    fontSize: 16,
    color: '#1A1A1A',
  },
  scanButton: {
    padding: 8,
    marginLeft: 8,
    borderLeftWidth: 1,
    borderLeftColor: '#E5E7EB',
  },
  filterContainer: {
    paddingHorizontal: 16,
    marginBottom: 8,
  },
  filterChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: '#FFFFFF',
    borderRadius: 20,
    marginRight: 8,
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  filterChipActive: {
    backgroundColor: '#0066CC',
    borderColor: '#0066CC',
  },
  filterChipText: {
    fontSize: 14,
    color: '#6B7280',
    fontWeight: '500',
  },
  filterChipTextActive: {
    color: '#FFFFFF',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#374151',
    marginTop: 16,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#9CA3AF',
    marginTop: 4,
  },
  listContent: {
    padding: 16,
    paddingTop: 8,
  },
  stockCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: {width: 0, height: 1},
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  stockHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 16,
  },
  productInfo: {
    flex: 1,
    marginRight: 12,
  },
  productName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1A1A1A',
  },
  sku: {
    fontSize: 13,
    color: '#6B7280',
    marginTop: 4,
  },
  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
  },
  statusText: {
    fontSize: 11,
    fontWeight: '600',
  },
  stockDetails: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#F3F4F6',
  },
  stockMetric: {
    alignItems: 'center',
  },
  metricValue: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1A1A1A',
  },
  metricLabel: {
    fontSize: 11,
    color: '#9CA3AF',
    marginTop: 2,
  },
  warehouseRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  warehouseName: {
    fontSize: 13,
    color: '#6B7280',
    marginLeft: 6,
  },
  footerLoader: {
    paddingVertical: 16,
  },
});

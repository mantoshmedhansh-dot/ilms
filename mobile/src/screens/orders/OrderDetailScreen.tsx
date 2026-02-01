/**
 * Order Detail Screen
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

import {ordersApi, Order} from '../../api/orders';
import {OrderStackParamList} from '../../navigation/MainNavigator';

type OrderDetailRouteProp = RouteProp<OrderStackParamList, 'OrderDetail'>;

const STATUS_COLORS: Record<string, {bg: string; text: string}> = {
  DRAFT: {bg: '#F3F4F6', text: '#6B7280'},
  CONFIRMED: {bg: '#DBEAFE', text: '#1D4ED8'},
  PROCESSING: {bg: '#FEF3C7', text: '#D97706'},
  SHIPPED: {bg: '#E0E7FF', text: '#4F46E5'},
  DELIVERED: {bg: '#DCFCE7', text: '#16A34A'},
  CANCELLED: {bg: '#FEE2E2', text: '#DC2626'},
};

const STATUS_FLOW = ['DRAFT', 'CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED'];

export function OrderDetailScreen(): React.JSX.Element {
  const route = useRoute<OrderDetailRouteProp>();
  const {orderId} = route.params;

  const [order, setOrder] = useState<Order | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);

  const fetchOrder = useCallback(async () => {
    try {
      const data = await ordersApi.getOrder(orderId);
      setOrder(data);
    } catch (error) {
      console.error('Failed to fetch order:', error);
      Alert.alert('Error', 'Failed to load order details');
    } finally {
      setIsLoading(false);
      setRefreshing(false);
    }
  }, [orderId]);

  useEffect(() => {
    fetchOrder();
  }, [fetchOrder]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchOrder();
  }, [fetchOrder]);

  const handleUpdateStatus = async (newStatus: string) => {
    if (!order) return;

    Alert.alert(
      'Update Status',
      `Change order status to ${newStatus}?`,
      [
        {text: 'Cancel', style: 'cancel'},
        {
          text: 'Update',
          onPress: async () => {
            setIsUpdating(true);
            try {
              const updated = await ordersApi.updateStatus(orderId, newStatus);
              setOrder(updated);
              Alert.alert('Success', 'Order status updated');
            } catch (error) {
              console.error('Failed to update status:', error);
              Alert.alert('Error', 'Failed to update order status');
            } finally {
              setIsUpdating(false);
            }
          },
        },
      ],
    );
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

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const getNextStatus = () => {
    if (!order) return null;
    const currentIndex = STATUS_FLOW.indexOf(order.status);
    if (currentIndex === -1 || currentIndex >= STATUS_FLOW.length - 1) {
      return null;
    }
    return STATUS_FLOW[currentIndex + 1];
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#0066CC" />
      </View>
    );
  }

  if (!order) {
    return (
      <View style={styles.errorContainer}>
        <Icon name="alert-circle-outline" size={64} color="#DC2626" />
        <Text style={styles.errorText}>Order not found</Text>
      </View>
    );
  }

  const statusStyle = STATUS_COLORS[order.status] || STATUS_COLORS.DRAFT;
  const nextStatus = getNextStatus();

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }>
      {/* Order Header */}
      <View style={styles.header}>
        <View style={styles.headerTop}>
          <Text style={styles.orderNumber}>{order.order_number}</Text>
          <View style={[styles.statusBadge, {backgroundColor: statusStyle.bg}]}>
            <Text style={[styles.statusText, {color: statusStyle.text}]}>
              {order.status}
            </Text>
          </View>
        </View>
        <Text style={styles.orderDate}>{formatDate(order.order_date)}</Text>
      </View>

      {/* Customer Info */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Customer</Text>
        <View style={styles.card}>
          <View style={styles.infoRow}>
            <Icon name="account" size={20} color="#6B7280" />
            <Text style={styles.infoText}>{order.customer_name}</Text>
          </View>
          {order.customer_phone && (
            <View style={styles.infoRow}>
              <Icon name="phone" size={20} color="#6B7280" />
              <Text style={styles.infoText}>{order.customer_phone}</Text>
            </View>
          )}
          {order.customer_email && (
            <View style={styles.infoRow}>
              <Icon name="email" size={20} color="#6B7280" />
              <Text style={styles.infoText}>{order.customer_email}</Text>
            </View>
          )}
        </View>
      </View>

      {/* Shipping Address */}
      {order.shipping_address && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Shipping Address</Text>
          <View style={styles.card}>
            <View style={styles.infoRow}>
              <Icon name="map-marker" size={20} color="#6B7280" />
              <View style={styles.addressContainer}>
                <Text style={styles.infoText}>
                  {order.shipping_address.address_line1}
                </Text>
                {order.shipping_address.address_line2 && (
                  <Text style={styles.infoText}>
                    {order.shipping_address.address_line2}
                  </Text>
                )}
                <Text style={styles.infoText}>
                  {order.shipping_address.city}, {order.shipping_address.state}{' '}
                  {order.shipping_address.pincode}
                </Text>
              </View>
            </View>
          </View>
        </View>
      )}

      {/* Order Items */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Items ({order.items?.length || 0})</Text>
        <View style={styles.card}>
          {order.items?.map((item, index) => (
            <View
              key={item.id || index}
              style={[
                styles.itemRow,
                index < (order.items?.length || 0) - 1 && styles.itemBorder,
              ]}>
              <View style={styles.itemInfo}>
                <Text style={styles.itemName}>{item.product_name}</Text>
                <Text style={styles.itemSku}>SKU: {item.sku}</Text>
                <Text style={styles.itemQty}>
                  {item.quantity} x {formatCurrency(item.unit_price)}
                </Text>
              </View>
              <Text style={styles.itemTotal}>
                {formatCurrency(item.quantity * item.unit_price)}
              </Text>
            </View>
          ))}
        </View>
      </View>

      {/* Order Summary */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Summary</Text>
        <View style={styles.card}>
          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>Subtotal</Text>
            <Text style={styles.summaryValue}>
              {formatCurrency(order.subtotal)}
            </Text>
          </View>
          {order.discount > 0 && (
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>Discount</Text>
              <Text style={[styles.summaryValue, {color: '#16A34A'}]}>
                -{formatCurrency(order.discount)}
              </Text>
            </View>
          )}
          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>Tax (GST)</Text>
            <Text style={styles.summaryValue}>
              {formatCurrency(order.tax_amount)}
            </Text>
          </View>
          {order.shipping_charges > 0 && (
            <View style={styles.summaryRow}>
              <Text style={styles.summaryLabel}>Shipping</Text>
              <Text style={styles.summaryValue}>
                {formatCurrency(order.shipping_charges)}
              </Text>
            </View>
          )}
          <View style={[styles.summaryRow, styles.totalRow]}>
            <Text style={styles.totalLabel}>Total</Text>
            <Text style={styles.totalValue}>{formatCurrency(order.total)}</Text>
          </View>
        </View>
      </View>

      {/* Action Buttons */}
      {nextStatus && order.status !== 'CANCELLED' && (
        <View style={styles.actionSection}>
          <TouchableOpacity
            style={styles.primaryButton}
            onPress={() => handleUpdateStatus(nextStatus)}
            disabled={isUpdating}>
            {isUpdating ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <>
                <Icon name="check" size={20} color="#FFFFFF" />
                <Text style={styles.primaryButtonText}>
                  Mark as {nextStatus}
                </Text>
              </>
            )}
          </TouchableOpacity>

          {order.status !== 'CANCELLED' && (
            <TouchableOpacity
              style={styles.cancelButton}
              onPress={() => handleUpdateStatus('CANCELLED')}
              disabled={isUpdating}>
              <Icon name="close" size={20} color="#DC2626" />
              <Text style={styles.cancelButtonText}>Cancel Order</Text>
            </TouchableOpacity>
          )}
        </View>
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
    alignItems: 'center',
    marginBottom: 4,
  },
  orderNumber: {
    fontSize: 20,
    fontWeight: '700',
    color: '#1A1A1A',
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
  },
  statusText: {
    fontSize: 13,
    fontWeight: '600',
  },
  orderDate: {
    fontSize: 14,
    color: '#6B7280',
  },
  section: {
    padding: 16,
    paddingBottom: 0,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
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
  infoText: {
    fontSize: 15,
    color: '#1A1A1A',
    marginLeft: 12,
    flex: 1,
  },
  addressContainer: {
    marginLeft: 12,
    flex: 1,
  },
  itemRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingVertical: 12,
  },
  itemBorder: {
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  itemInfo: {
    flex: 1,
    marginRight: 16,
  },
  itemName: {
    fontSize: 15,
    fontWeight: '500',
    color: '#1A1A1A',
  },
  itemSku: {
    fontSize: 13,
    color: '#9CA3AF',
    marginTop: 2,
  },
  itemQty: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 4,
  },
  itemTotal: {
    fontSize: 15,
    fontWeight: '600',
    color: '#1A1A1A',
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  summaryLabel: {
    fontSize: 14,
    color: '#6B7280',
  },
  summaryValue: {
    fontSize: 14,
    color: '#1A1A1A',
  },
  totalRow: {
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
    paddingTop: 12,
    marginTop: 4,
    marginBottom: 0,
  },
  totalLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1A1A1A',
  },
  totalValue: {
    fontSize: 20,
    fontWeight: '700',
    color: '#1A1A1A',
  },
  actionSection: {
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
  cancelButton: {
    backgroundColor: '#FFFFFF',
    borderRadius: 10,
    padding: 16,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#DC2626',
  },
  cancelButtonText: {
    color: '#DC2626',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  bottomPadding: {
    height: 32,
  },
});

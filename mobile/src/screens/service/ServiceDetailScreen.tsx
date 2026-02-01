/**
 * Service Request Detail Screen
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
  Linking,
} from 'react-native';
import {RouteProp, useRoute} from '@react-navigation/native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

import {serviceRequestsApi, ServiceRequest} from '../../api/serviceRequests';
import {ServiceStackParamList} from '../../navigation/MainNavigator';

type ServiceDetailRouteProp = RouteProp<ServiceStackParamList, 'ServiceDetail'>;

const STATUS_COLORS: Record<string, {bg: string; text: string}> = {
  OPEN: {bg: '#DBEAFE', text: '#1D4ED8'},
  IN_PROGRESS: {bg: '#FEF3C7', text: '#D97706'},
  RESOLVED: {bg: '#DCFCE7', text: '#16A34A'},
  CLOSED: {bg: '#F3F4F6', text: '#6B7280'},
  CANCELLED: {bg: '#FEE2E2', text: '#DC2626'},
};

const PRIORITY_COLORS: Record<string, {bg: string; text: string}> = {
  LOW: {bg: '#F3F4F6', text: '#6B7280'},
  MEDIUM: {bg: '#FEF3C7', text: '#D97706'},
  HIGH: {bg: '#FEE2E2', text: '#DC2626'},
  CRITICAL: {bg: '#581C87', text: '#FFFFFF'},
};

const STATUS_FLOW = ['OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'];

export function ServiceDetailScreen(): React.JSX.Element {
  const route = useRoute<ServiceDetailRouteProp>();
  const {requestId} = route.params;

  const [request, setRequest] = useState<ServiceRequest | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);

  const fetchRequest = useCallback(async () => {
    try {
      const data = await serviceRequestsApi.getRequest(requestId);
      setRequest(data);
    } catch (error) {
      console.error('Failed to fetch service request:', error);
      Alert.alert('Error', 'Failed to load service request details');
    } finally {
      setIsLoading(false);
      setRefreshing(false);
    }
  }, [requestId]);

  useEffect(() => {
    fetchRequest();
  }, [fetchRequest]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchRequest();
  }, [fetchRequest]);

  const handleUpdateStatus = async (newStatus: string) => {
    Alert.alert(
      'Update Status',
      `Change status to ${newStatus}?`,
      [
        {text: 'Cancel', style: 'cancel'},
        {
          text: 'Update',
          onPress: async () => {
            setIsUpdating(true);
            try {
              const updated = await serviceRequestsApi.updateStatus(
                requestId,
                newStatus,
              );
              setRequest(updated);
              Alert.alert('Success', 'Status updated successfully');
            } catch (error) {
              console.error('Failed to update status:', error);
              Alert.alert('Error', 'Failed to update status');
            } finally {
              setIsUpdating(false);
            }
          },
        },
      ],
    );
  };

  const handleCall = () => {
    if (request?.customer_phone) {
      Linking.openURL(`tel:${request.customer_phone}`);
    }
  };

  const handleEmail = () => {
    if (request?.customer_email) {
      Linking.openURL(`mailto:${request.customer_email}`);
    }
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

  const getNextStatus = () => {
    if (!request) return null;
    const currentIndex = STATUS_FLOW.indexOf(request.status);
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

  if (!request) {
    return (
      <View style={styles.errorContainer}>
        <Icon name="alert-circle-outline" size={64} color="#DC2626" />
        <Text style={styles.errorText}>Service request not found</Text>
      </View>
    );
  }

  const statusStyle = STATUS_COLORS[request.status] || STATUS_COLORS.OPEN;
  const priorityStyle = PRIORITY_COLORS[request.priority] || PRIORITY_COLORS.MEDIUM;
  const nextStatus = getNextStatus();

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
      }>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerTop}>
          <View style={styles.ticketInfo}>
            <Text style={styles.ticketNumber}>{request.ticket_number}</Text>
            <View style={[styles.priorityBadge, {backgroundColor: priorityStyle.bg}]}>
              <Text style={[styles.priorityText, {color: priorityStyle.text}]}>
                {request.priority}
              </Text>
            </View>
          </View>
          <View style={[styles.statusBadge, {backgroundColor: statusStyle.bg}]}>
            <Text style={[styles.statusText, {color: statusStyle.text}]}>
              {request.status.replace('_', ' ')}
            </Text>
          </View>
        </View>
        <Text style={styles.typeText}>{request.type}</Text>
        <Text style={styles.dateText}>Created: {formatDate(request.created_at)}</Text>
      </View>

      {/* Issue Description */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Issue Description</Text>
        <View style={styles.card}>
          <Text style={styles.issueText}>{request.issue_description}</Text>
        </View>
      </View>

      {/* Customer Info */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Customer</Text>
        <View style={styles.card}>
          <View style={styles.infoRow}>
            <Icon name="account" size={20} color="#6B7280" />
            <Text style={styles.infoText}>{request.customer_name}</Text>
          </View>
          <TouchableOpacity style={styles.infoRow} onPress={handleCall}>
            <Icon name="phone" size={20} color="#0066CC" />
            <Text style={[styles.infoText, styles.linkText]}>
              {request.customer_phone}
            </Text>
          </TouchableOpacity>
          {request.customer_email && (
            <TouchableOpacity style={styles.infoRow} onPress={handleEmail}>
              <Icon name="email" size={20} color="#0066CC" />
              <Text style={[styles.infoText, styles.linkText]}>
                {request.customer_email}
              </Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      {/* Product Info */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Product</Text>
        <View style={styles.card}>
          <View style={styles.infoRow}>
            <Icon name="washing-machine" size={20} color="#6B7280" />
            <Text style={styles.infoText}>{request.product_name}</Text>
          </View>
          {request.product_serial && (
            <View style={styles.infoRow}>
              <Icon name="barcode" size={20} color="#6B7280" />
              <Text style={styles.infoText}>Serial: {request.product_serial}</Text>
            </View>
          )}
        </View>
      </View>

      {/* Service Address */}
      {request.service_address && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Service Address</Text>
          <View style={styles.card}>
            <View style={styles.infoRow}>
              <Icon name="map-marker" size={20} color="#6B7280" />
              <View style={styles.addressContainer}>
                <Text style={styles.infoText}>
                  {request.service_address.address_line1}
                </Text>
                {request.service_address.address_line2 && (
                  <Text style={styles.infoText}>
                    {request.service_address.address_line2}
                  </Text>
                )}
                <Text style={styles.infoText}>
                  {request.service_address.city}, {request.service_address.state}{' '}
                  {request.service_address.pincode}
                </Text>
              </View>
            </View>
          </View>
        </View>
      )}

      {/* Assignment Info */}
      {(request.assigned_to || request.technician_name || request.scheduled_date) && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Assignment</Text>
          <View style={styles.card}>
            {request.technician_name && (
              <View style={styles.infoRow}>
                <Icon name="account-wrench" size={20} color="#6B7280" />
                <Text style={styles.infoText}>{request.technician_name}</Text>
              </View>
            )}
            {request.scheduled_date && (
              <View style={styles.infoRow}>
                <Icon name="calendar-clock" size={20} color="#4F46E5" />
                <Text style={[styles.infoText, {color: '#4F46E5'}]}>
                  Scheduled: {formatDate(request.scheduled_date)}
                </Text>
              </View>
            )}
          </View>
        </View>
      )}

      {/* Resolution */}
      {request.resolution && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Resolution</Text>
          <View style={[styles.card, styles.resolutionCard]}>
            <Text style={styles.resolutionText}>{request.resolution}</Text>
            {request.completed_at && (
              <Text style={styles.completedDate}>
                Completed: {formatDate(request.completed_at)}
              </Text>
            )}
          </View>
        </View>
      )}

      {/* Quick Actions */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Quick Actions</Text>
        <View style={styles.quickActions}>
          <TouchableOpacity style={styles.actionButton} onPress={handleCall}>
            <Icon name="phone" size={24} color="#0066CC" />
            <Text style={styles.actionText}>Call</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionButton}>
            <Icon name="message-text" size={24} color="#0066CC" />
            <Text style={styles.actionText}>SMS</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionButton}>
            <Icon name="whatsapp" size={24} color="#25D366" />
            <Text style={styles.actionText}>WhatsApp</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionButton}>
            <Icon name="directions" size={24} color="#0066CC" />
            <Text style={styles.actionText}>Navigate</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Status Actions */}
      {nextStatus && request.status !== 'CANCELLED' && (
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
                  Mark as {nextStatus.replace('_', ' ')}
                </Text>
              </>
            )}
          </TouchableOpacity>

          {request.status !== 'CANCELLED' && (
            <TouchableOpacity
              style={styles.cancelButton}
              onPress={() => handleUpdateStatus('CANCELLED')}
              disabled={isUpdating}>
              <Icon name="close" size={20} color="#DC2626" />
              <Text style={styles.cancelButtonText}>Cancel Request</Text>
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
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  ticketInfo: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  ticketNumber: {
    fontSize: 20,
    fontWeight: '700',
    color: '#1A1A1A',
    marginRight: 8,
  },
  priorityBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 4,
  },
  priorityText: {
    fontSize: 11,
    fontWeight: '600',
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
  typeText: {
    fontSize: 15,
    color: '#374151',
    fontWeight: '500',
  },
  dateText: {
    fontSize: 13,
    color: '#9CA3AF',
    marginTop: 4,
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
  issueText: {
    fontSize: 15,
    color: '#1A1A1A',
    lineHeight: 22,
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
  linkText: {
    color: '#0066CC',
  },
  addressContainer: {
    marginLeft: 12,
    flex: 1,
  },
  resolutionCard: {
    backgroundColor: '#F0FDF4',
    borderColor: '#86EFAC',
    borderWidth: 1,
  },
  resolutionText: {
    fontSize: 15,
    color: '#166534',
    lineHeight: 22,
  },
  completedDate: {
    fontSize: 13,
    color: '#16A34A',
    marginTop: 8,
  },
  quickActions: {
    flexDirection: 'row',
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
    flex: 1,
    alignItems: 'center',
    padding: 12,
  },
  actionText: {
    fontSize: 12,
    color: '#374151',
    marginTop: 4,
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

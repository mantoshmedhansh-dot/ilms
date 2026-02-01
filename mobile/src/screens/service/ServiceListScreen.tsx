/**
 * Service Request List Screen
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

import {serviceRequestsApi, ServiceRequest} from '../../api/serviceRequests';
import {ServiceStackParamList} from '../../navigation/MainNavigator';

type ServiceListNavigationProp = NativeStackNavigationProp<
  ServiceStackParamList,
  'ServiceList'
>;

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

export function ServiceListScreen(): React.JSX.Element {
  const navigation = useNavigation<ServiceListNavigationProp>();

  const [requests, setRequests] = useState<ServiceRequest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  const fetchRequests = useCallback(
    async (reset = false) => {
      try {
        const currentPage = reset ? 1 : page;
        const response = await serviceRequestsApi.getRequests({
          page: currentPage,
          size: 20,
          search: searchQuery || undefined,
          status: selectedStatus || undefined,
        });

        if (reset) {
          setRequests(response.items);
          setPage(2);
        } else {
          setRequests(prev => [...prev, ...response.items]);
          setPage(prev => prev + 1);
        }
        setHasMore(response.items.length === 20);
      } catch (error) {
        console.error('Failed to fetch service requests:', error);
      } finally {
        setIsLoading(false);
        setRefreshing(false);
      }
    },
    [page, searchQuery, selectedStatus],
  );

  useEffect(() => {
    setIsLoading(true);
    fetchRequests(true);
  }, [searchQuery, selectedStatus]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchRequests(true);
  }, [fetchRequests]);

  const onEndReached = () => {
    if (!isLoading && hasMore) {
      fetchRequests(false);
    }
  };

  const navigateToDetail = (requestId: string) => {
    navigation.navigate('ServiceDetail', {requestId});
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  };

  const renderStatusFilter = () => {
    const statuses = [
      {key: null, label: 'All'},
      {key: 'OPEN', label: 'Open'},
      {key: 'IN_PROGRESS', label: 'In Progress'},
      {key: 'RESOLVED', label: 'Resolved'},
      {key: 'CLOSED', label: 'Closed'},
    ];

    return (
      <View style={styles.filterContainer}>
        <FlatList
          horizontal
          showsHorizontalScrollIndicator={false}
          data={statuses}
          keyExtractor={item => item.label}
          renderItem={({item}) => (
            <TouchableOpacity
              style={[
                styles.filterChip,
                selectedStatus === item.key && styles.filterChipActive,
              ]}
              onPress={() => setSelectedStatus(item.key)}>
              <Text
                style={[
                  styles.filterChipText,
                  selectedStatus === item.key && styles.filterChipTextActive,
                ]}>
                {item.label}
              </Text>
            </TouchableOpacity>
          )}
        />
      </View>
    );
  };

  const renderRequestItem = ({item}: {item: ServiceRequest}) => {
    const statusStyle = STATUS_COLORS[item.status] || STATUS_COLORS.OPEN;
    const priorityStyle = PRIORITY_COLORS[item.priority] || PRIORITY_COLORS.MEDIUM;

    return (
      <TouchableOpacity
        style={styles.requestCard}
        onPress={() => navigateToDetail(item.id)}>
        <View style={styles.requestHeader}>
          <View style={styles.ticketInfo}>
            <Text style={styles.ticketNumber}>{item.ticket_number}</Text>
            <View style={[styles.priorityBadge, {backgroundColor: priorityStyle.bg}]}>
              <Text style={[styles.priorityText, {color: priorityStyle.text}]}>
                {item.priority}
              </Text>
            </View>
          </View>
          <View style={[styles.statusBadge, {backgroundColor: statusStyle.bg}]}>
            <Text style={[styles.statusText, {color: statusStyle.text}]}>
              {item.status.replace('_', ' ')}
            </Text>
          </View>
        </View>

        <Text style={styles.issueDescription} numberOfLines={2}>
          {item.issue_description}
        </Text>

        <View style={styles.requestDetails}>
          <View style={styles.detailRow}>
            <Icon name="account" size={14} color="#6B7280" />
            <Text style={styles.detailText}>{item.customer_name}</Text>
          </View>
          <View style={styles.detailRow}>
            <Icon name="tag" size={14} color="#6B7280" />
            <Text style={styles.detailText}>{item.type}</Text>
          </View>
        </View>

        <View style={styles.requestFooter}>
          <View style={styles.productInfo}>
            <Icon name="washing-machine" size={14} color="#6B7280" />
            <Text style={styles.productName} numberOfLines={1}>
              {item.product_name}
            </Text>
          </View>
          <Text style={styles.dateText}>{formatDate(item.created_at)}</Text>
        </View>

        {item.scheduled_date && (
          <View style={styles.scheduledRow}>
            <Icon name="calendar-clock" size={14} color="#4F46E5" />
            <Text style={styles.scheduledText}>
              Scheduled: {formatDate(item.scheduled_date)}
            </Text>
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
          placeholder="Search by ticket number or customer..."
          placeholderTextColor="#9CA3AF"
          value={searchQuery}
          onChangeText={setSearchQuery}
        />
        {searchQuery.length > 0 && (
          <TouchableOpacity onPress={() => setSearchQuery('')}>
            <Icon name="close-circle" size={20} color="#9CA3AF" />
          </TouchableOpacity>
        )}
      </View>

      {/* Status Filters */}
      {renderStatusFilter()}

      {/* Request List */}
      {isLoading && requests.length === 0 ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#0066CC" />
        </View>
      ) : requests.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Icon name="headset" size={64} color="#D1D5DB" />
          <Text style={styles.emptyText}>No service requests found</Text>
          <Text style={styles.emptySubtext}>
            {searchQuery
              ? 'Try adjusting your search'
              : 'Service requests will appear here'}
          </Text>
        </View>
      ) : (
        <FlatList
          data={requests}
          renderItem={renderRequestItem}
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

      {/* FAB for new request */}
      <TouchableOpacity style={styles.fab}>
        <Icon name="plus" size={28} color="#FFFFFF" />
      </TouchableOpacity>
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
    paddingBottom: 80,
  },
  requestCard: {
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
  requestHeader: {
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
    fontSize: 16,
    fontWeight: '600',
    color: '#1A1A1A',
    marginRight: 8,
  },
  priorityBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  priorityText: {
    fontSize: 10,
    fontWeight: '600',
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
  issueDescription: {
    fontSize: 14,
    color: '#374151',
    marginBottom: 12,
    lineHeight: 20,
  },
  requestDetails: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 12,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 16,
    marginBottom: 4,
  },
  detailText: {
    fontSize: 13,
    color: '#6B7280',
    marginLeft: 4,
  },
  requestFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: '#F3F4F6',
    paddingTop: 12,
  },
  productInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    marginRight: 12,
  },
  productName: {
    fontSize: 13,
    color: '#6B7280',
    marginLeft: 6,
    flex: 1,
  },
  dateText: {
    fontSize: 12,
    color: '#9CA3AF',
  },
  scheduledRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#F3F4F6',
  },
  scheduledText: {
    fontSize: 13,
    color: '#4F46E5',
    marginLeft: 6,
    fontWeight: '500',
  },
  footerLoader: {
    paddingVertical: 16,
  },
  fab: {
    position: 'absolute',
    right: 20,
    bottom: 20,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#0066CC',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: {width: 0, height: 4},
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 8,
  },
});

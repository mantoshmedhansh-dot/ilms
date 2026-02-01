/**
 * Main Navigator with Bottom Tabs
 */

import React from 'react';
import {createBottomTabNavigator} from '@react-navigation/bottom-tabs';
import {createNativeStackNavigator} from '@react-navigation/native-stack';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

// Screens
import {DashboardScreen} from '../screens/dashboard/DashboardScreen';
import {OrderListScreen} from '../screens/orders/OrderListScreen';
import {OrderDetailScreen} from '../screens/orders/OrderDetailScreen';
import {InventoryScreen} from '../screens/inventory/InventoryScreen';
import {StockDetailScreen} from '../screens/inventory/StockDetailScreen';
import {ServiceListScreen} from '../screens/service/ServiceListScreen';
import {ServiceDetailScreen} from '../screens/service/ServiceDetailScreen';
import {ProfileScreen} from '../screens/profile/ProfileScreen';

export type MainTabParamList = {
  DashboardTab: undefined;
  OrdersTab: undefined;
  InventoryTab: undefined;
  ServiceTab: undefined;
  ProfileTab: undefined;
};

export type OrderStackParamList = {
  OrderList: undefined;
  OrderDetail: {orderId: string};
};

export type InventoryStackParamList = {
  Inventory: undefined;
  StockDetail: {sku: string};
};

export type ServiceStackParamList = {
  ServiceList: undefined;
  ServiceDetail: {requestId: string};
};

const Tab = createBottomTabNavigator<MainTabParamList>();
const OrderStack = createNativeStackNavigator<OrderStackParamList>();
const InventoryStack = createNativeStackNavigator<InventoryStackParamList>();
const ServiceStack = createNativeStackNavigator<ServiceStackParamList>();

// Order Stack Navigator
function OrdersNavigator() {
  return (
    <OrderStack.Navigator>
      <OrderStack.Screen
        name="OrderList"
        component={OrderListScreen}
        options={{title: 'Orders'}}
      />
      <OrderStack.Screen
        name="OrderDetail"
        component={OrderDetailScreen}
        options={{title: 'Order Details'}}
      />
    </OrderStack.Navigator>
  );
}

// Inventory Stack Navigator
function InventoryNavigator() {
  return (
    <InventoryStack.Navigator>
      <InventoryStack.Screen
        name="Inventory"
        component={InventoryScreen}
        options={{title: 'Inventory'}}
      />
      <InventoryStack.Screen
        name="StockDetail"
        component={StockDetailScreen}
        options={{title: 'Stock Details'}}
      />
    </InventoryStack.Navigator>
  );
}

// Service Stack Navigator
function ServiceNavigator() {
  return (
    <ServiceStack.Navigator>
      <ServiceStack.Screen
        name="ServiceList"
        component={ServiceListScreen}
        options={{title: 'Service Requests'}}
      />
      <ServiceStack.Screen
        name="ServiceDetail"
        component={ServiceDetailScreen}
        options={{title: 'Request Details'}}
      />
    </ServiceStack.Navigator>
  );
}

export function MainNavigator(): React.JSX.Element {
  return (
    <Tab.Navigator
      screenOptions={({route}) => ({
        tabBarIcon: ({focused, color, size}) => {
          let iconName: string;

          switch (route.name) {
            case 'DashboardTab':
              iconName = focused ? 'view-dashboard' : 'view-dashboard-outline';
              break;
            case 'OrdersTab':
              iconName = focused ? 'clipboard-list' : 'clipboard-list-outline';
              break;
            case 'InventoryTab':
              iconName = focused ? 'package-variant' : 'package-variant-closed';
              break;
            case 'ServiceTab':
              iconName = focused ? 'wrench' : 'wrench-outline';
              break;
            case 'ProfileTab':
              iconName = focused ? 'account' : 'account-outline';
              break;
            default:
              iconName = 'circle';
          }

          return <Icon name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#0066CC',
        tabBarInactiveTintColor: '#666666',
        tabBarLabelStyle: {
          fontSize: 12,
          fontWeight: '500',
        },
        headerShown: false,
      })}>
      <Tab.Screen
        name="DashboardTab"
        component={DashboardScreen}
        options={{tabBarLabel: 'Dashboard', headerShown: true, title: 'Dashboard'}}
      />
      <Tab.Screen
        name="OrdersTab"
        component={OrdersNavigator}
        options={{tabBarLabel: 'Orders'}}
      />
      <Tab.Screen
        name="InventoryTab"
        component={InventoryNavigator}
        options={{tabBarLabel: 'Inventory'}}
      />
      <Tab.Screen
        name="ServiceTab"
        component={ServiceNavigator}
        options={{tabBarLabel: 'Service'}}
      />
      <Tab.Screen
        name="ProfileTab"
        component={ProfileScreen}
        options={{tabBarLabel: 'Profile', headerShown: true, title: 'Profile'}}
      />
    </Tab.Navigator>
  );
}

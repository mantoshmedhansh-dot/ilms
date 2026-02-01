'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { formatDistanceToNow, format } from 'date-fns';
import {
  Bell,
  Check,
  CheckCheck,
  ExternalLink,
  Trash2,
  Filter,
  Settings,
  Mail,
  MessageSquare,
  Smartphone,
  Moon,
  RefreshCw,
  AlertCircle,
  Info,
  AlertTriangle,
  X,
} from 'lucide-react';
import Link from 'next/link';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

import {
  notificationsApi,
  UserNotification,
  NotificationPriority,
  NotificationType,
  Announcement,
} from '@/lib/api';

const priorityColors: Record<NotificationPriority, string> = {
  LOW: 'bg-gray-100 text-gray-800',
  MEDIUM: 'bg-blue-100 text-blue-800',
  HIGH: 'bg-orange-100 text-orange-800',
  URGENT: 'bg-red-100 text-red-800',
};

const announcementTypeIcons: Record<string, typeof Info> = {
  INFO: Info,
  WARNING: AlertTriangle,
  SUCCESS: Check,
  ERROR: AlertCircle,
};

const announcementTypeColors: Record<string, string> = {
  INFO: 'bg-blue-50 border-blue-200 text-blue-800',
  WARNING: 'bg-yellow-50 border-yellow-200 text-yellow-800',
  SUCCESS: 'bg-green-50 border-green-200 text-green-800',
  ERROR: 'bg-red-50 border-red-200 text-red-800',
};

export default function NotificationsPage() {
  const [activeTab, setActiveTab] = useState('notifications');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterType, setFilterType] = useState<string>('all');
  const [announcementDialogOpen, setAnnouncementDialogOpen] = useState(false);

  const queryClient = useQueryClient();

  // Queries
  const { data: notificationsData, isLoading: notificationsLoading } = useQuery({
    queryKey: ['notifications', filterStatus, filterType],
    queryFn: () => notificationsApi.getMyNotifications({
      size: 100,
      is_read: filterStatus === 'all' ? undefined : filterStatus === 'unread' ? false : true,
    }),
  });

  const { data: statsData } = useQuery({
    queryKey: ['notification-stats'],
    queryFn: notificationsApi.getStats,
  });

  const { data: preferencesData, isLoading: preferencesLoading } = useQuery({
    queryKey: ['notification-preferences'],
    queryFn: notificationsApi.getPreferences,
  });

  const { data: announcementsData, isLoading: announcementsLoading } = useQuery({
    queryKey: ['announcements'],
    queryFn: () => notificationsApi.getAnnouncements({ active_only: false }),
  });

  const { data: typesData } = useQuery({
    queryKey: ['notification-types'],
    queryFn: notificationsApi.getTypes,
  });

  // Mutations
  const markAsReadMutation = useMutation({
    mutationFn: (ids: string[]) => notificationsApi.markAsRead(ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['notification-stats'] });
      queryClient.invalidateQueries({ queryKey: ['notifications-unread-count'] });
      toast.success('Notifications marked as read');
    },
  });

  const markAllAsReadMutation = useMutation({
    mutationFn: notificationsApi.markAllAsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['notification-stats'] });
      queryClient.invalidateQueries({ queryKey: ['notifications-unread-count'] });
      toast.success('All notifications marked as read');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: notificationsApi.deleteNotification,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['notification-stats'] });
      queryClient.invalidateQueries({ queryKey: ['notifications-unread-count'] });
      toast.success('Notification deleted');
    },
  });

  const updatePreferencesMutation = useMutation({
    mutationFn: notificationsApi.updatePreferences,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notification-preferences'] });
      toast.success('Preferences updated');
    },
    onError: () => {
      toast.error('Failed to update preferences');
    },
  });

  const dismissAnnouncementMutation = useMutation({
    mutationFn: notificationsApi.dismissAnnouncement,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['announcements'] });
      toast.success('Announcement dismissed');
    },
  });

  const createAnnouncementMutation = useMutation({
    mutationFn: notificationsApi.createAnnouncement,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['announcements'] });
      setAnnouncementDialogOpen(false);
      toast.success('Announcement created');
    },
    onError: () => {
      toast.error('Failed to create announcement');
    },
  });

  const notifications = notificationsData?.items || [];
  const stats = statsData;
  const preferences = preferencesData;
  const announcements = announcementsData?.items || [];

  const handlePreferenceChange = (key: string, value: boolean) => {
    updatePreferencesMutation.mutate({ [key]: value });
  };

  const handleCreateAnnouncement = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    createAnnouncementMutation.mutate({
      title: formData.get('title') as string,
      message: formData.get('message') as string,
      announcement_type: formData.get('announcement_type') as string,
      start_date: new Date().toISOString(),
      is_dismissible: true,
      show_on_dashboard: true,
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Notifications</h1>
          <p className="text-muted-foreground">
            Manage your notifications and preferences
          </p>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Total</CardTitle>
              <Bell className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Unread</CardTitle>
              <AlertCircle className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">{stats.unread}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">High Priority</CardTitle>
              <AlertTriangle className="h-4 w-4 text-orange-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-orange-600">
                {(stats.by_priority?.HIGH || 0) + (stats.by_priority?.URGENT || 0)}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Categories</CardTitle>
              <Filter className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{Object.keys(stats.by_type || {}).length}</div>
            </CardContent>
          </Card>
        </div>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="notifications" className="flex items-center gap-2">
            <Bell className="h-4 w-4" />
            Notifications
            {stats?.unread ? (
              <Badge variant="secondary" className="ml-1">{stats.unread}</Badge>
            ) : null}
          </TabsTrigger>
          <TabsTrigger value="announcements" className="flex items-center gap-2">
            <Info className="h-4 w-4" />
            Announcements
          </TabsTrigger>
          <TabsTrigger value="preferences" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Preferences
          </TabsTrigger>
        </TabsList>

        {/* Notifications Tab */}
        <TabsContent value="notifications" className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="unread">Unread</SelectItem>
                  <SelectItem value="read">Read</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {stats?.unread ? (
              <Button
                variant="outline"
                onClick={() => markAllAsReadMutation.mutate()}
                disabled={markAllAsReadMutation.isPending}
              >
                <CheckCheck className="mr-2 h-4 w-4" />
                Mark All Read
              </Button>
            ) : null}
          </div>

          <Card>
            <CardContent className="p-0">
              {notificationsLoading ? (
                <div className="p-6 space-y-4">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="flex items-center gap-4">
                      <Skeleton className="h-10 w-10 rounded-full" />
                      <div className="space-y-2 flex-1">
                        <Skeleton className="h-4 w-3/4" />
                        <Skeleton className="h-3 w-full" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : notifications.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                  <Bell className="h-12 w-12 mb-4 opacity-50" />
                  <p className="text-lg">No notifications</p>
                  <p className="text-sm">You&apos;re all caught up!</p>
                </div>
              ) : (
                <div className="divide-y">
                  {notifications.map((notification) => (
                    <div
                      key={notification.id}
                      className={`p-4 hover:bg-muted/50 transition-colors ${
                        !notification.is_read ? 'bg-blue-50/50' : ''
                      }`}
                    >
                      <div className="flex items-start gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            {!notification.is_read && (
                              <span className="h-2 w-2 rounded-full bg-blue-500" />
                            )}
                            <span className="font-medium">{notification.title}</span>
                            <Badge
                              variant="outline"
                              className={`text-xs ${priorityColors[notification.priority]}`}
                            >
                              {notification.priority}
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground mb-2">
                            {notification.message}
                          </p>
                          <div className="flex items-center gap-4 text-xs text-muted-foreground">
                            <span>
                              {formatDistanceToNow(new Date(notification.created_at), { addSuffix: true })}
                            </span>
                            <span className="capitalize">
                              {notification.notification_type.replace(/_/g, ' ').toLowerCase()}
                            </span>
                            {notification.action_url && (
                              <Link
                                href={notification.action_url}
                                className="inline-flex items-center text-primary hover:underline"
                              >
                                {notification.action_label || 'View'}
                                <ExternalLink className="h-3 w-3 ml-1" />
                              </Link>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          {!notification.is_read && (
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => markAsReadMutation.mutate([notification.id])}
                            >
                              <Check className="h-4 w-4" />
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-muted-foreground hover:text-destructive"
                            onClick={() => deleteMutation.mutate(notification.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Announcements Tab */}
        <TabsContent value="announcements" className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">System Announcements</h2>
            <Dialog open={announcementDialogOpen} onOpenChange={setAnnouncementDialogOpen}>
              <DialogTrigger asChild>
                <Button>Create Announcement</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create Announcement</DialogTitle>
                  <DialogDescription>
                    Create a system-wide announcement
                  </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleCreateAnnouncement}>
                  <div className="grid gap-4 py-4">
                    <div className="space-y-2">
                      <Label htmlFor="title">Title</Label>
                      <Input id="title" name="title" required />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="message">Message</Label>
                      <Input id="message" name="message" required />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="announcement_type">Type</Label>
                      <Select name="announcement_type" defaultValue="INFO">
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="INFO">Info</SelectItem>
                          <SelectItem value="WARNING">Warning</SelectItem>
                          <SelectItem value="SUCCESS">Success</SelectItem>
                          <SelectItem value="ERROR">Error</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <DialogFooter>
                    <Button type="button" variant="outline" onClick={() => setAnnouncementDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button type="submit" disabled={createAnnouncementMutation.isPending}>
                      {createAnnouncementMutation.isPending ? 'Creating...' : 'Create'}
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          </div>

          {announcementsLoading ? (
            <div className="space-y-4">
              {[...Array(3)].map((_, i) => (
                <Skeleton key={i} className="h-24" />
              ))}
            </div>
          ) : announcements.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Info className="h-12 w-12 mb-4 opacity-50" />
                <p className="text-lg">No announcements</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {announcements.map((announcement) => {
                const Icon = announcementTypeIcons[announcement.announcement_type] || Info;
                const colorClass = announcementTypeColors[announcement.announcement_type] || announcementTypeColors.INFO;
                return (
                  <Card key={announcement.id} className={`border ${colorClass}`}>
                    <CardContent className="pt-4">
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-3">
                          <Icon className="h-5 w-5 mt-0.5" />
                          <div>
                            <h3 className="font-semibold">{announcement.title}</h3>
                            <p className="text-sm mt-1">{announcement.message}</p>
                            <div className="flex items-center gap-4 mt-2 text-xs opacity-70">
                              <span>{format(new Date(announcement.start_date), 'MMM d, yyyy')}</span>
                              {announcement.is_active ? (
                                <Badge variant="outline" className="text-xs">Active</Badge>
                              ) : (
                                <Badge variant="secondary" className="text-xs">Inactive</Badge>
                              )}
                            </div>
                          </div>
                        </div>
                        {announcement.is_dismissible && !announcement.is_dismissed && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => dismissAnnouncementMutation.mutate(announcement.id)}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </TabsContent>

        {/* Preferences Tab */}
        <TabsContent value="preferences" className="space-y-4">
          {preferencesLoading ? (
            <Card>
              <CardContent className="p-6">
                <div className="space-y-6">
                  {[...Array(4)].map((_, i) => (
                    <div key={i} className="flex items-center justify-between">
                      <Skeleton className="h-4 w-48" />
                      <Skeleton className="h-6 w-12" />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ) : preferences ? (
            <div className="grid gap-6 md:grid-cols-2">
              {/* Channel Preferences */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Notification Channels</CardTitle>
                  <CardDescription>Choose how you want to receive notifications</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Bell className="h-5 w-5 text-muted-foreground" />
                      <Label htmlFor="in_app">In-App Notifications</Label>
                    </div>
                    <Switch
                      id="in_app"
                      checked={preferences.in_app_enabled}
                      onCheckedChange={(checked) => handlePreferenceChange('in_app_enabled', checked)}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Mail className="h-5 w-5 text-muted-foreground" />
                      <Label htmlFor="email">Email Notifications</Label>
                    </div>
                    <Switch
                      id="email"
                      checked={preferences.email_enabled}
                      onCheckedChange={(checked) => handlePreferenceChange('email_enabled', checked)}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <MessageSquare className="h-5 w-5 text-muted-foreground" />
                      <Label htmlFor="sms">SMS Notifications</Label>
                    </div>
                    <Switch
                      id="sms"
                      checked={preferences.sms_enabled}
                      onCheckedChange={(checked) => handlePreferenceChange('sms_enabled', checked)}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Smartphone className="h-5 w-5 text-muted-foreground" />
                      <Label htmlFor="push">Push Notifications</Label>
                    </div>
                    <Switch
                      id="push"
                      checked={preferences.push_enabled}
                      onCheckedChange={(checked) => handlePreferenceChange('push_enabled', checked)}
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Digest & Quiet Hours */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Advanced Settings</CardTitle>
                  <CardDescription>Configure digest and quiet hours</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Mail className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <Label htmlFor="digest">Email Digest</Label>
                        <p className="text-xs text-muted-foreground">Receive summary emails</p>
                      </div>
                    </div>
                    <Switch
                      id="digest"
                      checked={preferences.email_digest_enabled}
                      onCheckedChange={(checked) => handlePreferenceChange('email_digest_enabled', checked)}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Moon className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <Label htmlFor="quiet">Quiet Hours</Label>
                        <p className="text-xs text-muted-foreground">Pause notifications during set times</p>
                      </div>
                    </div>
                    <Switch
                      id="quiet"
                      checked={preferences.quiet_hours_enabled}
                      onCheckedChange={(checked) => handlePreferenceChange('quiet_hours_enabled', checked)}
                    />
                  </div>
                  {preferences.quiet_hours_enabled && (
                    <div className="grid grid-cols-2 gap-4 pt-2">
                      <div className="space-y-2">
                        <Label htmlFor="quiet_start">Start Time</Label>
                        <Input
                          id="quiet_start"
                          type="time"
                          defaultValue={preferences.quiet_hours_start || '22:00'}
                          onChange={(e) => updatePreferencesMutation.mutate({ quiet_hours_start: e.target.value })}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="quiet_end">End Time</Label>
                        <Input
                          id="quiet_end"
                          type="time"
                          defaultValue={preferences.quiet_hours_end || '08:00'}
                          onChange={(e) => updatePreferencesMutation.mutate({ quiet_hours_end: e.target.value })}
                        />
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          ) : null}
        </TabsContent>
      </Tabs>
    </div>
  );
}

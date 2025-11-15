'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import useSWR from 'swr';
import { apiClient } from '@/lib/api-client';
import { useAuthStatus } from '@/hooks/useAuthStatus';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import {
  Mail,
  Clock,
  FolderOpen,
  Send,
  RefreshCw,
  Settings,
  CheckCircle,
  XCircle,
  AlertCircle,
  X as XIcon,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { toast } from 'sonner';
import type { ActivityItem } from '@/types/dashboard';

/**
 * Dashboard Overview Page
 * Displays system status, email statistics, and recent activity
 *
 * Features:
 * - Connection status cards (Gmail, Telegram)
 * - Email processing statistics
 * - Time saved metrics
 * - Recent activity feed
 * - Auto-refresh every 30 seconds via SWR
 * - Manual refresh button
 * - System health indicator
 * - Quick actions navigation
 * - Helpful tips for new users
 */
export default function DashboardPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, user } = useAuthStatus();

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  // Redirect to onboarding if not completed
  useEffect(() => {
    if (!authLoading && isAuthenticated && user && !user.onboarding_completed) {
      router.push('/onboarding');
    }
  }, [authLoading, isAuthenticated, user, router]);

  // Fetch dashboard stats with SWR (auto-refresh every 30 seconds)
  const {
    data: statsResponse,
    error: statsError,
    isLoading: statsLoading,
    mutate: refreshStats,
  } = useSWR(
    isAuthenticated ? '/api/v1/dashboard/stats' : null,
    () => apiClient.getDashboardStats(),
    {
      refreshInterval: 30000, // 30 seconds
      revalidateOnFocus: true,
      revalidateOnReconnect: true,
    }
  );

  // Extract stats from response
  const stats = statsResponse?.data;

  // Show error toast when stats fail to load
  useEffect(() => {
    if (statsError) {
      toast.error('Failed to load dashboard stats', {
        action: {
          label: 'Retry',
          onClick: () => refreshStats(),
        },
      });
    }
  }, [statsError, refreshStats]);

  // Loading state
  if (authLoading || (isAuthenticated && statsLoading && !stats)) {
    return <DashboardSkeleton />;
  }

  // Not authenticated - show nothing (will redirect)
  if (!isAuthenticated || !user) {
    return null;
  }

  // Calculate system health
  const gmailConnected = stats?.connections.gmail.connected ?? false;
  const telegramConnected = stats?.connections.telegram.connected ?? false;
  const hasWarnings = !gmailConnected || !telegramConnected;
  const hasErrors = !gmailConnected && !telegramConnected;

  const healthStatus = hasErrors
    ? 'error'
    : hasWarnings
    ? 'warning'
    : 'operational';

  // Check if user is new (onboarding completed recently)
  // Note: created_at not available from useAuthStatus, defaulting to show tips
  const isNewUser = user.onboarding_completed ?? false;

  // Manual refresh handler
  const handleRefresh = () => {
    refreshStats();
    toast.success('Dashboard refreshed');
  };

  return (
    <div className="min-h-screen bg-background p-4 md:p-6 lg:p-8">
      <div className="mx-auto max-w-7xl space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground">
              Monitor your email processing and system status
            </p>
          </div>
          <Button onClick={handleRefresh} variant="outline" size="sm">
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>

        {/* System Health Indicator */}
        {healthStatus === 'operational' && (
          <Alert className="border-green-500 bg-green-50 dark:bg-green-950">
            <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
            <AlertTitle className="text-green-800 dark:text-green-200">
              All systems operational
            </AlertTitle>
            <AlertDescription className="text-green-700 dark:text-green-300">
              Gmail and Telegram are connected and working correctly.
            </AlertDescription>
          </Alert>
        )}
        {healthStatus === 'warning' && (
          <Alert className="border-yellow-500 bg-yellow-50 dark:bg-yellow-950">
            <AlertCircle className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
            <AlertTitle className="text-yellow-800 dark:text-yellow-200">
              Minor issues detected
            </AlertTitle>
            <AlertDescription className="text-yellow-700 dark:text-yellow-300">
              {!gmailConnected && 'Gmail is disconnected. '}
              {!telegramConnected && 'Telegram is disconnected. '}
              Please reconnect to restore full functionality.
            </AlertDescription>
          </Alert>
        )}
        {healthStatus === 'error' && (
          <Alert className="border-red-500 bg-red-50 dark:bg-red-950">
            <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
            <AlertTitle className="text-red-800 dark:text-red-200">
              Service disruption
            </AlertTitle>
            <AlertDescription className="text-red-700 dark:text-red-300">
              Both Gmail and Telegram are disconnected. Please reconnect to use Mail Agent.
            </AlertDescription>
          </Alert>
        )}

        {/* RAG Indexing Progress (if in progress) */}
        {stats?.rag_indexing_in_progress && (
          <Alert className="border-blue-500 bg-blue-50 dark:bg-blue-950">
            <Clock className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            <AlertTitle className="text-blue-800 dark:text-blue-200">
              Email history indexing in progress...
            </AlertTitle>
            <AlertDescription className="text-blue-700 dark:text-blue-300">
              {stats.rag_indexing_progress
                ? `${stats.rag_indexing_progress}% complete`
                : 'Preparing your email context for AI responses'}
            </AlertDescription>
          </Alert>
        )}

        {/* Connection Status Cards */}
        <div className="grid gap-4 md:grid-cols-2">
          {/* Gmail Connection Card */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Gmail Connection</CardTitle>
              <Mail className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  {gmailConnected ? (
                    <>
                      <div className="h-2 w-2 rounded-full bg-green-500" />
                      <span className="text-sm font-medium text-green-700 dark:text-green-400">
                        Connected
                      </span>
                    </>
                  ) : (
                    <>
                      <div className="h-2 w-2 rounded-full bg-red-500" />
                      <span className="text-sm font-medium text-red-700 dark:text-red-400">
                        Disconnected
                      </span>
                    </>
                  )}
                </div>
                {gmailConnected && stats?.connections.gmail.last_sync && (
                  <p className="text-xs text-muted-foreground">
                    Last sync: {formatDistanceToNow(new Date(stats.connections.gmail.last_sync), { addSuffix: true })}
                  </p>
                )}
                {!gmailConnected && (
                  <Button
                    onClick={() => router.push('/onboarding?step=gmail')}
                    size="sm"
                    variant="outline"
                    className="mt-2"
                  >
                    Reconnect Gmail
                  </Button>
                )}
                {stats?.connections.gmail.error && (
                  <p className="text-xs text-red-600 dark:text-red-400">
                    {stats.connections.gmail.error}
                  </p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Telegram Connection Card */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Telegram Connection</CardTitle>
              <Send className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  {telegramConnected ? (
                    <>
                      <div className="h-2 w-2 rounded-full bg-green-500" />
                      <span className="text-sm font-medium text-green-700 dark:text-green-400">
                        Connected
                      </span>
                    </>
                  ) : (
                    <>
                      <div className="h-2 w-2 rounded-full bg-red-500" />
                      <span className="text-sm font-medium text-red-700 dark:text-red-400">
                        Disconnected
                      </span>
                    </>
                  )}
                </div>
                {!telegramConnected && (
                  <Button
                    onClick={() => router.push('/onboarding?step=telegram')}
                    size="sm"
                    variant="outline"
                    className="mt-2"
                  >
                    Reconnect Telegram
                  </Button>
                )}
                {stats?.connections.telegram.error && (
                  <p className="text-xs text-red-600 dark:text-red-400">
                    {stats.connections.telegram.error}
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Email Statistics */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Processed</CardTitle>
              <Mail className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.email_stats.total_processed ?? 0}</div>
              <p className="text-xs text-muted-foreground">Emails processed today</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Pending Approval</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.email_stats.pending_approval ?? 0}</div>
              <p className="text-xs text-muted-foreground">Awaiting your decision</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Auto-Sorted</CardTitle>
              <FolderOpen className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.email_stats.auto_sorted ?? 0}</div>
              <p className="text-xs text-muted-foreground">Automatically organized</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Responses Sent</CardTitle>
              <Send className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats?.email_stats.responses_sent ?? 0}</div>
              <p className="text-xs text-muted-foreground">AI-generated replies</p>
            </CardContent>
          </Card>
        </div>

        {/* Time Saved & Recent Activity */}
        <div className="grid gap-4 md:grid-cols-2">
          {/* Time Saved Card */}
          <Card>
            <CardHeader>
              <CardTitle>Time Saved</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <p className="text-sm text-muted-foreground">Today</p>
                <p className="text-2xl font-bold">
                  {stats?.time_saved.today_minutes ?? 0} min
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total</p>
                <p className="text-2xl font-bold">
                  {stats?.time_saved.total_minutes
                    ? stats.time_saved.total_minutes >= 60
                      ? `${Math.floor(stats.time_saved.total_minutes / 60)}h ${stats.time_saved.total_minutes % 60}m`
                      : `${stats.time_saved.total_minutes} min`
                    : '0 min'}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Recent Activity Feed */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3 max-h-[280px] overflow-y-auto">
                {stats?.recent_activity && stats.recent_activity.length > 0 ? (
                  stats.recent_activity.slice(0, 10).map((activity: ActivityItem) => {
                    const icon =
                      activity.type === 'sorted' ? (
                        <FolderOpen className="h-4 w-4 text-blue-500" />
                      ) : activity.type === 'response_sent' ? (
                        <Send className="h-4 w-4 text-green-500" />
                      ) : (
                        <XIcon className="h-4 w-4 text-red-500" />
                      );

                    const subject =
                      activity.email_subject.length > 50
                        ? `${activity.email_subject.substring(0, 50)}...`
                        : activity.email_subject;

                    return (
                      <div key={activity.id} className="flex items-start gap-3 text-sm">
                        <div className="mt-0.5">{icon}</div>
                        <div className="flex-1 space-y-1">
                          <p className="font-medium leading-none">{subject}</p>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            {activity.type === 'sorted' && activity.folder_name && (
                              <span className="rounded bg-muted px-1.5 py-0.5">
                                {activity.folder_name}
                              </span>
                            )}
                            <span>
                              {formatDistanceToNow(new Date(activity.timestamp), {
                                addSuffix: true,
                              })}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <p className="text-sm text-muted-foreground text-center py-8">
                    No recent activity
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions & Helpful Tips */}
        <div className="grid gap-4 md:grid-cols-2">
          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button
                onClick={() => router.push('/settings/folders')}
                variant="outline"
                className="w-full justify-start"
              >
                <FolderOpen className="mr-2 h-4 w-4" />
                Manage Folders
              </Button>
              <Button
                onClick={() => router.push('/settings/notifications')}
                variant="outline"
                className="w-full justify-start"
              >
                <Settings className="mr-2 h-4 w-4" />
                Update Settings
              </Button>
              <Button
                variant="outline"
                className="w-full justify-start"
                disabled
                title="Coming soon in future release"
              >
                <Mail className="mr-2 h-4 w-4" />
                View Full Stats
              </Button>
            </CardContent>
          </Card>

          {/* Helpful Tips for New Users */}
          {isNewUser && (
            <Card>
              <CardHeader>
                <CardTitle>Getting Started</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="space-y-2 text-sm">
                  <p>
                    ✉️ Your first email will arrive soon! Check Telegram for notifications.
                  </p>
                  <p>
                    📁 You can customize folder categories in Settings → Folders.
                  </p>
                  <p>
                    ❓ Need help? Visit our{' '}
                    <a href="#" className="text-primary underline-offset-4 hover:underline">
                      documentation
                    </a>
                    .
                  </p>
                </div>
                <Button
                  onClick={() => {
                    if (typeof window !== 'undefined') {
                      localStorage.setItem('dashboard-tips-dismissed', 'true');
                    }
                    toast.success('Tips dismissed');
                  }}
                  variant="ghost"
                  size="sm"
                  className="w-full"
                >
                  Dismiss
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Dashboard Skeleton Loading Component
 * Displays while dashboard data is being fetched
 */
function DashboardSkeleton() {
  return (
    <div className="min-h-screen bg-background p-4 md:p-6 lg:p-8">
      <div className="mx-auto max-w-7xl space-y-6">
        {/* Header Skeleton */}
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <Skeleton className="h-8 w-[200px]" />
            <Skeleton className="h-4 w-[300px]" />
          </div>
          <Skeleton className="h-9 w-[100px]" />
        </div>

        {/* Alert Skeleton */}
        <Skeleton className="h-16 w-full" />

        {/* Connection Cards Skeleton */}
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-[120px]" />
          <Skeleton className="h-[120px]" />
        </div>

        {/* Stats Cards Skeleton */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Skeleton className="h-[120px]" />
          <Skeleton className="h-[120px]" />
          <Skeleton className="h-[120px]" />
          <Skeleton className="h-[120px]" />
        </div>

        {/* Time Saved & Activity Skeleton */}
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-[280px]" />
          <Skeleton className="h-[280px]" />
        </div>

        {/* Quick Actions Skeleton */}
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-[200px]" />
          <Skeleton className="h-[200px]" />
        </div>
      </div>
    </div>
  );
}

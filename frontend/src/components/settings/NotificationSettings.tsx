'use client';

import { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import { Bell, Clock, AlertCircle } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import type { UpdateNotificationPrefsRequest } from '@/types/settings';
import { DEFAULT_NOTIFICATION_PREFERENCES } from '@/types/settings';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

/**
 * Time format validation regex (HH:MM in 24-hour format)
 */
const TIME_REGEX = /^([01]\d|2[0-3]):([0-5]\d)$/;

/**
 * Validate overnight quiet hours range
 * Allows ranges like 22:00 - 08:00 (crosses midnight)
 * Only invalid if start === end
 */
function isValidQuietHoursRange(start: string, end: string): boolean {
  if (start === end) {
    return false; // Same time not allowed
  }
  return true; // Both overnight (22:00-08:00) and same-day (08:00-22:00) ranges are valid
}

/**
 * Form validation schema
 */
const notificationFormSchema = z.object({
  batch_enabled: z.boolean(),
  batch_time: z.string().regex(TIME_REGEX, 'Invalid time format (use HH:MM)'),
  quiet_hours_enabled: z.boolean(),
  quiet_hours_start: z.string().regex(TIME_REGEX, 'Invalid time format (use HH:MM)'),
  quiet_hours_end: z.string().regex(TIME_REGEX, 'Invalid time format (use HH:MM)'),
  priority_immediate: z.boolean(),
  min_confidence_threshold: z.number().min(0).max(1),
}).refine(
  (data) => isValidQuietHoursRange(data.quiet_hours_start, data.quiet_hours_end),
  {
    message: 'Quiet hours end time must be different from start time',
    path: ['quiet_hours_end'],
  }
);

type NotificationFormData = z.infer<typeof notificationFormSchema>;

/**
 * NotificationSettings Component
 * Manages user notification preferences including batch timing, quiet hours, and priority alerts
 */
export default function NotificationSettings() {
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [testingNotification, setTestingNotification] = useState(false);
  const [showDefaultBanner, setShowDefaultBanner] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    control,
    reset,
    formState: { errors },
  } = useForm<NotificationFormData>({
    resolver: zodResolver(notificationFormSchema),
    defaultValues: DEFAULT_NOTIFICATION_PREFERENCES,
  });

  // Watch toggle states to show/hide dependent fields
  const batchEnabled = watch('batch_enabled');
  const quietHoursEnabled = watch('quiet_hours_enabled');
  const priorityImmediate = watch('priority_immediate');
  const minConfidenceThreshold = watch('min_confidence_threshold');

  /**
   * Load notification preferences on component mount
   * Run only on mount - loadPreferences should not re-run on state changes
   */
  useEffect(() => {
    loadPreferences();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /**
   * Fetch preferences from backend
   */
  async function loadPreferences() {
    try {
      setLoading(true);
      const response = await apiClient.getNotificationPrefs();

      if (response.data) {
        // Populate form with existing preferences using reset for atomic update
        reset({
          batch_enabled: response.data.batch_enabled,
          batch_time: response.data.batch_time,
          quiet_hours_enabled: response.data.quiet_hours_enabled,
          quiet_hours_start: response.data.quiet_hours_start,
          quiet_hours_end: response.data.quiet_hours_end,
          priority_immediate: response.data.priority_immediate,
          min_confidence_threshold: response.data.min_confidence_threshold,
        });
      } else {
        // No saved preferences - defaults already loaded, show banner
        setShowDefaultBanner(true);
      }
    } catch (error) {
      console.error('Failed to load notification preferences:', error);
      toast.error('Failed to load notification preferences');
      // Use defaults on error
      setShowDefaultBanner(true);
    } finally {
      setLoading(false);
    }
  }

  /**
   * Save preferences to backend
   */
  async function onSubmit(data: NotificationFormData) {
    try {
      setSubmitting(true);

      const updatePayload: UpdateNotificationPrefsRequest = {
        batch_enabled: data.batch_enabled,
        batch_time: data.batch_time,
        quiet_hours_enabled: data.quiet_hours_enabled,
        quiet_hours_start: data.quiet_hours_start,
        quiet_hours_end: data.quiet_hours_end,
        priority_immediate: data.priority_immediate,
        min_confidence_threshold: data.min_confidence_threshold,
      };

      const response = await apiClient.updateNotificationPrefs(updatePayload);

      if (response.data) {
        setShowDefaultBanner(false); // Hide default banner after first save
        toast.success('Notification preferences updated!');
      } else {
        throw new Error('No data received from server');
      }
    } catch (error) {
      console.error('Failed to save notification preferences:', error);
      toast.error('Failed to save preferences. Please try again.');
    } finally {
      setSubmitting(false);
    }
  }

  /**
   * Send test notification to user's Telegram
   */
  async function handleTestNotification() {
    try {
      setTestingNotification(true);

      const response = await apiClient.testNotification();

      if (response.data.success) {
        const timestamp = new Date().toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
        });
        toast.success(`Test notification sent! Check your Telegram. (Sent at ${timestamp})`);
      } else {
        throw new Error(response.data.message || 'Test notification failed');
      }
    } catch (error: unknown) {
      console.error('Failed to send test notification:', error);

      // Extract error message
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';

      toast.error(`Failed to send test notification: ${errorMessage}`);
    } finally {
      setTestingNotification(false);
    }
  }

  /**
   * Loading skeleton
   */
  if (loading) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-96 mt-2" />
          </CardHeader>
          <CardContent className="space-y-6">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Default Settings Banner */}
      {showDefaultBanner && (
        <div className="rounded-lg border border-blue-500/50 bg-blue-500/10 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-blue-500 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-blue-500">Default settings applied</p>
              <p className="text-sm text-muted-foreground mt-1">
                Adjust notification preferences as needed and click Save to apply your changes.
              </p>
            </div>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Batch Notifications Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Batch Notifications
            </CardTitle>
            <CardDescription>
              Group email notifications and send once per day
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Batch Toggle */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="batch_enabled" className="text-base">
                  Enable batch notifications
                </Label>
                <p className="text-sm text-muted-foreground">
                  Group email notifications and send once per day
                </p>
              </div>
              <Controller
                name="batch_enabled"
                control={control}
                render={({ field }) => (
                  <Switch
                    id="batch_enabled"
                    checked={field.value}
                    onCheckedChange={field.onChange}
                  />
                )}
              />
            </div>

            {/* Batch Time Selector (shown only when batch enabled) */}
            {batchEnabled && (
              <div className="space-y-2">
                <Label htmlFor="batch_time">Batch notification time</Label>
                <Controller
                  name="batch_time"
                  control={control}
                  render={({ field }) => (
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger id="batch_time">
                        <SelectValue placeholder="Select time" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="08:00">Morning (08:00)</SelectItem>
                        <SelectItem value="18:00">End of day (18:00)</SelectItem>
                        <SelectItem value="12:00">Noon (12:00)</SelectItem>
                        <SelectItem value="20:00">Evening (20:00)</SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                />
                {errors.batch_time && (
                  <p className="text-sm text-destructive">{errors.batch_time.message}</p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Priority Notifications Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5" />
              Priority Notifications
            </CardTitle>
            <CardDescription>
              Receive high-priority emails immediately, bypassing batch
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Priority Toggle */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="priority_immediate" className="text-base">
                  Immediate priority notifications
                </Label>
                <p className="text-sm text-muted-foreground">
                  Send high-priority emails immediately, bypassing batch
                </p>
              </div>
              <Controller
                name="priority_immediate"
                control={control}
                render={({ field }) => (
                  <Switch
                    id="priority_immediate"
                    checked={field.value}
                    onCheckedChange={field.onChange}
                  />
                )}
              />
            </div>

            {/* Warning when priority disabled */}
            {!priorityImmediate && (
              <div className="rounded-lg border border-yellow-500/50 bg-yellow-500/10 p-3">
                <p className="text-sm text-yellow-500">
                  ⚠️ All emails will wait for batch notification time
                </p>
              </div>
            )}

            {/* Confidence Threshold Slider (shown only when priority enabled) */}
            {priorityImmediate && (
              <div className="space-y-2">
                <Label htmlFor="min_confidence_threshold">
                  Minimum confidence for priority detection
                </Label>
                <div className="flex items-center gap-4">
                  <Input
                    id="min_confidence_threshold"
                    type="range"
                    min="0.5"
                    max="1.0"
                    step="0.05"
                    {...register('min_confidence_threshold', { valueAsNumber: true })}
                    className="flex-1"
                  />
                  <span className="text-sm font-medium w-12 text-right">
                    {Math.round(minConfidenceThreshold * 100)}%
                  </span>
                </div>
                <p className="text-sm text-muted-foreground">
                  Higher values = fewer interruptions, but may miss urgent emails
                </p>
                {errors.min_confidence_threshold && (
                  <p className="text-sm text-destructive">{errors.min_confidence_threshold.message}</p>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Quiet Hours Section */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Quiet Hours
            </CardTitle>
            <CardDescription>
              Suppress all notifications during specified hours
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Quiet Hours Toggle */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="quiet_hours_enabled" className="text-base">
                  Enable quiet hours
                </Label>
                <p className="text-sm text-muted-foreground">
                  Suppress all notifications during specified hours
                </p>
              </div>
              <Controller
                name="quiet_hours_enabled"
                control={control}
                render={({ field }) => (
                  <Switch
                    id="quiet_hours_enabled"
                    checked={field.value}
                    onCheckedChange={field.onChange}
                  />
                )}
              />
            </div>

            {/* Quiet Hours Time Pickers (shown only when quiet hours enabled) */}
            {quietHoursEnabled && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="quiet_hours_start">Quiet hours start</Label>
                  <Input
                    id="quiet_hours_start"
                    type="time"
                    {...register('quiet_hours_start')}
                    className="w-full"
                  />
                  {errors.quiet_hours_start && (
                    <p className="text-sm text-destructive">{errors.quiet_hours_start.message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="quiet_hours_end">Quiet hours end</Label>
                  <Input
                    id="quiet_hours_end"
                    type="time"
                    {...register('quiet_hours_end')}
                    className="w-full"
                  />
                  {errors.quiet_hours_end && (
                    <p className="text-sm text-destructive">{errors.quiet_hours_end.message}</p>
                  )}
                </div>
              </div>
            )}

            {/* Overnight range helper text */}
            {quietHoursEnabled && (
              <p className="text-sm text-muted-foreground">
                💡 Overnight ranges are supported (e.g., 22:00 - 08:00)
              </p>
            )}
          </CardContent>
        </Card>

        {/* Action Buttons */}
        <div className="flex items-center justify-between">
          <Button
            type="button"
            variant="secondary"
            onClick={handleTestNotification}
            disabled={testingNotification || submitting}
          >
            {testingNotification ? 'Sending...' : 'Send Test Notification'}
          </Button>

          <Button type="submit" disabled={submitting || testingNotification}>
            {submitting ? 'Saving...' : 'Save Preferences'}
          </Button>
        </div>
      </form>
    </div>
  );
}

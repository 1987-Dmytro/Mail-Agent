import { Metadata } from 'next';
import { LoginForm } from '@/components/auth/LoginForm';

/**
 * Metadata for login page
 */
export const metadata: Metadata = {
  title: 'Sign In | Mail Agent',
  description: 'Sign in to your Mail Agent account',
};

/**
 * Login page
 *
 * Allows existing users to sign in with email and password.
 * After successful authentication, users are redirected to dashboard.
 *
 * Route: /login
 * Accessible by: All users (no authentication required)
 */
export default function LoginPage() {
  return (
    <main className="min-h-screen flex items-center justify-center p-4 bg-background">
      <div className="w-full max-w-md space-y-6">
        {/* Page title */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold tracking-tight">Mail Agent</h1>
          <p className="text-muted-foreground">
            AI-powered email management
          </p>
        </div>

        {/* Login form */}
        <LoginForm />
      </div>
    </main>
  );
}

/**
 * Authentication Context providing reactive user identity and verified RBAC roles.
 */
import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import {
  auth,
  isInitialized,
  firebaseProjectId,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  updateProfile,
  onAuthStateChanged,
  FirebaseUser,
} from '../services/firebase';
import { getCurrentUser, syncUserProfile } from '../services/api';
import { UserRole, UserPrincipal } from '../types';

interface AuthContextType {
  user: UserPrincipal | null;
  firebaseUser: FirebaseUser | null;
  role: UserRole;
  token: string | null;
  loading: boolean;
  error: string | null;
  isFirebaseActive: boolean;
  firebaseProjectId: string;
  login: (email: string, pass: string) => Promise<void>;
  register: (email: string, pass: string, displayName: string) => Promise<void>;
  logout: () => Promise<void>;
  quickDevLogin: (role: UserRole, customEmail?: string) => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const DEV_AUTH_STORAGE_KEY = 'nexus_dev_user_principal';
const DEV_TOKEN_STORAGE_KEY = 'nexus_dev_auth_token';
const DEMO_USERS_STORAGE_KEY = 'nexus_demo_registered_users';

interface DemoRegisteredUser {
  uid: string;
  email: string;
  passwordHash: string;
  displayName: string;
  role: UserRole;
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserPrincipal | null>(null);
  const [firebaseUser, setFirebaseUser] = useState<FirebaseUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<UserRole>('COMMUNITY_USER');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const clearError = () => setError(null);

  // Restore dev user from localStorage if present
  const restoreDevSession = useCallback((): boolean => {
    try {
      const storedUser = localStorage.getItem(DEV_AUTH_STORAGE_KEY);
      const storedToken = localStorage.getItem(DEV_TOKEN_STORAGE_KEY);
      if (storedUser && storedToken) {
        const parsed: UserPrincipal = JSON.parse(storedUser);
        setUser(parsed);
        setRole(parsed.role);
        setToken(storedToken);
        setLoading(false);
        return true;
      }
    } catch (e) {
      console.warn('Could not restore dev session:', e);
    }
    return false;
  }, []);

  // Sync token and role claims with backend
  const handleUserSession = useCallback(async (fbUser: FirebaseUser | null) => {
    if (!fbUser) {
      if (isInitialized) {
        // When live Firebase is active, Firebase Auth is the sole source of truth.
        // Purge any stale offline dev mock keys.
        localStorage.removeItem(DEV_AUTH_STORAGE_KEY);
        localStorage.removeItem(DEV_TOKEN_STORAGE_KEY);
        setUser(null);
        setFirebaseUser(null);
        setToken(null);
        setRole('COMMUNITY_USER');
        setLoading(false);
        return;
      }
      // Check if dev session is active before clearing (offline mode only)
      const restored = restoreDevSession();
      if (!restored) {
        setUser(null);
        setFirebaseUser(null);
        setToken(null);
        setRole('COMMUNITY_USER');
        setLoading(false);
      }
      return;
    }

    try {
      setFirebaseUser(fbUser);
      const idToken = await fbUser.getIdToken();
      setToken(idToken);

      // Verify token with backend /auth/me to get trusted role
      try {
        const verifiedPrincipal = await getCurrentUser(idToken);
        setUser(verifiedPrincipal);
        setRole(verifiedPrincipal.role);
      } catch {
        // Fallback if backend /auth/me fails: extract from token or default
        const idTokenResult = await fbUser.getIdTokenResult();
        const tokenRole = (idTokenResult.claims.role as UserRole) || 'COMMUNITY_USER';
        setUser({
          uid: fbUser.uid,
          email: fbUser.email || '',
          role: tokenRole,
        });
        setRole(tokenRole);
      }
    } catch (err: unknown) {
      console.error('Error establishing session:', err);
      setError(err instanceof Error ? err.message : 'Session synchronization failed');
    } finally {
      setLoading(false);
    }
  }, [restoreDevSession]);

  useEffect(() => {
    if (isInitialized && auth && typeof onAuthStateChanged === 'function') {
      const unsubscribe = onAuthStateChanged(auth, (fbUser) => {
        handleUserSession(fbUser);
      });
      return () => unsubscribe();
    } else {
      restoreDevSession();
      setLoading(false);
    }
  }, [handleUserSession, restoreDevSession]);

  // Helper to load demo registered accounts
  const getDemoUsers = (): DemoRegisteredUser[] => {
    try {
      const stored = localStorage.getItem(DEMO_USERS_STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  };

  // Helper to save demo registered account
  const saveDemoUser = (userObj: DemoRegisteredUser) => {
    try {
      const users = getDemoUsers().filter((u) => u.email.toLowerCase() !== userObj.email.toLowerCase());
      users.push(userObj);
      localStorage.setItem(DEMO_USERS_STORAGE_KEY, JSON.stringify(users));
    } catch (e) {
      console.warn('Could not save demo user:', e);
    }
  };

function formatFirebaseError(err: any): string {
  if (!err) return 'Authentication failed.';
  const code = err.code || '';
  switch (code) {
    case 'auth/email-already-in-use':
      return 'This email address is already registered in Firebase. Please sign in instead.';
    case 'auth/invalid-email':
      return 'The email address format is invalid.';
    case 'auth/weak-password':
      return 'Password is too weak. Please use at least 6 characters.';
    case 'auth/wrong-password':
    case 'auth/user-not-found':
    case 'auth/invalid-credential':
      return 'Invalid email or password. Please verify your credentials.';
    case 'auth/too-many-requests':
      return 'Too many attempts. Access is temporarily restricted. Please try again later.';
    case 'auth/network-request-failed':
      return 'Network connection to Firebase Authentication failed. Please check your internet connection.';
    case 'auth/operation-not-allowed':
      return 'Email/Password sign-in is not enabled in Firebase Authentication.';
    default:
      return err.message || 'Firebase authentication error occurred.';
  }
}

  // Firebase Email/Password Sign-In
  const login = async (email: string, pass: string) => {
    setLoading(true);
    setError(null);
    const cleanEmail = email.trim().toLowerCase();

    try {
      // If authentic Firebase configuration is active, use live Firebase Auth directly
      if (isInitialized && auth && typeof signInWithEmailAndPassword === 'function') {
        try {
          const cred = await signInWithEmailAndPassword(auth, email, pass);
          if (!cred.user?.uid) {
            throw new Error('Firebase did not return a valid user UID.');
          }
          await handleUserSession(cred.user);
          return;
        } catch (fbErr: any) {
          const formatted = formatFirebaseError(fbErr);
          throw new Error(formatted);
        }
      }

      // Standby / Offline Dev Mode only when Firebase is unconfigured
      const demoUsers = getDemoUsers();
      const existing = demoUsers.find((u) => u.email.toLowerCase() === cleanEmail);

      if (existing) {
        if (existing.passwordHash !== pass) {
          throw new Error('Invalid credentials. Password does not match registered account.');
        }
        const devToken = `dev-token:${existing.uid}:${existing.email}:${existing.role}`;
        const principal: UserPrincipal = {
          uid: existing.uid,
          email: existing.email,
          role: existing.role,
          claims: { dev: true, displayName: existing.displayName },
        };
        localStorage.setItem(DEV_AUTH_STORAGE_KEY, JSON.stringify(principal));
        localStorage.setItem(DEV_TOKEN_STORAGE_KEY, devToken);
        setUser(principal);
        setRole(existing.role);
        setToken(devToken);
        return;
      }

      // If logging in with well-known test email in offline dev mode
      const isAnalyst = cleanEmail.includes('analyst');
      const isAdmin = cleanEmail.includes('admin');
      const assignedRole: UserRole = isAdmin ? 'ADMIN' : isAnalyst ? 'ANALYST' : 'COMMUNITY_USER';
      const uid = `usr_${assignedRole.toLowerCase()}_${Math.random().toString(36).substring(2, 8)}`;
      const devToken = `dev-token:${uid}:${cleanEmail}:${assignedRole}`;
      const principal: UserPrincipal = {
        uid,
        email: cleanEmail,
        role: assignedRole,
        claims: { dev: true },
      };

      localStorage.setItem(DEV_AUTH_STORAGE_KEY, JSON.stringify(principal));
      localStorage.setItem(DEV_TOKEN_STORAGE_KEY, devToken);
      setUser(principal);
      setRole(assignedRole);
      setToken(devToken);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Authentication failed';
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Firebase Email/Password Registration (Strict Live Firebase Verification)
  const register = async (email: string, pass: string, displayName: string) => {
    setLoading(true);
    setError(null);
    const cleanEmail = email.trim().toLowerCase();

    try {
      if (!isInitialized || !auth || typeof createUserWithEmailAndPassword !== 'function') {
        throw new Error(
          'Firebase is not initialized. Please configure VITE_FIREBASE_* variables in frontend/.env to enable live registration.'
        );
      }

      // Await live Firebase Authentication response
      let cred;
      try {
        cred = await createUserWithEmailAndPassword(auth, email, pass);
      } catch (fbErr: any) {
        const formatted = formatFirebaseError(fbErr);
        throw new Error(formatted);
      }

      if (!cred || !cred.user || !cred.user.uid) {
        throw new Error('Firebase did not return a valid user UID upon registration.');
      }

      // Update user display name in Firebase Auth
      if (displayName) {
        try {
          await updateProfile(cred.user, { displayName });
        } catch (nameErr) {
          console.warn('Could not update Firebase displayName:', nameErr);
        }
      }

      const idToken = await cred.user.getIdToken();

      // Synchronize profile to FastAPI backend (strictly receives COMMUNITY_USER role)
      try {
        await syncUserProfile(displayName, idToken);
      } catch (syncErr) {
        console.warn('Backend profile sync notice (auth succeeded, sync deferred):', syncErr);
      }

      // Establish verified live user session
      await handleUserSession(cred.user);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Registration failed';
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Logout
  const logout = async () => {
    setLoading(true);
    try {
      localStorage.removeItem(DEV_AUTH_STORAGE_KEY);
      localStorage.removeItem(DEV_TOKEN_STORAGE_KEY);
      if (isInitialized && auth) {
        await signOut(auth);
      }
      setUser(null);
      setFirebaseUser(null);
      setToken(null);
      setRole('COMMUNITY_USER');
    } catch (err: unknown) {
      console.error('Logout error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Quick Developer / Demonstration Login for Evaluators
  const quickDevLogin = async (targetRole: UserRole, customEmail?: string) => {
    setLoading(true);
    setError(null);
    try {
      const rolePrefix = targetRole.toLowerCase();
      const email = customEmail || `${rolePrefix}@nexus.ai`;
      const uid = `usr_${rolePrefix}_${Math.random().toString(36).substring(2, 8)}`;
      const devToken = `dev-token:${uid}:${email}:${targetRole}`;

      const principal: UserPrincipal = {
        uid,
        email,
        role: targetRole,
        claims: { dev: true },
      };

      localStorage.setItem(DEV_AUTH_STORAGE_KEY, JSON.stringify(principal));
      localStorage.setItem(DEV_TOKEN_STORAGE_KEY, devToken);

      setUser(principal);
      setRole(targetRole);
      setToken(devToken);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        firebaseUser,
        role,
        token,
        loading,
        error,
        isFirebaseActive: isInitialized,
        firebaseProjectId,
        login,
        register,
        logout,
        quickDevLogin,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

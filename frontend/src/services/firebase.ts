/**
 * Frontend Firebase Client Initialization & Authentication Module
 * NEXUS AI — Community Intelligence & Risk Decision Platform
 */
import { initializeApp, getApps, getApp, FirebaseApp } from 'firebase/app';
import {
  getAuth,
  Auth,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut,
  updateProfile,
  onAuthStateChanged,
  setPersistence,
  browserLocalPersistence,
  User as FirebaseUser,
  UserCredential,
} from 'firebase/auth';
import {
  getFirestore,
  Firestore,
  collection,
  doc,
  getDoc,
  getDocs,
  setDoc,
  addDoc,
  updateDoc,
  deleteDoc,
  query,
  where,
  orderBy,
  limit,
  startAfter,
  onSnapshot,
  serverTimestamp,
  Timestamp,
} from 'firebase/firestore';
import {
  getStorage,
  FirebaseStorage,
  ref,
  uploadBytes,
  getDownloadURL,
} from 'firebase/storage';

// Read configuration strictly from Vite environment variables (No fabricated credentials)
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || '',
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || '',
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || '',
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET || '',
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID || '',
  appId: import.meta.env.VITE_FIREBASE_APP_ID || '',
};

// Check if valid project configuration has been provided
const isConfigured = Boolean(
  firebaseConfig.apiKey &&
  firebaseConfig.apiKey.trim() !== '' &&
  firebaseConfig.projectId &&
  firebaseConfig.projectId.trim() !== '' &&
  firebaseConfig.appId &&
  firebaseConfig.appId.trim() !== ''
);

const isStorageConfigured = Boolean(
  isConfigured &&
  firebaseConfig.storageBucket &&
  firebaseConfig.storageBucket.trim() !== ''
);

let app: FirebaseApp;
let auth: Auth;
let db: Firestore;
let storage: FirebaseStorage;
let isInitialized = false;
const firebaseProjectId = firebaseConfig.projectId || '';

if (isConfigured) {
  try {
    app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApp();
    auth = getAuth(app);
    db = getFirestore(app);
    storage = getStorage(app);
    setPersistence(auth, browserLocalPersistence).catch((err) => {
      console.warn('Could not set persistence to browserLocalPersistence:', err);
    });
    isInitialized = true;
    console.info('Firebase initialized successfully for project:', firebaseConfig.projectId);
  } catch (error) {
    console.error('Firebase initialization error:', error);
    app = {} as FirebaseApp;
    auth = {} as Auth;
    db = {} as Firestore;
    storage = {} as FirebaseStorage;
    isInitialized = false;
  }
} else {
  // Unconfigured standby mode - components remain safe until credentials are input
  app = {} as FirebaseApp;
  auth = {} as Auth;
  db = {} as Firestore;
  storage = {} as FirebaseStorage;
  isInitialized = false;
}

// Authentication Exports
export {
  app,
  auth,
  isInitialized,
  firebaseProjectId,
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut,
  updateProfile,
  onAuthStateChanged,
  setPersistence,
  browserLocalPersistence,
};
export type { FirebaseUser, UserCredential };

// Firestore Database Exports
export {
  db,
  collection,
  doc,
  getDoc,
  getDocs,
  setDoc,
  addDoc,
  updateDoc,
  deleteDoc,
  query,
  where,
  orderBy,
  limit,
  startAfter,
  onSnapshot,
  serverTimestamp,
  Timestamp,
};

// Cloud Storage Exports
export {
  storage,
  isStorageConfigured,
  ref,
  uploadBytes,
  getDownloadURL,
};

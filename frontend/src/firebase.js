import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider } from 'firebase/auth';

const app = initializeApp({
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
});

export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();

const FIREBASE_ERRORS = {
  'auth/invalid-credential': 'Incorrect email or password',
  'auth/email-already-in-use': 'Email is already registered',
  'auth/weak-password': 'Password must be at least 6 characters',
  'auth/invalid-email': 'Invalid email address',
  'auth/too-many-requests': 'Too many attempts, try again later',
  'auth/popup-closed-by-user': 'Sign-in popup was closed',
};

export const firebaseErrorMessage = (err) => FIREBASE_ERRORS[err.code] || err.message;

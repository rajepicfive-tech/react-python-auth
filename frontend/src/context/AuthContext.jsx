import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import {
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
  updateProfile,
} from 'firebase/auth';
import { api } from '../api/client.js';
import { auth, firebaseErrorMessage, googleProvider } from '../firebase.js';

const AuthContext = createContext(null);

// Re-throw Firebase errors with a readable message for the forms.
const withMessage = (fn) => async (...args) => {
  try {
    return await fn(...args);
  } catch (err) {
    throw new Error(firebaseErrorMessage(err));
  }
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadProfile = useCallback(async () => {
    try {
      setUser(await api('/api/auth/me'));
    } catch {
      setUser(null);
    }
  }, []);

  // Firebase restores the session on reload; load the backend profile whenever it changes.
  useEffect(
    () =>
      onAuthStateChanged(auth, async (fbUser) => {
        if (fbUser) await loadProfile();
        else setUser(null);
        setLoading(false);
      }),
    [loadProfile]
  );

  const login = useCallback(
    withMessage(async (email, password) => {
      await signInWithEmailAndPassword(auth, email, password);
      await loadProfile();
    }),
    [loadProfile]
  );

  const loginWithGoogle = useCallback(
    withMessage(async () => {
      await signInWithPopup(auth, googleProvider);
      await loadProfile();
    }),
    [loadProfile]
  );

  const register = useCallback(
    withMessage(async (fullName, email, password) => {
      const { user: fbUser } = await createUserWithEmailAndPassword(auth, email, password);
      await updateProfile(fbUser, { displayName: fullName.trim() });
      await fbUser.getIdToken(true); // refresh so the JWT carries the new `name` claim
      await loadProfile();
    }),
    [loadProfile]
  );

  const logout = useCallback(() => signOut(auth), []);

  return (
    <AuthContext.Provider value={{ user, loading, login, loginWithGoogle, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);

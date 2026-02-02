import React, { createContext, useContext, useState, useCallback } from 'react';

const LoadingContext = createContext();

export const useLoading = () => {
  const context = useContext(LoadingContext);
  if (!context) {
    throw new Error('useLoading must be used within a LoadingProvider');
  }
  return context;
};

export const LoadingProvider = ({ children }) => {
  const [loadingStates, setLoadingStates] = useState({});
  const [globalLoading, setGlobalLoading] = useState(false);

  const startLoading = useCallback((key = 'global') => {
    if (key === 'global') {
      setGlobalLoading(true);
    } else {
      setLoadingStates(prev => ({ ...prev, [key]: true }));
    }
  }, []);

  const stopLoading = useCallback((key = 'global') => {
    if (key === 'global') {
      setGlobalLoading(false);
    } else {
      setLoadingStates(prev => ({ ...prev, [key]: false }));
    }
  }, []);

  const isLoading = useCallback((key = 'global') => {
    if (key === 'global') {
      return globalLoading;
    }
    return loadingStates[key] || false;
  }, [loadingStates, globalLoading]);

  const withLoading = useCallback(async (key, asyncFn) => {
    try {
      startLoading(key);
      const result = await asyncFn();
      return result;
    } finally {
      stopLoading(key);
    }
  }, [startLoading, stopLoading]);

  const value = {
    startLoading,
    stopLoading,
    isLoading,
    withLoading,
    globalLoading
  };

  return (
    <LoadingContext.Provider value={value}>
      {children}
    </LoadingContext.Provider>
  );
};

export default LoadingProvider;

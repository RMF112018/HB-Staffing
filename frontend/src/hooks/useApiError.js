import { useState, useCallback } from 'react';

export const useApiError = () => {
  const [error, setError] = useState(null);
  const [isRetrying, setIsRetrying] = useState(false);

  const handleApiError = useCallback((err, operation = null) => {
    console.error('API Error:', err);

    let errorMessage = 'An unexpected error occurred';
    let errorType = 'unknown';

    if (err.response) {
      // Server responded with error status
      const { status, data } = err.response;

      switch (status) {
        case 400:
          errorType = 'validation';
          errorMessage = data?.error?.message || 'Invalid request data';
          break;
        case 401:
          errorType = 'unauthorized';
          errorMessage = 'You are not authorized to perform this action';
          break;
        case 403:
          errorType = 'forbidden';
          errorMessage = 'Access denied';
          break;
        case 404:
          errorType = 'not_found';
          errorMessage = data?.error?.message || 'Resource not found';
          break;
        case 409:
          errorType = 'conflict';
          errorMessage = data?.error?.message || 'Operation conflicts with current state';
          break;
        case 422:
          errorType = 'business_logic';
          errorMessage = data?.error?.message || 'Business logic validation failed';
          break;
        case 500:
          errorType = 'server_error';
          errorMessage = 'Server error. Please try again later.';
          break;
        default:
          errorType = 'server_error';
          errorMessage = `Server error (${status})`;
      }
    } else if (err.request) {
      // Network error
      errorType = 'network';
      errorMessage = 'Network error. Please check your connection and try again.';
    } else {
      // Other error
      errorType = 'unknown';
      errorMessage = err.message || 'An unexpected error occurred';
    }

    const apiError = {
      type: errorType,
      message: errorMessage,
      operation,
      timestamp: new Date().toISOString(),
      details: err.response?.data?.error?.details || null
    };

    setError(apiError);
    return apiError;
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const retryOperation = useCallback(async (operation, maxRetries = 3, delay = 1000) => {
    setIsRetrying(true);
    setError(null);

    let lastError;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        const result = await operation();
        setIsRetrying(false);
        return result;
      } catch (err) {
        lastError = err;

        // Don't retry on client errors (4xx)
        if (err.response && err.response.status >= 400 && err.response.status < 500) {
          break;
        }

        // Wait before retrying (exponential backoff)
        if (attempt < maxRetries) {
          await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, attempt - 1)));
        }
      }
    }

    setIsRetrying(false);
    throw handleApiError(lastError, 'retry_operation');
  }, [handleApiError]);

  return {
    error,
    isRetrying,
    handleApiError,
    clearError,
    retryOperation
  };
};

export default useApiError;

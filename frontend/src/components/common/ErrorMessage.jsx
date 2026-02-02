import React from 'react';
import './ErrorMessage.css';

const ErrorMessage = ({
  message,
  title = 'Error',
  onRetry,
  retryText = 'Try Again',
  className = ''
}) => {
  return (
    <div className={`error-message ${className}`}>
      <div className="error-message-content">
        <h3 className="error-message-title">{title}</h3>
        <p className="error-message-text">{message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="error-message-retry"
          >
            {retryText}
          </button>
        )}
      </div>
    </div>
  );
};

export default ErrorMessage;

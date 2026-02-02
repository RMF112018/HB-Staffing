import React from 'react';
import './ErrorMessage.css';

const ErrorMessage = ({
  message,
  title,
  type = 'error',
  onRetry,
  onDismiss,
  retryText = 'Try Again',
  dismissText = 'Dismiss',
  action,
  className = '',
  showIcon = true
}) => {
  // Auto-generate title based on type if not provided
  const getDefaultTitle = () => {
    switch (type) {
      case 'validation':
        return 'Invalid Input';
      case 'network':
        return 'Connection Error';
      case 'unauthorized':
        return 'Access Denied';
      case 'not_found':
        return 'Not Found';
      case 'conflict':
        return 'Conflict';
      case 'server_error':
        return 'Server Error';
      case 'business_logic':
        return 'Action Not Allowed';
      default:
        return 'Error';
    }
  };

  const finalTitle = title || getDefaultTitle();

  return (
    <div className={`error-message error-message-${type} ${className}`}>
      <div className="error-message-content">
        {showIcon && (
          <div className="error-message-icon">
            <ErrorIcon type={type} />
          </div>
        )}
        <div className="error-message-body">
          <h3 className="error-message-title">{finalTitle}</h3>
          <p className="error-message-text">{message}</p>
          <div className="error-message-actions">
            {action}
            {onRetry && (
              <button
                onClick={onRetry}
                className="error-message-retry"
              >
                {retryText}
              </button>
            )}
            {onDismiss && (
              <button
                onClick={onDismiss}
                className="error-message-dismiss"
              >
                {dismissText}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const ErrorIcon = ({ type }) => {
  const getIconSymbol = () => {
    switch (type) {
      case 'validation':
        return '⚠️';
      case 'network':
        return '📡';
      case 'unauthorized':
        return '🔒';
      case 'not_found':
        return '🔍';
      case 'conflict':
        return '⚡';
      case 'server_error':
        return '🔧';
      case 'business_logic':
        return '🚫';
      default:
        return '❌';
    }
  };

  return <span className="error-icon-symbol">{getIconSymbol()}</span>;
};

export default ErrorMessage;

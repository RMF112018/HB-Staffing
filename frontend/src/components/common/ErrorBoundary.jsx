import React from 'react';
import ErrorMessage from './ErrorMessage';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    // Log the error to console and potentially to a logging service
    console.error('ErrorBoundary caught an error:', error, errorInfo);

    this.setState({
      error: error,
      errorInfo: errorInfo
    });

    // Here you could also send the error to a logging service
    // logErrorToService(error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      // Render fallback UI
      const { fallback: Fallback, children } = this.props;

      if (Fallback) {
        return <Fallback error={this.state.error} retry={this.handleRetry} />;
      }

      return (
        <div className="error-boundary-container">
          <ErrorMessage
            title="Something went wrong"
            message="An unexpected error occurred. Please refresh the page or try again."
            action={
              <button
                onClick={this.handleRetry}
                className="retry-button"
              >
                Try Again
              </button>
            }
          />
          {process.env.NODE_ENV === 'development' && (
            <details className="error-details">
              <summary>Error Details (Development)</summary>
              <pre className="error-stack">
                {this.state.error && this.state.error.toString()}
                <br />
                {this.state.errorInfo.componentStack}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;

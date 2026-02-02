import React from 'react';
import { format } from 'date-fns';
import Input from './Input';
import './DatePicker.css';

const DatePicker = ({
  label,
  name,
  value,
  onChange,
  error,
  required = false,
  disabled = false,
  min,
  max,
  className = '',
  ...props
}) => {
  const handleChange = (fieldName, inputValue) => {
    // Ensure date is in YYYY-MM-DD format
    if (inputValue) {
      try {
        const date = new Date(inputValue);
        const formattedDate = format(date, 'yyyy-MM-dd');
        onChange(fieldName, formattedDate);
      } catch (error) {
        onChange(fieldName, inputValue);
      }
    } else {
      onChange(fieldName, inputValue);
    }
  };

  // Format the display value
  const displayValue = value ? format(new Date(value), 'yyyy-MM-dd') : '';

  return (
    <Input
      label={label}
      name={name}
      type="date"
      value={displayValue}
      onChange={handleChange}
      error={error}
      required={required}
      disabled={disabled}
      min={min}
      max={max}
      className={`date-picker ${className}`}
      {...props}
    />
  );
};

export default DatePicker;

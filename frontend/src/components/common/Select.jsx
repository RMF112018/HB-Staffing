import React from 'react';
import './Select.css';

const Select = ({
  label,
  name,
  value,
  onChange,
  options = [],
  error,
  required = false,
  placeholder = 'Select an option',
  disabled = false,
  className = '',
  ...props
}) => {
  const handleChange = (e) => {
    const { value: selectedValue } = e.target;
    onChange(name, selectedValue);
  };

  return (
    <div className={`select-group ${className}`}>
      {label && (
        <label htmlFor={name} className={`select-label ${required ? 'required' : ''}`}>
          {label}
        </label>
      )}
      <select
        id={name}
        name={name}
        value={value || ''}
        onChange={handleChange}
        disabled={disabled}
        className={`select-field ${error ? 'select-error' : ''}`}
        {...props}
      >
        <option value="" disabled>
          {placeholder}
        </option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {error && <span className="select-error-message">{error}</span>}
    </div>
  );
};

export default Select;

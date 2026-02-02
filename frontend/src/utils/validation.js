import { isValid, isAfter, isBefore, parseISO } from 'date-fns';

/**
 * Form validation utilities
 */

// Validate required field
export const required = (value, fieldName) => {
  if (!value || (typeof value === 'string' && value.trim() === '')) {
    return `${fieldName} is required`;
  }
  return null;
};

// Validate email format
export const email = (value) => {
  if (!value) return null;
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(value)) {
    return 'Please enter a valid email address';
  }
  return null;
};

// Validate number range
export const numberRange = (value, min, max, fieldName) => {
  if (value === null || value === undefined || value === '') return null;

  const num = Number(value);
  if (isNaN(num)) {
    return `${fieldName} must be a valid number`;
  }

  if (min !== undefined && num < min) {
    return `${fieldName} must be at least ${min}`;
  }

  if (max !== undefined && num > max) {
    return `${fieldName} must be no more than ${max}`;
  }

  return null;
};

// Validate positive number
export const positiveNumber = (value, fieldName) => {
  return numberRange(value, 0.01, undefined, fieldName);
};

// Validate date format
export const dateFormat = (value, fieldName) => {
  if (!value) return null;

  try {
    const date = parseISO(value);
    if (!isValid(date)) {
      return `${fieldName} must be a valid date`;
    }
  } catch (error) {
    return `${fieldName} must be a valid date`;
  }

  return null;
};

// Validate date range
export const dateRange = (startDate, endDate, startFieldName = 'Start date', endFieldName = 'End date') => {
  if (!startDate || !endDate) return null;

  try {
    const start = parseISO(startDate);
    const end = parseISO(endDate);

    if (!isValid(start) || !isValid(end)) return null;

    if (!isBefore(start, end) && start.getTime() !== end.getTime()) {
      return `${endFieldName} must be after ${startFieldName}`;
    }
  } catch (error) {
    return 'Invalid date format';
  }

  return null;
};

// Validate skills array (optional - empty array is valid)
export const skillsArray = (skills) => {
  if (!skills) return null;

  if (!Array.isArray(skills)) {
    return 'Skills must be a list';
  }

  // Empty array is valid - skills are optional
  if (skills.length === 0) {
    return null;
  }

  // Check for duplicates
  const uniqueSkills = new Set(skills.map(skill => skill.toLowerCase().trim()));
  if (uniqueSkills.size !== skills.length) {
    return 'Skills must be unique';
  }

  // Check skill length
  for (const skill of skills) {
    if (skill.trim().length < 2) {
      return 'Each skill must be at least 2 characters long';
    }
    if (skill.trim().length > 50) {
      return 'Each skill must be no more than 50 characters long';
    }
  }

  return null;
};

// Validate project status
export const projectStatus = (status) => {
  const validStatuses = ['planning', 'active', 'completed', 'cancelled', 'on-hold'];
  if (!validStatuses.includes(status)) {
    return 'Invalid project status';
  }
  return null;
};

// Validate staff role (legacy - for text input)
export const staffRole = (role) => {
  if (!role || role.trim().length < 2) {
    return 'Role must be at least 2 characters long';
  }
  if (role.length > 100) {
    return 'Role must be no more than 100 characters long';
  }
  return null;
};

// Validate staff role_id (for dropdown selection)
export const staffRoleId = (value, fieldName = 'Role') => {
  if (!value || value === '' || value === 0) {
    return `${fieldName} is required`;
  }
  const numValue = Number(value);
  if (isNaN(numValue) || numValue <= 0) {
    return `Please select a valid ${fieldName.toLowerCase()}`;
  }
  return null;
};

// Validate assignment hours per week
export const hoursPerWeek = (hours) => {
  return numberRange(hours, 0.5, 80, 'Hours per week');
};

// Generic form validation function
export const validateForm = (formData, validationRules) => {
  const errors = {};

  for (const [fieldName, rules] of Object.entries(validationRules)) {
    const value = formData[fieldName];
    const fieldErrors = [];

    for (const rule of rules) {
      const error = rule(value, fieldName);
      if (error) {
        fieldErrors.push(error);
        break; // Stop at first error for this field
      }
    }

    if (fieldErrors.length > 0) {
      errors[fieldName] = fieldErrors[0];
    }
  }

  return errors;
};

// Validation rules for each form
export const staffValidationRules = {
  name: [required],
  role_id: [staffRoleId],
  internal_hourly_cost: [required, positiveNumber],
  availability_start: [dateFormat],
  availability_end: [dateFormat],
  skills: [skillsArray]
};

export const projectValidationRules = {
  name: [required],
  status: [required, projectStatus],
  start_date: [dateFormat],
  end_date: [dateFormat],
  budget: [numberRange.bind(null, undefined, 0, undefined)]
};

export const assignmentValidationRules = {
  staff_id: [required],
  project_id: [required],
  start_date: [required, dateFormat],
  end_date: [required, dateFormat],
  hours_per_week: [required, hoursPerWeek]
};

// Optional positive number validation (for fields that can be null/empty)
export const optionalPositiveNumber = (value, fieldName) => {
  if (value === null || value === undefined || value === '') return null;
  return positiveNumber(value, fieldName);
};

export const roleValidationRules = {
  name: [required],
  hourly_cost: [required, positiveNumber],
  default_billable_rate: [optionalPositiveNumber]
};

// Cross-field validation
export const validateStaffForm = (formData) => {
  const errors = validateForm(formData, staffValidationRules);

  // Cross-field validation for availability dates
  if (formData.availability_start && formData.availability_end) {
    const dateRangeError = dateRange(
      formData.availability_start,
      formData.availability_end,
      'Availability start date',
      'Availability end date'
    );
    if (dateRangeError) {
      errors.availability_end = dateRangeError;
    }
  }

  return errors;
};

export const validateProjectForm = (formData) => {
  const errors = validateForm(formData, projectValidationRules);

  // Cross-field validation for project dates
  if (formData.start_date && formData.end_date) {
    const dateRangeError = dateRange(
      formData.start_date,
      formData.end_date,
      'Project start date',
      'Project end date'
    );
    if (dateRangeError) {
      errors.end_date = dateRangeError;
    }
  }

  return errors;
};

export const validateAssignmentForm = (formData) => {
  const errors = validateForm(formData, assignmentValidationRules);

  // Cross-field validation for assignment dates
  if (formData.start_date && formData.end_date) {
    const dateRangeError = dateRange(
      formData.start_date,
      formData.end_date,
      'Assignment start date',
      'Assignment end date'
    );
    if (dateRangeError) {
      errors.end_date = dateRangeError;
    }
  }

  return errors;
};

export const validateRoleForm = (formData) => {
  const errors = validateForm(formData, roleValidationRules);

  // Additional business logic: default_billable_rate should typically be higher than hourly_cost
  if (formData.hourly_cost && formData.default_billable_rate) {
    const cost = Number(formData.hourly_cost);
    const rate = Number(formData.default_billable_rate);
    if (!isNaN(cost) && !isNaN(rate) && rate < cost) {
      errors.default_billable_rate = 'Warning: Default billable rate is lower than internal cost';
    }
  }

  return errors;
};

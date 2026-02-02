/**
 * @jest-environment jsdom
 */

import {
  validateRequired,
  validateEmail,
  validateNumber,
  validateDate,
  validateDateRange
} from './validation';

describe('Validation Utilities', () => {
  describe('validateRequired', () => {
    test('passes with non-empty string', () => {
      expect(() => validateRequired('test', 'field')).not.toThrow();
    });

    test('passes with number', () => {
      expect(() => validateRequired(42, 'field')).not.toThrow();
    });

    test('fails with empty string', () => {
      expect(() => validateRequired('', 'field')).toThrow('field is required');
    });

    test('fails with whitespace only string', () => {
      expect(() => validateRequired('   ', 'field')).toThrow('field is required');
    });

    test('fails with null', () => {
      expect(() => validateRequired(null, 'field')).toThrow('field is required');
    });

    test('fails with undefined', () => {
      expect(() => validateRequired(undefined, 'field')).toThrow('field is required');
    });
  });

  describe('validateEmail', () => {
    test('passes with valid email', () => {
      expect(() => validateEmail('test@example.com', 'email')).not.toThrow();
    });

    test('passes with valid email with subdomain', () => {
      expect(() => validateEmail('user@sub.domain.com', 'email')).not.toThrow();
    });

    test('fails with invalid email', () => {
      expect(() => validateEmail('invalid-email', 'email')).toThrow('email must be a valid email address');
    });

    test('fails with email without domain', () => {
      expect(() => validateEmail('user@', 'email')).toThrow('email must be a valid email address');
    });

    test('fails with empty string', () => {
      expect(() => validateEmail('', 'email')).toThrow('email must be a valid email address');
    });
  });

  describe('validateNumber', () => {
    test('passes with positive number', () => {
      expect(() => validateNumber(42, 'age')).not.toThrow();
    });

    test('passes with zero', () => {
      expect(() => validateNumber(0, 'count')).not.toThrow();
    });

    test('passes with negative number when allowed', () => {
      expect(() => validateNumber(-5, 'temperature', { allowNegative: true })).not.toThrow();
    });

    test('fails with negative number by default', () => {
      expect(() => validateNumber(-5, 'count')).toThrow('count must be a positive number');
    });

    test('passes with valid range', () => {
      expect(() => validateNumber(25, 'age', { min: 18, max: 65 })).not.toThrow();
    });

    test('fails with number below minimum', () => {
      expect(() => validateNumber(16, 'age', { min: 18 })).toThrow('age must be at least 18');
    });

    test('fails with number above maximum', () => {
      expect(() => validateNumber(70, 'age', { max: 65 })).toThrow('age must be at most 65');
    });

    test('fails with non-numeric string', () => {
      expect(() => validateNumber('not-a-number', 'field')).toThrow('field must be a valid number');
    });

    test('fails with NaN', () => {
      expect(() => validateNumber(NaN, 'field')).toThrow('field must be a valid number');
    });
  });

  describe('validateDate', () => {
    test('passes with valid date string', () => {
      expect(() => validateDate('2024-01-15', 'start_date')).not.toThrow();
    });

    test('passes with valid date object', () => {
      expect(() => validateDate(new Date('2024-01-15'), 'start_date')).not.toThrow();
    });

    test('fails with invalid date string', () => {
      expect(() => validateDate('invalid-date', 'start_date')).toThrow('start_date must be a valid date');
    });

    test('fails with invalid date format', () => {
      expect(() => validateDate('15/01/2024', 'start_date')).toThrow('start_date must be a valid date');
    });

    test('fails with empty string', () => {
      expect(() => validateDate('', 'start_date')).toThrow('start_date must be a valid date');
    });

    test('passes with future date when required', () => {
      const futureDate = new Date();
      futureDate.setFullYear(futureDate.getFullYear() + 1);
      expect(() => validateDate(futureDate.toISOString().split('T')[0], 'future_date', { future: true })).not.toThrow();
    });

    test('fails with past date when future required', () => {
      expect(() => validateDate('2020-01-01', 'future_date', { future: true })).toThrow('future_date must be a future date');
    });
  });

  describe('validateDateRange', () => {
    test('passes with valid date range', () => {
      expect(() => validateDateRange('2024-01-01', '2024-01-31', 'start_date', 'end_date')).not.toThrow();
    });

    test('fails when end date is before start date', () => {
      expect(() => validateDateRange('2024-01-31', '2024-01-01', 'start_date', 'end_date')).toThrow('end_date must be after start_date');
    });

    test('fails when dates are the same', () => {
      expect(() => validateDateRange('2024-01-01', '2024-01-01', 'start_date', 'end_date')).toThrow('end_date must be after start_date');
    });

    test('passes with valid Date objects', () => {
      const startDate = new Date('2024-01-01');
      const endDate = new Date('2024-01-31');
      expect(() => validateDateRange(startDate, endDate, 'start_date', 'end_date')).not.toThrow();
    });

    test('handles null/undefined dates gracefully', () => {
      expect(() => validateDateRange(null, '2024-01-01', 'start_date', 'end_date')).not.toThrow();
      expect(() => validateDateRange('2024-01-01', null, 'start_date', 'end_date')).not.toThrow();
    });
  });

  describe('Integration tests', () => {
    test('complete form validation scenario', () => {
      // Simulate validating a complete form
      const formData = {
        name: 'John Doe',
        email: 'john@example.com',
        age: 30,
        startDate: '2024-01-01',
        endDate: '2024-12-31'
      };

      // All validations should pass
      expect(() => {
        validateRequired(formData.name, 'name');
        validateEmail(formData.email, 'email');
        validateNumber(formData.age, 'age', { min: 18, max: 65 });
        validateDate(formData.startDate, 'start_date');
        validateDate(formData.endDate, 'end_date');
        validateDateRange(formData.startDate, formData.endDate, 'start_date', 'end_date');
      }).not.toThrow();
    });

    test('form validation with errors', () => {
      const invalidFormData = {
        name: '',
        email: 'invalid-email',
        age: 15,
        startDate: '2024-12-31',
        endDate: '2024-01-01'
      };

      const errors = [];

      // Collect validation errors
      try { validateRequired(invalidFormData.name, 'name'); }
      catch (e) { errors.push(e.message); }

      try { validateEmail(invalidFormData.email, 'email'); }
      catch (e) { errors.push(e.message); }

      try { validateNumber(invalidFormData.age, 'age', { min: 18 }); }
      catch (e) { errors.push(e.message); }

      try { validateDateRange(invalidFormData.startDate, invalidFormData.endDate, 'start_date', 'end_date'); }
      catch (e) { errors.push(e.message); }

      expect(errors.length).toBeGreaterThan(0);
      expect(errors).toContain('name is required');
      expect(errors).toContain('email must be a valid email address');
      expect(errors).toContain('age must be at least 18');
      expect(errors).toContain('end_date must be after start_date');
    });
  });
});

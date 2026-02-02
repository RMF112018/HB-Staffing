module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true,
    node: true
  },
  extends: [
    'eslint:recommended',
    'plugin:react/recommended',
    'plugin:react/jsx-runtime',
    'plugin:react-hooks/recommended'
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module',
    ecmaFeatures: {
      jsx: true
    }
  },
  plugins: ['react', 'react-hooks'],
  settings: {
    react: {
      version: 'detect'
    }
  },
  rules: {
    // React rules
    'react/prop-types': 'off', // We're not using PropTypes
    'react/react-in-jsx-scope': 'off', // Not needed with React 17+
    'react/jsx-uses-react': 'off',
    'react/jsx-uses-vars': 'error',
    
    // React Hooks rules
    'react-hooks/rules-of-hooks': 'error',
    'react-hooks/exhaustive-deps': 'warn',
    
    // General rules
    'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
    'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    'no-debugger': process.env.NODE_ENV === 'production' ? 'error' : 'off',
    'prefer-const': 'warn',
    'no-var': 'error',
    'eqeqeq': ['error', 'always', { null: 'ignore' }],
    
    // Code style (less strict - leave formatting to Prettier)
    'semi': ['error', 'always'],
    'quotes': ['warn', 'single', { avoidEscape: true }],
    'comma-dangle': ['warn', 'never'],
    'no-trailing-spaces': 'warn',
    'no-multiple-empty-lines': ['warn', { max: 2 }]
  },
  ignorePatterns: ['dist/', 'node_modules/', '*.min.js']
};


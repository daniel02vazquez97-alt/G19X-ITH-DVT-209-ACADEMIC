import js from '@eslint/js';
import { defineConfig, globalIgnores } from 'eslint/config';
import reactHooks from 'eslint-plugin-react-hooks';
import tseslint from 'typescript-eslint';

export default defineConfig([
  globalIgnores(['dist/', 'coverage/', 'src/api/schema.gen.ts']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
    ],
    rules: {
      // DT-070 point 3: the session lives only in memory.
      'no-restricted-globals': [
        'error',
        { name: 'localStorage', message: 'La sesión vive solo en memoria (DT-070).' },
        { name: 'sessionStorage', message: 'La sesión vive solo en memoria (DT-070).' },
      ],
      'no-restricted-properties': [
        'error',
        { object: 'window', property: 'localStorage', message: 'La sesión vive solo en memoria.' },
        {
          object: 'window',
          property: 'sessionStorage',
          message: 'La sesión vive solo en memoria.',
        },
      ],
    },
  },
  {
    // Tests inspect browser storage to prove the session never uses it.
    files: ['**/*.test.{ts,tsx}'],
    rules: { 'no-restricted-globals': 'off' },
  },
]);

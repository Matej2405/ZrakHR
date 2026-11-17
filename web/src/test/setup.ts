import '@testing-library/jest-dom/vitest'

import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach } from 'vitest'

import { mockSystemColorScheme } from './matchMedia'

beforeEach(() => {
  mockSystemColorScheme('light')
})

afterEach(() => {
  cleanup()
  localStorage.clear()
  delete document.documentElement.dataset.theme
})

import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { mockSystemColorScheme } from '../test/matchMedia'
import { ThemeToggle } from './ThemeToggle'

describe('ThemeToggle', () => {
  it('uključuje tamnu temu i pamti izbor', async () => {
    const user = userEvent.setup()
    render(<ThemeToggle />)
    const toggle = screen.getByRole('button', { name: 'Tamna tema' })
    expect(toggle).toHaveAttribute('aria-pressed', 'false')

    await user.click(toggle)

    expect(document.documentElement.dataset.theme).toBe('dark')
    expect(localStorage.getItem('zrakhr-theme')).toBe('dark')
    expect(toggle).toHaveAttribute('aria-pressed', 'true')
  })

  it('bez spremljenog izbora prati temu sustava', () => {
    mockSystemColorScheme('dark')
    render(<ThemeToggle />)

    expect(screen.getByRole('button', { name: 'Tamna tema' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })

  it('spremljeni izbor ima prednost pred temom sustava', async () => {
    mockSystemColorScheme('dark')
    const user = userEvent.setup()
    render(<ThemeToggle />)

    await user.click(screen.getByRole('button', { name: 'Tamna tema' }))

    expect(document.documentElement.dataset.theme).toBe('light')
    expect(screen.getByRole('button', { name: 'Tamna tema' })).toHaveAttribute(
      'aria-pressed',
      'false',
    )
  })
})

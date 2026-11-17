import '@fontsource-variable/archivo/wdth.css'
import './styles/tokens.css'
import './styles/base.css'

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router/dom'

import { router } from './router'

const container = document.getElementById('root')
if (!container) {
  throw new Error('index.html nema element #root u koji se montira aplikacija')
}

createRoot(container).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)

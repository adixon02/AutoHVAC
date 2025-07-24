import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'AutoHVAC - Professional HVAC Load Calculations',
  description: 'Generate professional HVAC load calculations and system recommendations in minutes',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  )
}
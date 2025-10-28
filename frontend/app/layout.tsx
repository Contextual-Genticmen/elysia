import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Elysia',
  description: 'Your AI Platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-background h-screen w-screen overflow-hidden font-text antialiased flex">
        {children}
      </body>
    </html>
  )
}


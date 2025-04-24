// app/api/auth/login/route.ts
import { NextResponse } from 'next/server'

export async function POST(request: Request) {
  try {
    const body = await request.json()
    const { token } = body

    // Call your backend API
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_BACKEND_API_URL}/auth/login`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token }),
      }
    )

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.detail || 'Login failed')
    }

    return NextResponse.json(data)
  } catch (error: unknown) {
    if (error instanceof Error) {
      return NextResponse.json(
        { detail: error.message || 'Internal server error' },
        { status: 500 }
      )
    }
    throw new Error('Internal server error')
  }
}
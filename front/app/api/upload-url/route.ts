import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  try {
    const backendUrl = process.env.BACKEND_URL;
    const frontendApiKey = process.env.FRONTEND_API_KEY;

    if (!backendUrl || !frontendApiKey) {
      return NextResponse.json(
        { message: 'Server configuration error: Missing backend URL or API key' },
        { status: 500 }
      );
    }

    const body = await req.json();
    const { filename, content_type } = body;

    if (!filename) {
      return NextResponse.json(
        { message: 'Filename is required' },
        { status: 400 }
      );
    }

    // Railway 백엔드에 Pre-signed URL 요청
    const response = await fetch(`${backendUrl}/voice/generate-upload-url`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': frontendApiKey,
      },
      body: JSON.stringify({
        filename,
        content_type: content_type || 'audio/mpeg',
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json(
        { message: `Backend error: ${errorText}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error: any) {
    console.error('API Route error:', error);
    return NextResponse.json(
      { message: 'Internal server error', error: error.message },
      { status: 500 }
    );
  }
}

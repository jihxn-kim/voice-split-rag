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
    const { s3_key, language_code } = body;

    if (!s3_key) {
      return NextResponse.json(
        { message: 'S3 key is required' },
        { status: 400 }
      );
    }

    // Railway 백엔드에 S3 파일 처리 요청
    const response = await fetch(`${backendUrl}/voice/process-s3-file`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': frontendApiKey,
      },
      body: JSON.stringify({
        s3_key,
        language_code: language_code || 'ko',
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

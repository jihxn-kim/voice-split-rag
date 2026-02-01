import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    // 서버 사이드에서만 실행 (API 키 안전)
    const apiKey = process.env.FRONTEND_API_KEY;
    const backendUrl = process.env.BACKEND_URL;

    if (!apiKey) {
      return NextResponse.json(
        { error: 'FRONTEND_API_KEY not configured' },
        { status: 500 }
      );
    }

    if (!backendUrl) {
      return NextResponse.json(
        { error: 'BACKEND_URL not configured' },
        { status: 500 }
      );
    }

    // 클라이언트로부터 받은 FormData 그대로 전달
    const formData = await request.formData();

    // Railway 백엔드로 요청 (API 키 포함)
    const response = await fetch(`${backendUrl}/voice/speaker-diarization-v2`, {
      method: 'POST',
      headers: {
        'X-API-Key': apiKey, // 프론트엔드-백엔드 간 인증
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.text();
      return NextResponse.json(
        { error: error || 'Backend request failed' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error('API Route error:', error);
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
      { status: 500 }
    );
  }
}

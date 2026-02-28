import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: '음성 화자 구분 - Voice Split RAG',
  description: '음성 파일을 업로드하여 화자를 구분하고 분석합니다',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko">
      <body>
        <div className="app-shell">
          <div className="app-content">{children}</div>
        </div>
      </body>
    </html>
  )
}

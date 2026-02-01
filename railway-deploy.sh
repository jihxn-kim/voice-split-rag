#!/bin/bash
# Railway CLI 배포 스크립트

echo "Railway CLI 설치 중..."
npm install -g @railway/cli

echo "Railway 로그인..."
railway login

echo "프로젝트 초기화..."
cd back
railway init

echo "환경 변수를 수동으로 설정하세요:"
echo "railway variables set VSR_URL=https://your-vercel-app.vercel.app"
echo "railway variables set GOOGLE_APPLICATION_CREDENTIALS_JSON='...'"

echo "배포 시작..."
railway up

echo "완료!"

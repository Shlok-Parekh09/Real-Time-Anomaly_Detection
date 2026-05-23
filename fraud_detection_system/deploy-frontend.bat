@echo off
echo ========================================
echo Deploying Frontend to Vercel
echo ========================================
echo.

cd frontend

echo IMPORTANT: Make sure you have deployed the backend first!
echo.
set /p BACKEND_URL="Enter your backend URL (e.g., https://your-backend.vercel.app): "

echo.
echo Creating .env.production file...
echo VITE_API_URL=%BACKEND_URL%> .env.production
echo VITE_USE_PUTER_AI=true>> .env.production

echo.
echo [1/2] Logging in to Vercel...
npx vercel login

echo.
echo [2/2] Deploying frontend...
npx vercel --prod

echo.
echo ========================================
echo Frontend Deployed!
echo ========================================
echo.
echo Your fraud detection system is now live!
echo.
pause

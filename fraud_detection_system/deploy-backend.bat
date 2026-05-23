@echo off
echo ========================================
echo Deploying Backend to Vercel
echo ========================================
echo.

cd backend

echo [1/2] Logging in to Vercel...
npx vercel login

echo.
echo [2/2] Deploying backend...
npx vercel --prod

echo.
echo ========================================
echo Backend Deployed!
echo ========================================
echo.
echo Copy the backend URL and use it in frontend deployment.
echo.
pause

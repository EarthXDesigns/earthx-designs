@echo off
title EarthX Designs Web Server
echo ========================================================
echo EarthX Designs - Solar Design & Engineering CMS Website
echo ========================================================
echo.
echo Starting local development server...
echo.
echo - Public Website:   http://127.0.0.1:5000/
echo - Admin Dashboard:  http://127.0.0.1:5000/admin
echo.
echo Default Admin Credentials:
echo - Email:    admin@earthxdesigns.com
echo - Password: EarthX@123
echo.
echo Press Ctrl+C to terminate the server.
echo.
echo ========================================================
python app.py
pause

$backend = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "app.main:app", "--port", "8000", "--host", "0.0.0.0" -WorkingDirectory "$PWD\backend" -PassThru
$frontend = Start-Process -FilePath "cmd" -ArgumentList "/c", "npx vite preview --port 4173 --host 0.0.0.0" -WorkingDirectory "$PWD\frontend" -PassThru

Write-Host "Waiting 5 seconds for backend (PID $($backend.Id)) and frontend (PID $($frontend.Id)) to initialize..."
Start-Sleep -Seconds 5

try {
    node scripts\verify_live_map_and_telemetry.mjs
}
finally {
    Write-Host "Terminating background verification servers..."
    Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
    Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue
}

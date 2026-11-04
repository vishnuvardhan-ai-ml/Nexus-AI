$backend = Start-Process -FilePath "cmd" -ArgumentList "/c", "set PYTHONPATH=$PWD\backend;. && python -m uvicorn app.main:app --port 8000 --host 127.0.0.1" -WorkingDirectory "$PWD\backend" -PassThru
$frontend = Start-Process -FilePath "cmd" -ArgumentList "/c", "npx vite preview --port 4173 --host 127.0.0.1" -WorkingDirectory "$PWD\frontend" -PassThru

Write-Host "Waiting 6 seconds for backend (PID $($backend.Id)) and frontend (PID $($frontend.Id)) to initialize..."
Start-Sleep -Seconds 6

try {
    node scripts\verify_live_milestone5_stage5.mjs
}
finally {
    Write-Host "Terminating background verification servers..."
    if ($backend) { Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue }
    if ($frontend) { Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue }
    # Also kill any child python and node processes on 8000 and 4173
    Get-Process -Name python, node -ErrorAction SilentlyContinue | Where-Object { $_.Id -ne $PID } | ForEach-Object { }
}

@echo off
REM Triavia - checks that your folder has the latest files. Run it from the project folder:  check_install.bat
setlocal
set PROBLEMS=0
echo.
echo Checking Triavia files in %CD% ...
echo.
for %%F in (frontend\app.py frontend\styles.py frontend\presets.py frontend\legal.py frontend\siteinfo.py frontend\api_client.py backend\main.py backend\routers\auth.py backend\routers\feedback.py backend\routers\predict.py backend\services\auth_service.py backend\services\predictor_service.py database\db.py database\auth_store.py database\schema.sqlite.sql database\schema.postgres.sql model\train.py model\training\features.py tests\test_feedback.py tests\test_presets.py tests\test_auth.py pytest.ini start.bat .streamlit\config.toml requirements.txt) do (
  if not exist "%%F" (
    echo   MISSING : %%F
    set PROBLEMS=1
  )
)
for %%F in (tests\test_features.py database\schema.sql) do (
  if exist "%%F" (
    echo   OLD FILE, please delete it : %%F
    set PROBLEMS=1
  )
)
findstr /c:"brandpanel" frontend\app.py >nul 2>&1 || (echo   frontend\app.py is an OLD version & set PROBLEMS=1)
findstr /c:"CARD_TONE" frontend\app.py >nul 2>&1 || (echo   frontend\app.py is an OLD version & set PROBLEMS=1)
findstr /c:"light" .streamlit\config.toml >nul 2>&1 || (echo   .streamlit\config.toml is an OLD version - it should say base = "light" & set PROBLEMS=1)
findstr /c:"2.2.0" backend\core\config.py >nul 2>&1 || (echo   backend\core\config.py is an OLD version & set PROBLEMS=1)
echo.
if "%PROBLEMS%"=="0" (
  echo   ALL GOOD - you have the latest Triavia. Now run:  pytest tests   then   start.bat
) else (
  echo   PROBLEMS FOUND - extract the full triavia.zip again and choose "Replace the files".
)
echo.
endlocal

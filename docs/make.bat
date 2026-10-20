@ECHO OFF
REM Adapted from WsprryPi-Docs; MIT notice in reference/credits.md.
setlocal
pushd "%~dp0"
if "%SPHINXBUILD%" == "" set SPHINXBUILD=.venv\Scripts\python.exe -m sphinx
if "%SPHINXOPTS%" == "" set SPHINXOPTS=-n -W --keep-going
set TARGET=%1
if "%TARGET%" == "" set TARGET=help
%SPHINXBUILD% -M %TARGET% . _build %SPHINXOPTS%
set RESULT=%ERRORLEVEL%
popd
exit /b %RESULT%

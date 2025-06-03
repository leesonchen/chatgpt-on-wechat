rem if "%1"=="hide" goto CmdBegin
rem start mshta vbscript:createobject("wscript.shell").run("""%~0"" hide",0)(window.close)&&exit
:CmdBegin
set http_proxy=
set https_proxy=
d:\anaconda3\envs\botany\python app.py
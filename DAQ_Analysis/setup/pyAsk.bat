@echo off
.\MSGBOX.EXE "Python 3.4 or greater must be installed to perform setup.\n\nDo you want to install it ?" "MessageBox Test" YESNOCANCEL
if errorlevel 7 goto NO
if errorlevel 6 goto YES
if errorlevel 2 goto CANCEL
goto fin

:no
echo You don't want to continue.
goto no+

:yes
echo You want to continue.
goto yes+

:cancel
echo You don't want to go further.
goto fin

:ok
echo ok
goto fin

:no+
.\MSGBOX.EXE "DAQ Setup will perform.It may take several minutes, be patient."
goto fin

:yes+
.\MSGBOX.EXE "Python Setup will perform from site"
start iexplore.exe "https://www.python.org/downloads/"
.\MSGBOX.EXE "Press ok once python installed, DAQ Setup will perform.It may take several minutes, be patient."
goto fin

:fin

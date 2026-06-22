
' Instagram Analyzer — 콘솔 창 없이 실행
Set objFSO   = CreateObject("Scripting.FileSystemObject")
Set objShell = CreateObject("WScript.Shell")

scriptDir  = objFSO.GetParentFolderName(WScript.ScriptFullName)
launcherPy = scriptDir & "\instagram_analyzer\launcher.py"

' pythonw.exe = 콘솔 창 없는 Python 실행기
objShell.Run "pythonw """ & launcherPy & """", 0, False

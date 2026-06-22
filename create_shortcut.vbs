
' Create desktop shortcut for Instagram Analyzer
Set objFSO   = CreateObject("Scripting.FileSystemObject")
Set objShell = CreateObject("WScript.Shell")

scriptDir   = objFSO.GetParentFolderName(WScript.ScriptFullName)
startVbs    = scriptDir & "\start.vbs"
iconFile    = scriptDir & "\instagram_analyzer\icon.ico"
desktopPath = objShell.SpecialFolders("Desktop")
shortcutPath = desktopPath & "\Instagram Analyzer.lnk"

Set oShortcut = objShell.CreateShortcut(shortcutPath)
oShortcut.TargetPath       = "wscript.exe"
oShortcut.Arguments        = """" & startVbs & """"
oShortcut.WorkingDirectory = scriptDir
oShortcut.Description      = "Instagram Analyzer"
oShortcut.WindowStyle      = 1

If objFSO.FileExists(iconFile) Then
    oShortcut.IconLocation = iconFile & ",0"
End If

oShortcut.Save

MsgBox "Shortcut created on Desktop!" & Chr(10) & "Double-click 'Instagram Analyzer' to launch.", 64, "Done"

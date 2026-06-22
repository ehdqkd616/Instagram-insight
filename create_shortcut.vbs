
' 바탕화면에 Instagram Analyzer 바로가기 생성
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

' 아이콘 파일이 있으면 사용
If objFSO.FileExists(iconFile) Then
    oShortcut.IconLocation = iconFile & ",0"
End If

oShortcut.Save

MsgBox "바탕화면에 'Instagram Analyzer' 바로가기가 생성됐습니다!" & Chr(10) & _
       "더블클릭으로 실행하세요.", 64, "완료"

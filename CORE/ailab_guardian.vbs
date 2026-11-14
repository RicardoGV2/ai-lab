Set args = WScript.Arguments
If args.Count = 0 Then WScript.Quit
targetPid = args(0)
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
rootDir = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
flagFile = rootDir & "\BRAIN\.active_session.json"
batFile = rootDir & "\ailab.bat"

Do
    WScript.Sleep 2000
    If Not fso.FileExists(flagFile) Then
        WScript.Quit
    End If
    Set wmi = GetObject("winmgmts:\\.\root\cimv2")
    Set procs = wmi.ExecQuery("Select ProcessId From Win32_Process Where ProcessId = " & targetPid)
    If procs.Count = 0 Then
        WScript.Sleep 1500
        If fso.FileExists(flagFile) Then
            shell.Run "cmd /c start ""AI-LAB Recovery"" """ & batFile & """", 1, False
        End If
        WScript.Quit
    End If
Loop

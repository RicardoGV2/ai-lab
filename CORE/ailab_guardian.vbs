Set args = WScript.Arguments
If args.Count = 0 Then WScript.Quit
targetPid = args(0)
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
rootDir = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
flagFile = rootDir & "\BRAIN\.active_session.json"
batFile = rootDir & "\ailab.bat"
logFile = rootDir & "\BRAIN\guardian.log"

Sub WriteLog(msg)
    Set f = fso.OpenTextFile(logFile, 8, True)
    f.WriteLine Now & " | " & msg
    f.Close
End Sub

WriteLog "Guardian iniciado vigilando PID=" & targetPid

Do
    WScript.Sleep 1500
    If Not fso.FileExists(flagFile) Then
        WriteLog "Flag .active_session.json borrada (salida limpia). Saliendo."
        WScript.Quit
    End If
    Set wmi = GetObject("winmgmts:\\.\root\cimv2")
    Set procs = wmi.ExecQuery("Select ProcessId From Win32_Process Where ProcessId = " & targetPid)
    If procs.Count = 0 Then
        WriteLog "PID=" & targetPid & " desaparecio! Esperando 1.5s para confirmar..."
        WScript.Sleep 1500
        If fso.FileExists(flagFile) Then
            WriteLog "Lanzando ventana nueva via schtasks interactivo..."
            ' Tarea programada interactiva (/IT) para abrir ventana visible en el escritorio del usuario
            cmdCreate = "schtasks /Create /TN ""AILAB_Recover"" /TR ""cmd.exe /c start \""AI-LAB Recovery\"" \""" & batFile & "\"" "" /SC ONCE /ST 00:00 /F /IT"
            shell.Run cmdCreate, 0, True
            shell.Run "schtasks /Run /TN ""AILAB_Recover""", 0, True
            WriteLog "Tarea AILAB_Recover disparada con exito."
        End If
        WScript.Quit
    End If
Loop

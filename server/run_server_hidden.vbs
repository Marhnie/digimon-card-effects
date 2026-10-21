' Starts the judge-helper server keeper, the public quick tunnel and the address watcher, all without windows.
' Called at logon by Startup\DigimonJudgeServer.vbs. Pass "tunnel" to start only the tunnel parts.
Set sh = CreateObject("WScript.Shell")
dir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
onlyTunnel = (WScript.Arguments.Count > 0)
If Not onlyTunnel Then sh.Run "cmd /c """ & dir & "\run_server.cmd""", 0, False
sh.Run "cmd /c """ & dir & "\run_tunnel.cmd""", 0, False
sh.Run "powershell -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File """ & dir & "\watch_tunnel.ps1""", 0, False

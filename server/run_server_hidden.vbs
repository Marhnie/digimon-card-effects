' Starts server\run_server.cmd without a console window (used by the scheduled task).
Set sh = CreateObject("WScript.Shell")
dir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
sh.Run "cmd /c """ & dir & "\run_server.cmd""", 0, False

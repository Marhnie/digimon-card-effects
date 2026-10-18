// Unity -batchmode -projectPath <DCGO> -executeMethod HarnessCli.Run   (with env DCGO_JOB / DCGO_OUT set)
using UnityEditor;
using UnityEditor.SceneManagement;

public static class HarnessCli
{
    public static void Run()
    {
        EditorSceneManager.OpenScene("Assets/Scenes/BattleScene.unity");
        EditorApplication.EnterPlaymode();
    }

    // compile check only
    public static void Compile() { EditorApplication.Exit(0); }
}

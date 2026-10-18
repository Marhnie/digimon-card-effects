// Headless rules-question harness (card_effects project). Runs only when env DCGO_JOB points at a job JSON.
// Loads a vs-bot game, injects a board state, performs scripted actions, records the effect log + final state to DCGO_OUT.
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEngine;

public static class HarnessFlags
{
    public static bool Active;
    // -1 = engine/bot default, 0 = always decline, 1 = always accept optional effects for the scripted player
    public static int OptionalAnswer = 1;
}

[Serializable] public class HStack { public string[] cards; public bool suspended; }   // cards[0] = top
[Serializable] public class HSide { public int memory = 0; public string[] hand = new string[0]; public string[] trash = new string[0]; public string[] security = new string[0]; public HStack[] field = new HStack[0]; public bool clearHand = true; }
[Serializable] public class HStep { public string @do; public string card; public int frame = -1; public int target = -1; public int skill = 0; public int[] pick = new int[0]; public bool yes = true; }
[Serializable] public class HJob { public string id; public HSide you = new HSide(); public HSide opp = new HSide(); public HStep[] steps = new HStep[0]; public float timeScale = 20f; public float stepTimeout = 60f; public float calm = 6f; }

public class HarnessRunner : MonoBehaviour
{
    static string jobPath, outPath;
    readonly List<string> log = new List<string>();
    readonly List<string> errors = new List<string>();

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void Boot()
    {
        jobPath = Environment.GetEnvironmentVariable("DCGO_JOB");
        if (string.IsNullOrEmpty(jobPath) || !File.Exists(jobPath)) return;
        outPath = Environment.GetEnvironmentVariable("DCGO_OUT") ?? Path.ChangeExtension(jobPath, ".out.json");
        HarnessFlags.Active = true;
        var go = new GameObject("HarnessRunner");
        DontDestroyOnLoad(go);
        go.AddComponent<HarnessRunner>();
    }

    void Awake()
    {
        Application.logMessageReceived += (msg, st, type) => { if (type == LogType.Exception || type == LogType.Error) errors.Add(msg + (type == LogType.Exception ? " | " + st.Split('\n').FirstOrDefault() : "")); };
        PlayLog.OnAddLog += s => log.Add(s);
        StartCoroutine(Run());
    }

    HJob job; bool turnPassed; string lastSnap;
    IEnumerator Run()
    {
        job = JsonUtility.FromJson<HJob>(File.ReadAllText(jobPath, Encoding.UTF8));
        Time.timeScale = job.timeScale;
        float t0 = Time.realtimeSinceStartup;
        // 1. wait for a started game in our main phase
        while (!(GManager.instance != null && GManager.instance.turnStateMachine != null && GManager.instance.turnStateMachine.DoneStartGame
                 && GManager.instance.turnStateMachine.gameContext.TurnPhase == GameContext.phase.Main
                 && GManager.instance.turnStateMachine.gameContext.TurnPlayer == GManager.instance.You))
        {
            if (Time.realtimeSinceStartup - t0 > 300) { Finish("timeout waiting for main phase"); yield break; }
            yield return null;
        }
        Application.targetFrameRate = -1;
        yield return WaitIdle(10);
        log.Add("[harness] main phase reached");
        // 2. inject board state
        yield return Inject(GManager.instance.You, job.you);
        yield return Inject(GManager.instance.Opponent, job.opp);
        yield return WaitIdle(10);
        log.Add("[harness] injected");
        // 3. steps
        for (int i = 0; i < job.steps.Length; i++)
        {
            var s = job.steps[i];
            log.Add($"[harness] step {i}: {s.@do} {s.card} frame={s.frame} target={s.target}");
            string err = DoStep(s);
            if (err != null) { log.Add("[harness] step error: " + err); break; }
            yield return WaitIdle(job.stepTimeout);
        }
        Finish(null);
    }

    static CEntity_Base Entity(string id)
    {
        var cc = ContinuousController.instance;
        return cc.CardList.FirstOrDefault(e => e != null && e.CardID == id);
    }

    readonly Dictionary<string, CardSource> named = new Dictionary<string, CardSource>();
    CardSource Make(Player p, string id)
    {
        var e = Entity(id);
        if (e == null) { errors.Add("unknown card " + id); return null; }
        var c = CardObjectController.CreateCardSource(p.PlayerID, e, false);
        named[(p.isYou ? "you:" : "opp:") + id] = c;
        return c;
    }

    IEnumerator Inject(Player p, HSide side)
    {
        var cc = ContinuousController.instance;
        foreach (var perm in p.GetFieldPermanents().ToList()) yield return cc.StartCoroutine(CardObjectController.RemoveField(perm, true));
        foreach (var perm in p.GetBreedingAreaPermanents().ToList()) yield return cc.StartCoroutine(CardObjectController.RemoveField(perm, true));
        foreach (var sc in p.SecurityCards.ToList()) yield return cc.StartCoroutine(CardObjectController.AddTrashCard(sc));
        if (side.clearHand)
            foreach (var h in p.HandCards.ToList()) yield return cc.StartCoroutine(CardObjectController.AddTrashCard(h));
        p.TrashCards.Clear();
        foreach (var id in side.hand) { var c = Make(p, id); if (c != null) yield return cc.StartCoroutine(CardObjectController.AddHandCard(c, false)); }
        foreach (var id in side.trash) { var c = Make(p, id); if (c != null) yield return cc.StartCoroutine(CardObjectController.AddTrashCard(c)); }
        foreach (var id in side.security) { var c = Make(p, id); if (c != null) yield return cc.StartCoroutine(CardObjectController.AddSecurityCard(c, true, false, false)); }
        int frame = 0;
        foreach (var st in side.field)
        {
            var cards = st.cards.Select(id => Make(p, id)).Where(c => c != null).ToList(); cards.Reverse(); // JSON order: cards[0] = top; Permanent expects bottom first
            if (cards.Count == 0) continue;
            while (frame < p.fieldCardFrames.Count - 1 && !p.fieldCardFrames[frame].IsEmptyFrame()) frame++;
            var perm = new Permanent(cards);
            yield return cc.StartCoroutine(CardObjectController.CreateNewPermanent(perm, frame));
            if (perm.ShowingPermanentCard != null) perm.ShowingPermanentCard.gameObject.SetActive(true);
            perm.IsSuspended = st.suspended;
            frame++;
        }
        if (side.memory != 0) yield return cc.StartCoroutine(p.SetFixedMemory(side.memory, null));
    }

    Permanent FieldAt(Player p, int k) { var f = p.GetBattleAreaPermanents(); return k >= 0 && k < f.Count ? f[k] : null; }

    string DoStep(HStep s)
    {
        var tsm = GManager.instance.turnStateMachine;
        var you = GManager.instance.You;
        switch (s.@do)
        {
            case "play":
            case "digivolve":
            {
                var c = you.HandCards.FirstOrDefault(h => h.CardID == s.card);
                if (c == null) return "card not in hand: " + s.card;
                int frame;
                if (s.@do == "digivolve") { var perm = FieldAt(you, s.frame); if (perm == null) return "no permanent at " + s.frame; frame = Array.IndexOf(you.FieldPermanents, perm); }
                else { frame = 0; while (frame < you.fieldCardFrames.Count - 1 && !you.fieldCardFrames[frame].IsEmptyFrame()) frame++; }
                tsm.QueueMainPhaseAction(you, new PlayCardAction(c.CardIndex, frame, new int[0], -1, new int[0]));
                return null;
            }
            case "attack":
            {
                var f = you.GetFieldPermanents(); var a = FieldAt(you, s.frame); if (a == null) return "no attacker";
                int ti = -1; if (s.target >= 0) { var d = FieldAt(GManager.instance.Opponent, s.target); ti = GManager.instance.Opponent.GetFieldPermanents().IndexOf(d); }
                tsm.QueueMainPhaseAction(you, new AttackPermanentAction(f.IndexOf(a), ti));
                return null;
            }
            case "activate":
            {
                var f = you.GetFieldPermanents(); var a = FieldAt(you, s.frame); if (a == null) return "no permanent";
                tsm.QueueMainPhaseAction(you, new ActivatePermanentAction(f.IndexOf(a), s.skill));
                return null;
            }
            case "optional": HarnessFlags.OptionalAnswer = s.yes ? 1 : 0; return null;
            case "pass": tsm.QueueMainPhaseAction(you, new PassAction()); return null;
        }
        return "unknown step " + s.@do;
    }

    // idle = back in our main phase, nothing executing or being selected, for a few consecutive frames
    IEnumerator WaitIdle(float timeout)
    {
        float t0 = Time.realtimeSinceStartup; float calmSince = -1; int lastLogCount = log.Count;
        yield return null; yield return null;
        while (calmSince < 0 || Time.realtimeSinceStartup - calmSince < (job != null ? job.calm : 0.8f))
        {
            var tsm = GManager.instance.turnStateMachine;
            bool busy = tsm.isExecuting || tsm.IsSelecting || tsm.gameContext.TurnPhase != GameContext.phase.Main || tsm.gameContext.TurnPlayer != GManager.instance.You || tsm.endGame;
            if (tsm.gameContext.TurnPlayer != GManager.instance.You && !tsm.endGame) { log.Add("[harness] turn passed to opponent (state below is from before that)"); turnPassed = true; yield break; }
            if (log.Count != lastLogCount) { lastLogCount = log.Count; calmSince = -1; }
            if (busy) calmSince = -1; else { if (calmSince < 0) calmSince = Time.realtimeSinceStartup; try { lastSnap = Side(GManager.instance.You) + "|" + Side(GManager.instance.Opponent); } catch { } }
            if (tsm.endGame) { log.Add("[harness] game ended"); yield break; }
            if (Time.realtimeSinceStartup - t0 > timeout) { log.Add($"[harness] idle timeout (executing={tsm.isExecuting} selecting={tsm.IsSelecting} phase={tsm.gameContext.TurnPhase})"); yield break; }
            yield return null;
        }
    }

    static string Q(string s) => "\"" + (s ?? "").Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n").Replace("\r", "") + "\"";
    static string Arr(IEnumerable<string> xs) => "[" + string.Join(",", xs.Select(Q)) + "]";
    static string Side(Player p)
    {
        var sb = new StringBuilder("{");
        sb.Append("\"memory\":" + p.MemoryForPlayer);
        sb.Append(",\"hand\":" + Arr(p.HandCards.Select(c => c.CardID)));
        sb.Append(",\"trash\":" + Arr(p.TrashCards.Select(c => c.CardID)));
        sb.Append(",\"security\":" + p.SecurityCards.Count);
        sb.Append(",\"field\":[" + string.Join(",", p.GetFieldPermanents().Select(perm =>
            "{\"cards\":" + Arr(perm.cardSources.Select(c => c.CardID)) + ",\"dp\":" + (perm.TopCard != null && perm.TopCard.IsDigimon ? perm.DP : 0) + ",\"suspended\":" + (perm.IsSuspended ? "true" : "false") + "}")) + "]");
        return sb.Append("}").ToString();
    }

    void Finish(string fatal)
    {
        string json;
        try
        {
            var g = GManager.instance;
            json = "{\"id\":" + Q(job != null ? job.id : "") + ",\"fatal\":" + Q(fatal) +
                   (g != null && g.You != null ? ",\"you\":" + (turnPassed && lastSnap != null ? lastSnap.Split('|')[0] : Side(g.You)) + ",\"opp\":" + (turnPassed && lastSnap != null ? lastSnap.Split('|')[1] : Side(g.Opponent)) : "") +
                   ",\"log\":" + Arr(log) + ",\"errors\":" + Arr(errors.Take(50)) + "}";
        }
        catch (Exception e) { json = "{\"fatal\":" + Q("finish failed: " + e.Message) + ",\"log\":" + Arr(log) + "}"; }
        File.WriteAllText(outPath, json, new UTF8Encoding(false));
#if UNITY_EDITOR
        UnityEditor.EditorApplication.Exit(fatal == null ? 0 : 2);
#else
        Application.Quit(fatal == null ? 0 : 2);
#endif
    }
}

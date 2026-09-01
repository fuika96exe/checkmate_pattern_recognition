"use client";

import { useEffect, useMemo, useState } from "react";
import { Badge } from "@fluentui/react-badge";
import { Button } from "@fluentui/react-button";
import { Field } from "@fluentui/react-field";
import { Input } from "@fluentui/react-input";
import { Textarea } from "@fluentui/react-textarea";
import { AddRegular, BeakerRegular, DeleteRegular, PlayRegular } from "@fluentui/react-icons";
import { api } from "../lib/api";
import type { MemoryPreset, RecognitionState, RunAllResponse, TestCase } from "../lib/types";

const EMPTY_MEMORY: MemoryPreset = {
  redChoicePath: [], blackChoicePath: [], blackComposite: null, redWing: null, blackWing: null,
};

const CHOICE_OPTIONS = [
  ["", "由 FEN 推斷"],
  ["central_cannon", "中炮"], ["fly_elephant", "飛相／象"],
  ["proper_horse_opening", "起馬"], ["angle_pawn", "仙人指路／挺卒"],
  ["palcorner_cannon", "仕角炮"], ["cross_palace_cannon", "過宮炮"],
  ["proper_horse_opening,central_cannon", "起馬轉中炮"],
  ["proper_horse_opening,palcorner_cannon", "起馬轉仕角炮"],
  ["angle_pawn,central_cannon", "仙人指路轉中炮"],
  ["angle_pawn,fly_elephant", "仙人指路轉飛相"],
] as const;

const BLACK_COMPOSITES = [
  ["", "由 FEN 推斷"], ["screen_horse", "屏風馬"],
  ["reverse_palace_horse", "反宮馬"], ["single_horse", "單提馬"],
  ["left_three_step_tiger", "左三步虎"], ["right_three_step_tiger", "右三步虎"],
  ["left_cannon_blockade", "左炮封車"],
] as const;

function createDraft(fen: string, index: number): TestCase {
  return {
    id: `case-${String(index).padStart(2, "0")}`,
    name: "",
    fen,
    expectedName: "",
    memoryPreset: { ...EMPTY_MEMORY },
    notes: "",
    source: "user",
  };
}

interface Props { currentFen: string }

export function TestCaseLab({ currentFen }: Props) {
  const [cases, setCases] = useState<TestCase[]>([]);
  const [draft, setDraft] = useState<TestCase>(() => createDraft(currentFen, 1));
  const [preview, setPreview] = useState<RecognitionState | null>(null);
  const [run, setRun] = useState<RunAllResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const userCount = useMemo(() => cases.filter((item) => item.source === "user").length, [cases]);

  async function loadCases() {
    try { setCases(await api.cases()); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "無法載入案例"); }
  }

  useEffect(() => {
    let active = true;
    void api.cases().then((loaded) => {
      if (active) setCases(loaded);
    }).catch((reason: unknown) => {
      if (active) setError(reason instanceof Error ? reason.message : "無法載入案例");
    });
    return () => { active = false; };
  }, []);

  function setMemory(key: keyof MemoryPreset, value: string | null | string[]) {
    setDraft((current) => ({ ...current, memoryPreset: { ...current.memoryPreset, [key]: value } }));
  }

  async function analyze() {
    setBusy(true); setError("");
    try { setPreview((await api.inspect(draft.fen, draft.memoryPreset)).state); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "FEN 分析失敗"); }
    finally { setBusy(false); }
  }

  async function save() {
    if (!draft.id || !draft.name || !draft.expectedName) {
      setError("請填寫案例 ID、名稱及預期開局名稱"); return;
    }
    setBusy(true); setError("");
    try {
      await api.saveCase(draft);
      await loadCases();
      setDraft(createDraft(currentFen, userCount + 2));
      setPreview(null);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "儲存失敗"); }
    finally { setBusy(false); }
  }

  async function runAll() {
    setBusy(true); setError("");
    try { setRun(await api.runAll()); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "執行失敗"); }
    finally { setBusy(false); }
  }

  async function remove(id: string) {
    setBusy(true);
    try { await api.deleteCase(id); await loadCases(); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "刪除失敗"); }
    finally { setBusy(false); }
  }

  const resultById = new Map(run?.results.map((item) => [item.id, item]));

  return (
    <div className="test-layout">
      <section className="panel case-editor">
        <div className="panel-heading">
          <div><span className="eyebrow">CASE BUILDER</span><h2>新增辨認案例</h2></div>
          <Badge appearance="outline">你已輸入 {userCount} / 15</Badge>
        </div>
        <p className="support-copy">FEN 表示目前棋形；若名字依賴形成先後，請補上最小歷史記憶。</p>
        {error && <div className="error-banner" role="alert">{error}</div>}
        <div className="form-grid two">
          <Field label="案例 ID" hint="小寫字母、數字及連字號"><Input value={draft.id} onChange={(_, d) => setDraft({ ...draft, id: d.value })} /></Field>
          <Field label="案例名稱"><Input value={draft.name} onChange={(_, d) => setDraft({ ...draft, name: d.value })} /></Field>
        </div>
        <Field label="FEN"><Textarea resize="vertical" rows={3} value={draft.fen} onChange={(_, d) => setDraft({ ...draft, fen: d.value })} /></Field>
        <Button appearance="subtle" icon={<AddRegular />} onClick={() => setDraft({ ...draft, fen: currentFen })}>使用目前棋局 FEN</Button>
        <div className="form-grid two">
          <label className="native-field"><span>紅方主選擇歷史</span><select value={draft.memoryPreset.redChoicePath.join(",")} onChange={(e) => setMemory("redChoicePath", e.target.value ? e.target.value.split(",") : [])}>{CHOICE_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
          <label className="native-field"><span>黑方主選擇歷史</span><select value={draft.memoryPreset.blackChoicePath.join(",")} onChange={(e) => setMemory("blackChoicePath", e.target.value ? e.target.value.split(",") : [])}>{CHOICE_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
          <label className="native-field"><span>黑方複合體系</span><select value={draft.memoryPreset.blackComposite ?? ""} onChange={(e) => setMemory("blackComposite", e.target.value || null)}>{BLACK_COMPOSITES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
          <label className="native-field"><span>炮／馬方向</span><div className="direction-row"><select aria-label="紅方方向" value={draft.memoryPreset.redWing ?? ""} onChange={(e) => setMemory("redWing", e.target.value || null)}><option value="">紅：未指定</option><option value="left">紅：左</option><option value="right">紅：右</option></select><select aria-label="黑方方向" value={draft.memoryPreset.blackWing ?? ""} onChange={(e) => setMemory("blackWing", e.target.value || null)}><option value="">黑：未指定</option><option value="left">黑：左</option><option value="right">黑：右</option></select></div></label>
        </div>
        <Field label="預期開局名稱"><Input value={draft.expectedName} onChange={(_, d) => setDraft({ ...draft, expectedName: d.value })} /></Field>
        <Field label="備註"><Textarea resize="vertical" rows={2} value={draft.notes} onChange={(_, d) => setDraft({ ...draft, notes: d.value })} /></Field>
        {preview && <div className="preview-result"><span>目前判斷</span><strong>{preview.classification.displayName}</strong><Badge color={preview.classification.displayName === draft.expectedName ? "success" : "warning"}>{preview.classification.certainty}</Badge></div>}
        <div className="action-row"><Button icon={<BeakerRegular />} onClick={analyze} disabled={busy}>先分析</Button><Button appearance="primary" icon={<AddRegular />} onClick={save} disabled={busy}>儲存案例</Button></div>
      </section>

      <section className="panel cases-panel">
        <div className="panel-heading"><div><span className="eyebrow">REGRESSION</span><h2>測試案例</h2></div><Button appearance="primary" icon={<PlayRegular />} onClick={runAll} disabled={busy}>執行全部</Button></div>
        {run && <div className={`run-summary ${run.passed === run.total ? "pass" : "fail"}`}><strong>{run.passed} / {run.total}</strong><span>通過</span></div>}
        <div className="case-list">
          {cases.length === 0 && <div className="empty-state">尚未有案例。先確認 Python 後端正在運行。</div>}
          {cases.map((item) => {
            const result = resultById.get(item.id);
            return <article className="case-row" key={item.id}>
              <div className="case-status">{result ? <Badge color={result.passed ? "success" : "danger"}>{result.passed ? "PASS" : "FAIL"}</Badge> : <Badge appearance="outline">未執行</Badge>}</div>
              <div className="case-main"><div><strong>{item.name}</strong><span className="case-id">{item.id}</span></div><p>預期：{item.expectedName}{result && !result.passed ? ` · 實際：${result.actualName}` : ""}</p></div>
              <Badge appearance="tint" color={item.source === "built_in" ? "brand" : "informative"}>{item.source === "built_in" ? "內置" : "使用者"}</Badge>
              {item.source === "user" && <Button aria-label={`刪除 ${item.name}`} appearance="subtle" icon={<DeleteRegular />} onClick={() => remove(item.id)} />}
            </article>;
          })}
        </div>
      </section>
    </div>
  );
}

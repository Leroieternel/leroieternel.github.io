#!/usr/bin/env python3
"""Build a four-frame Panda 6062 report against reviewed hierarchy labels."""

from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any


MODES = ("om_only", "oa_om", "oa_future")
MODEL_LABELS = {
    "om_only": "OM only",
    "oa_om": "OA + OM",
    "oa_future": "OA + future actions",
}


def normalized(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def token_f1(prediction: str, target: str) -> float:
    predicted = Counter(normalized(prediction).split())
    expected = Counter(normalized(target).split())
    overlap = sum((predicted & expected).values())
    if not predicted or not expected:
        return float(predicted == expected)
    precision = overlap / sum(predicted.values())
    recall = overlap / sum(expected.values())
    return 2 * precision * recall / (precision + recall) if overlap else 0.0


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def row_key(row: dict[str, Any]) -> tuple[str, str, float]:
    return str(row["record_id"]), str(row["view"]), float(row["handoff_seconds"])


def at_frame(items: list[dict[str, Any]], frame: int, label: str) -> dict[str, Any]:
    matches = [item for item in items if int(item["start_frame"]) <= frame <= int(item["end_frame"])]
    if len(matches) != 1:
        raise ValueError(f"Expected one {label} at frame {frame}, got {len(matches)}")
    return matches[0]


def ground_truth(episode: dict[str, Any], frame: int) -> dict[str, Any]:
    atomic = at_frame(episode["atomic_tasks"], frame, "atomic task")
    missions = episode.get("short_term_missions") or episode["missions"]
    mission = at_frame(missions, frame, "short-term mission")
    effective = episode.get("effective_ongoing_missions") or []
    effective_item = at_frame(effective, frame, "effective mission") if effective else None
    ongoing_mission = (
        effective_item["ongoing_mission"]
        if effective_item
        else mission.get("short_term_mission", mission["mission"])
    )
    atomic_ids = list(mission.get("atomic_task_ids") or [])
    if not atomic_ids:
        atomic_ids = [
            item["atomic_task_id"]
            for item in episode["atomic_tasks"]
            if int(item["end_frame"]) >= int(mission["start_frame"])
            and int(item["start_frame"]) <= int(mission["end_frame"])
        ]
    current_id = atomic["atomic_task_id"]
    if current_id not in atomic_ids:
        raise ValueError(f"Atomic {current_id} is not a member of mission {mission['mission_id']}")
    atomic_by_id = {item["atomic_task_id"]: item for item in episode["atomic_tasks"]}
    position = atomic_ids.index(current_id)
    future = [atomic_by_id[item_id]["atomic_task"] for item_id in atomic_ids[position + 1 :]]
    return {
        "ongoing_action": atomic["atomic_task"],
        "ongoing_mission": ongoing_mission,
        "future_actions": future,
        "mission_done": not future,
        "mission": mission.get("short_term_mission", mission["mission"]),
        "mission_id": mission["mission_id"],
    }


def semantic_score(prediction: list[str], target: list[str]) -> dict[str, Any]:
    exact = [normalized(value) for value in prediction] == [normalized(value) for value in target]
    return {
        "exact": exact,
        "f1": token_f1(" ; ".join(prediction), " ; ".join(target)),
    }


def scalar_score(prediction: str | None, target: str) -> dict[str, Any]:
    return semantic_score([prediction or ""], [target])


def aggregate(scores: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "n": len(scores),
        "exact_count": sum(bool(score["exact"]) for score in scores),
        "exact": mean(float(score["exact"]) for score in scores),
        "f1": mean(float(score["f1"]) for score in scores),
    }


def load_contact_paths(report: Path) -> dict[tuple[str, str, float], str]:
    source = report.read_text(encoding="utf-8")
    match = re.search(r'<script id=report-data type=application/json>(.*?)</script>', source, re.S)
    if not match:
        raise ValueError(f"Could not find embedded report data in {report}")
    payload = json.loads(match.group(1))
    contacts = {row_key(row): str(row["contact_path"]) for row in payload["rows"]}
    if len(contacts) != 6062:
        raise ValueError(f"Expected 6062 contact sheets, got {len(contacts)}")
    return contacts


def load_predictions(root: Path) -> dict[str, dict[tuple[str, str, float], dict[str, Any]]]:
    result: dict[str, dict[tuple[str, str, float], dict[str, Any]]] = {}
    for mode in MODES:
        rows: list[dict[str, Any]] = []
        for path in sorted((root / mode).glob("replay_*_predictions.jsonl")):
            rows.extend(read_jsonl(path))
        indexed = {row_key(row): row for row in rows}
        if len(rows) != 6062 or len(indexed) != 6062:
            raise ValueError(f"{mode}: expected 6062 unique predictions, got {len(rows)}/{len(indexed)}")
        result[mode] = indexed
    if not (set(result["om_only"]) == set(result["oa_om"]) == set(result["oa_future"])):
        raise ValueError("Prediction cohorts do not match")
    return result


def model_result(mode: str, row: dict[str, Any], gt: dict[str, Any]) -> dict[str, Any]:
    parsed = row["score"]
    if mode == "om_only":
        prediction = [parsed.get("ongoing_mission") or ""]
        target = [gt["ongoing_mission"]]
        components = {
            "ongoing_mission": scalar_score(parsed.get("ongoing_mission"), gt["ongoing_mission"])
        }
    elif mode == "oa_om":
        prediction = [parsed.get("ongoing_action") or "", parsed.get("ongoing_mission") or ""]
        target = [gt["ongoing_action"], gt["ongoing_mission"]]
        components = {
            "ongoing_action": scalar_score(parsed.get("ongoing_action"), gt["ongoing_action"]),
            "ongoing_mission": scalar_score(parsed.get("ongoing_mission"), gt["ongoing_mission"]),
        }
    else:
        prediction = [parsed.get("ongoing_action") or ""] + list(parsed.get("future_actions") or [])
        target = [gt["ongoing_action"]] + list(gt["future_actions"])
        components = {
            "ongoing_action": scalar_score(parsed.get("ongoing_action"), gt["ongoing_action"]),
            "future_actions": semantic_score(list(parsed.get("future_actions") or []), gt["future_actions"]),
            "mission_done": {
                "exact": bool(parsed.get("mission_done")) == bool(gt["mission_done"]),
                "target": bool(gt["mission_done"]),
                "prediction": bool(parsed.get("mission_done")),
            },
        }
    return {
        "raw": parsed["raw_output"],
        "parsed": {
            "ongoing_action": parsed.get("ongoing_action"),
            "ongoing_mission": parsed.get("ongoing_mission"),
            "future_actions": parsed.get("future_actions") or [],
            "mission_done": bool(parsed.get("mission_done")),
        },
        "score": semantic_score(prediction, target),
        "components": components,
    }


def build(args: argparse.Namespace) -> None:
    labels = json.loads(args.labels.read_text(encoding="utf-8"))
    episodes = {episode["record_id"]: episode for episode in labels["episodes"]}
    if len(episodes) != 75:
        raise ValueError(f"Expected 75 episodes, got {len(episodes)}")
    predictions = load_predictions(args.prediction_root)
    contacts = load_contact_paths(args.contact_report)

    rows: list[dict[str, Any]] = []
    scores: dict[str, list[dict[str, Any]]] = {mode: [] for mode in MODES}
    scores_by_view = {
        mode: {"front": [], "wrist": []}
        for mode in MODES
    }
    for key, anchor in predictions["oa_om"].items():
        episode = episodes.get(anchor["record_id"])
        if episode is None:
            raise KeyError(anchor["record_id"])
        frame = min(int(anchor["prefix_frames"]) - 1, int(episode["total_frames"]) - 1)
        gt = ground_truth(episode, frame)
        outputs = {
            mode: model_result(mode, predictions[mode][key], gt)
            for mode in MODES
        }
        for mode in MODES:
            scores[mode].append(outputs[mode]["score"])
            scores_by_view[mode][anchor["view"]].append(outputs[mode]["score"])
        best_f1 = max(outputs[mode]["score"]["f1"] for mode in MODES)
        winners = [mode for mode in MODES if abs(outputs[mode]["score"]["f1"] - best_f1) < 1e-12]
        rows.append(
            {
                "record_id": anchor["record_id"],
                "episode_id": episode["episode_id"],
                "task_id": episode["task_id"],
                "view": anchor["view"],
                "handoff_seconds": anchor["handoff_seconds"],
                "cutoff_frame": frame,
                "frame_indices": anchor["frame_indices"],
                "fps": anchor["dataset_fps"],
                "full_task": episode["full_episode_instruction"],
                "context": anchor["context"],
                "contact_path": contacts[key],
                "ground_truth": gt,
                "outputs": outputs,
                "winner": winners[0] if len(winners) == 1 else "tie",
            }
        )
    rows.sort(
        key=lambda row: (
            int(row["task_id"]),
            int(row["episode_id"]),
            float(row["handoff_seconds"]),
            0 if row["view"] == "front" else 1,
        )
    )
    tasks = sorted({row["full_task"] for row in rows})
    summary = {
        "status": "complete",
        "label_file": args.labels.name,
        "episodes": len(episodes),
        "rows": len(rows),
        "views": {"front": sum(row["view"] == "front" for row in rows), "wrist": sum(row["view"] == "wrist" for row in rows)},
        "long_horizon_episodes": sum(bool(episode.get("long_horizon")) for episode in episodes.values()),
        "metrics": {
            mode: {
                "overall": aggregate(scores[mode]),
                "front": aggregate(scores_by_view[mode]["front"]),
                "wrist": aggregate(scores_by_view[mode]["wrist"]),
            }
            for mode in MODES
        },
        "score_definition": "Normalized structured semantic exact match; token F1 over semantic fields joined with semicolons.",
        "frame_policy": "The target is selected at prefix_frames - 1, the final observed frame in the four-frame input.",
    }
    report_data = {"summary": summary, "tasks": tasks, "rows": rows}
    encoded = json.dumps(report_data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.output_dir / "index.html").write_text(render_html(encoded), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def render_html(encoded: str) -> str:
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Panda 6062 · Reviewed Hierarchy Evaluation</title>
<style>
:root{{--bg:#080c12;--panel:#101722;--panel2:#151e2b;--line:#263449;--text:#edf4ff;--muted:#91a0b7;--blue:#5f91ff;--green:#42d4a0;--red:#ff7385;--amber:#ffbf69}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:16px/1.45 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}main{{max-width:1540px;margin:auto;padding:28px}}
h1{{font-size:clamp(2rem,5vw,4.2rem);line-height:.98;letter-spacing:-.05em;margin:.15em 0}}h2{{font-size:1.35rem;margin:0 0 14px}}h3{{font-size:1.05rem;margin:0}}p{{margin:.45rem 0}}code,pre{{font-family:"SFMono-Regular",Consolas,monospace}}.eyebrow{{color:#78a1ff;text-transform:uppercase;letter-spacing:.18em;font-weight:800;font-size:.78rem}}.muted{{color:var(--muted)}}
.top{{display:flex;justify-content:space-between;gap:22px;align-items:end;margin-bottom:26px}}.top p{{max-width:760px}}.summary-grid{{display:grid;grid-template-columns:repeat(3,minmax(230px,1fr));gap:14px;margin-bottom:18px}}.metric-card,.panel,.sample{{background:var(--panel);border:1px solid var(--line);border-radius:16px}}.metric-card{{padding:18px}}.metric-card .name{{font-weight:800}}.metric-card .numbers{{display:flex;gap:22px;margin-top:12px}}.metric-card strong{{font-size:1.55rem}}.metric-card small{{display:block;color:var(--muted)}}
.panel{{padding:18px;margin-bottom:18px}}.filters{{display:grid;grid-template-columns:minmax(240px,2fr) repeat(3,minmax(150px,1fr));gap:10px}}input,select,button{{font:inherit;color:var(--text);background:#0c121c;border:1px solid var(--line);border-radius:10px;padding:11px 13px}}button{{cursor:pointer;font-weight:750}}button:disabled{{opacity:.4;cursor:default}}
.countline{{display:flex;justify-content:space-between;gap:14px;margin:14px 2px}}.sample{{overflow:hidden;margin-bottom:16px}}.sample-head{{padding:16px 18px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:16px;align-items:start}}.sample-title{{font-weight:820;font-size:1.12rem}}.tags{{display:flex;flex-wrap:wrap;gap:7px;margin-top:8px}}.tag{{border:1px solid var(--line);border-radius:99px;padding:3px 9px;color:var(--muted);font-size:.78rem}}.tag.front{{color:#83bcff}}.tag.wrist{{color:#d5a3ff}}
.contact{{display:block;width:100%;height:auto;min-height:120px;background:#05070a;border-bottom:1px solid var(--line)}}.sample-body{{padding:16px 18px}}.gt{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:12px}}.gt>div{{background:#0b111a;border:1px solid var(--line);border-radius:11px;padding:11px}}.label{{display:block;color:var(--muted);font-size:.76rem;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px}}
.models{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}.model{{background:var(--panel2);border:1px solid var(--line);border-radius:12px;padding:12px;min-width:0}}.model.good{{border-color:#218b68}}.model-head{{display:flex;justify-content:space-between;gap:8px;align-items:center;margin-bottom:9px}}.pill{{border-radius:99px;padding:3px 8px;font-size:.76rem;background:#243044}}.pill.exact{{background:#164f3d;color:#8ff0cc}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;margin:0;color:#d7e2f3;font-size:.83rem;line-height:1.42}}.scoreline{{color:var(--muted);font-size:.82rem;margin-top:9px}}details{{margin-top:10px}}summary{{cursor:pointer;color:#a9bad3}}.context{{padding:12px;background:#0b111a;border-radius:10px;margin-top:10px;color:#c8d3e3}}.pager{{display:flex;justify-content:center;align-items:center;gap:12px;margin:24px 0 44px}}.winner{{color:var(--green)}}
@media(max-width:980px){{main{{padding:18px}}.top{{display:block}}.summary-grid,.models{{grid-template-columns:1fr}}.filters{{grid-template-columns:1fr 1fr}}.gt{{grid-template-columns:1fr}}}}@media(max-width:620px){{.filters{{grid-template-columns:1fr}}.sample-head{{display:block}}}}
</style></head><body><main>
<header class=top><div><div class=eyebrow>Human-reviewed temporal ground truth</div><h1>Panda Eval 6062</h1><p class=muted>Four-frame inputs, time-local hierarchy labels, and structured predictions from all three Qwen3.5-27B output schemes.</p></div><div class=muted id=cohort></div></header>
<section class=summary-grid id=summary></section>
<section class=panel id=browser><h2>Sample browser</h2><div class=filters><input id=q placeholder="Search task, episode, action or prediction…"><select id=view><option value="">All views</option><option value=front>Front</option><option value=wrist>Wrist</option></select><select id=task><option value="">All tasks</option></select><select id=result><option value="">Any result</option><option value=om_only>OM only has highest F1</option><option value=oa_om>OA + OM has highest F1</option><option value=oa_future>OA + future has highest F1</option><option value=tie>Tied highest F1</option><option value=any_exact>At least one exact</option><option value=none_exact>No exact output</option></select></div></section>
<div class=countline><div id=count class=muted></div><div class=muted>18 samples per page · images load on demand</div></div><div id=samples></div><div class=pager><button id=prev>Previous</button><span id=page></span><button id=next>Next</button></div>
</main><script id=report-data type=application/json>{encoded}</script><script>
const DATA=JSON.parse(document.querySelector('#report-data').textContent);const $=s=>document.querySelector(s);const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}}[c]));
const names={{om_only:'OM only',oa_om:'OA + OM',oa_future:'OA + future'}};const pct=x=>(100*x).toFixed(2)+'%';let page=0;const pageSize=18;
$('#cohort').textContent=`${{DATA.summary.episodes}} episodes · ${{DATA.summary.rows.toLocaleString()}} samples · ${{DATA.summary.views.front.toLocaleString()}} front + ${{DATA.summary.views.wrist.toLocaleString()}} wrist`;
$('#summary').innerHTML=['om_only','oa_om','oa_future'].map(mode=>{{const m=DATA.summary.metrics[mode];return `<article class=metric-card><div class=name>${{names[mode]}}</div><div class=numbers><div><strong>${{pct(m.overall.exact)}}</strong><small>Exact match</small></div><div><strong>${{m.overall.f1.toFixed(4)}}</strong><small>Token F1</small></div></div><p class=muted>Front F1 ${{m.front.f1.toFixed(4)}} · Wrist F1 ${{m.wrist.f1.toFixed(4)}}</p></article>`}}).join('');
DATA.tasks.forEach(t=>$('#task').insertAdjacentHTML('beforeend',`<option value="${{esc(t)}}">${{esc(t)}}</option>`));
function futureText(gt){{return gt.future_actions.length?gt.future_actions.map((x,i)=>`${{i+1}}. ${{x}}`).join('\n'):'Mission done'}}
function modelCard(mode,r){{const o=r.outputs[mode],s=o.score;return `<section class="model ${{s.exact?'good':''}}"><div class=model-head><h3>${{names[mode]}}</h3><span class="pill ${{s.exact?'exact':''}}">${{s.exact?'EXACT':'not exact'}}</span></div><pre>${{esc(o.raw)}}</pre><div class=scoreline>Structured EM ${{s.exact?'1':'0'}} · token F1 ${{s.f1.toFixed(4)}}</div><details><summary>Component scores</summary><pre>${{esc(Object.entries(o.components).map(([k,v])=>k+': '+(v.exact?'exact':'not exact')+(v.f1===undefined?'':' · F1 '+v.f1.toFixed(4))).join('\n'))}}</pre></details></section>`}}
function card(r){{const gt=r.ground_truth;return `<article class=sample><header class=sample-head><div><div class=sample-title>${{esc(r.full_task)}}</div><div class=tags><span class=tag>Episode ${{r.episode_id}} · Task ${{r.task_id}}</span><span class="tag ${{r.view}}">${{r.view}}</span><span class=tag>cutoff ${{r.handoff_seconds.toFixed(1)}}s / frame ${{r.cutoff_frame}}</span><span class=tag>input frames ${{r.frame_indices.join(', ')}}</span><span class=tag>${{esc(r.record_id)}}</span></div></div><div class=winner>${{r.winner==='tie'?'F1 tie':names[r.winner]+' highest F1'}}</div></header><img class=contact loading=lazy src="${{esc(r.contact_path)}}" alt="Four chronological ${{esc(r.view)}} input frames at indices ${{r.frame_indices.join(', ')}}"><div class=sample-body><section class=gt><div><span class=label>GT ongoing action</span>${{esc(gt.ongoing_action)}}</div><div><span class=label>GT ongoing mission</span>${{esc(gt.ongoing_mission)}}</div><div><span class=label>GT remaining within mission</span><pre>${{esc(futureText(gt))}}</pre></div></section><section class=models>${{['om_only','oa_om','oa_future'].map(m=>modelCard(m,r)).join('')}}</section><details><summary>Actual input context</summary><div class=context>${{esc(r.context)}}</div></details></div></article>`}}
function filtered(){{const q=$('#q').value.trim().toLowerCase(),view=$('#view').value,task=$('#task').value,result=$('#result').value;return DATA.rows.filter(r=>{{if(view&&r.view!==view)return false;if(task&&r.full_task!==task)return false;if(result==='any_exact'&&!Object.values(r.outputs).some(o=>o.score.exact))return false;if(result==='none_exact'&&Object.values(r.outputs).some(o=>o.score.exact))return false;if(result&&!['any_exact','none_exact'].includes(result)&&r.winner!==result)return false;if(q&&!JSON.stringify(r).toLowerCase().includes(q))return false;return true}})}}
function render(reset=false){{if(reset)page=0;const rows=filtered(),pages=Math.max(1,Math.ceil(rows.length/pageSize));page=Math.min(page,pages-1);const slice=rows.slice(page*pageSize,(page+1)*pageSize);$('#samples').innerHTML=slice.map(card).join('');$('#count').textContent=`${{rows.length.toLocaleString()}} matching samples`;$('#page').textContent=`Page ${{page+1}} / ${{pages}}`;$('#prev').disabled=page===0;$('#next').disabled=page>=pages-1}}
['#q','#view','#task','#result'].forEach(id=>$(id).addEventListener(id==='#q'?'input':'change',()=>render(true)));$('#prev').onclick=()=>{{page--;render();scrollTo({{top:$('#browser').offsetTop-20,behavior:'smooth'}})}};$('#next').onclick=()=>{{page++;render();scrollTo({{top:$('#browser').offsetTop-20,behavior:'smooth'}})}};render();
</script></body></html>'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--prediction-root", type=Path, required=True)
    parser.add_argument("--contact-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    build(parser.parse_args())


if __name__ == "__main__":
    main()

import type { RecognitionState } from "../lib/types";

const SYSTEM_LABELS: Record<string, string> = {
  central_cannon: "中炮", fly_elephant: "飛相／象", proper_horse_opening: "起馬",
  palcorner_cannon: "仕角炮", cross_palace_cannon: "過宮炮", angle_pawn: "仙人指路／挺卒",
  pawn_bottom_cannon: "卒底炮", screen_horse: "屏風馬", reverse_palace_horse: "反宮馬",
  single_horse: "單提馬", left_three_step_tiger: "左三步虎", right_three_step_tiger: "右三步虎",
  left_cannon_blockade: "左炮封車",
  five_six_cannon: "五六炮",
  five_seven_cannon: "五七炮",
  five_eight_cannon: "五八炮",
  five_nine_cannon: "五九炮",
  seven_route_horse: "七路馬",
  edge_horse_left: "邊馬",
  edge_horse_right: "邊馬",
  horizontal_rook: "橫車",
  straight_rook: "直車",
  double_horizontal_rooks: "雙橫車",
  river_cannon: "巡河炮",
  river_rook: "巡河車",
  riding_river_rook: "騎河車",
  cross_river_rook: "過河車",
  flat_cannon_exchange: "平炮兌車",
  advance_three_pawn: "進三兵",
  advance_seven_pawn: "進七兵",
  advance_three_soldier: "挺三卒",
  advance_seven_soldier: "挺七卒",
  two_headed_snake: "兩頭蛇",
  double_proper_horses: "雙正馬",
};

export function ChoicePath({ side, state }: { side: "red" | "black"; state: RecognitionState }) {
  const memory = state.openingMemory[side];
  const items = [...memory.choicePath, ...memory.compositeSystems, ...memory.formedShapes];
  return (
    <div className="choice-column">
      <div className="choice-label"><span className={`side-dot ${side}`} />{side === "red" ? "紅方" : "黑方"}</div>
      {items.length ? <div className="choice-path">{items.map((item, index) => {
        const wingText = item.id === "palcorner_cannon"
          ? ""
          : item.wing
            ? ` · ${item.wing === "left" ? "左" : "右"}`
            : "";
        return <span key={`${item.id}-${index}`}><strong>{SYSTEM_LABELS[item.id] ?? item.id}</strong><small>{item.source} · ply {item.formedAtPly}{wingText}</small></span>;
      })}</div> : <div className="choice-empty">尚未形成主選擇</div>}
    </div>
  );
}


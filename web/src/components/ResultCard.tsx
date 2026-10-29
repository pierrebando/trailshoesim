// One ranked shoe: score, price, why it fits, drawbacks, confidence, comparator button.

import type { Profile } from "../engine/profile";
import type { Point, RankedShoe } from "../engine/scoring";
import { becauseText, euro, SOURCE_LABEL, shoeName, TERM_LABEL } from "../labels";
import { ConfidenceBadge } from "./ConfidenceBadge";

interface Props {
  rank: number;
  result: RankedShoe;
  profile: Profile;
  inCompare: boolean;
  compareFull: boolean;
  onToggleCompare: () => void;
}

function PointLine({ point, profile }: { point: Point; profile: Profile }) {
  return (
    <>
      <strong>{TERM_LABEL[point.key]} {point.value.toFixed(1)}/10</strong> ({point.label}). Weighted{" "}
      {Math.round(point.weightShare * 100)} % for you {becauseText(point.because, profile.terrains, profile.footStrike)}.
      {point.quote && (
        <q className="quote">
          {point.quote.text}{" "}
          <a href={point.quote.url} target="_blank" rel="noopener noreferrer">
            {SOURCE_LABEL[point.quote.source] ?? point.quote.source}
          </a>
        </q>
      )}
    </>
  );
}

export function ResultCard({ rank, result, profile, inCompare, compareFull, onToggleCompare }: Props) {
  const { shoe, explanation } = result;
  const prices = shoe.retail.map((o) => o.price_eur);
  const cheapest = shoe.retail.reduce((best, o) => (o.price_eur < best.price_eur ? o : best), shoe.retail[0]);
  const low = Math.min(...prices);
  const high = Math.max(...prices);
  const name = shoeName(shoe);

  return (
    <article className="card" aria-labelledby={`title-${shoe.id}`}>
      <div className="card-head">
        <span className="rank" aria-label={`Rank ${rank}`}>{rank}</span>
        <div className="card-title">
          <h3 id={`title-${shoe.id}`}><a href={`#/shoe/${shoe.id}`}>{name}</a></h3>
          <p className="price">
            {low === high ? euro(low) : `${euro(low)}–${euro(high)}`} ·{" "}
            <a href={cheapest.url} target="_blank" rel="noopener noreferrer">
              cheapest at {SOURCE_LABEL[cheapest.retailer] ?? cheapest.retailer}
            </a>
          </p>
        </div>
        <div className="score" aria-label={`Score ${Math.round(result.score ?? 0)} out of 100`}>
          <span className="score-value">{Math.round(result.score ?? 0)}</span>
          <span className="score-max">/100</span>
        </div>
      </div>

      {explanation.reasons.length > 0 && (
        <div className="points">
          <h4>Why it fits</h4>
          <ul>
            {explanation.reasons.map((p) => <li key={p.key}><PointLine point={p} profile={profile} /></li>)}
          </ul>
        </div>
      )}
      {(explanation.drawbacks.length > 0 || explanation.missing.length > 0) && (
        <div className="points drawbacks">
          <h4>Watch out</h4>
          <ul>
            {explanation.drawbacks.map((p) => <li key={p.key}><PointLine point={p} profile={profile} /></li>)}
            {explanation.missing.slice(0, Math.max(0, 2 - explanation.drawbacks.length)).map((m) => (
              <li key={m.key}>No reliable data on {TERM_LABEL[m.key].toLowerCase()}.</li>
            ))}
          </ul>
        </div>
      )}

      <div className="card-foot">
        <ConfidenceBadge confidence={shoe.confidence} />
        <button type="button" className={inCompare ? "button selected" : "button"} aria-pressed={inCompare}
          disabled={!inCompare && compareFull} onClick={onToggleCompare}>
          {inCompare ? "✓ In comparator" : compareFull ? "Comparator full (4)" : "+ Compare"}
        </button>
      </div>
    </article>
  );
}

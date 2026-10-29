import type { Meta } from "../engine/types";

const day = (iso: string) => new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });

export function Footer({ meta }: { meta: Meta }) {
  const prices =
    meta.price_date_min === meta.price_date_max
      ? `prices checked on ${day(meta.price_date_max)}`
      : `prices checked between ${day(meta.price_date_min)} and ${day(meta.price_date_max)}`;
  return (
    <footer className="footer">
      <p>
        Data built on {day(meta.build_date)} · {prices} · {meta.shoe_count} shoes, {meta.brand_count} brands.
      </p>
      <p>
        Scores are heuristics, not science. <a href="#/how">How it works</a>
      </p>
    </footer>
  );
}

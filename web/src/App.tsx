// App shell: loads the data, keeps the state in the URL and picks the page from the hash.
//
// URL layout: ?<profile, filters, comparator>#/<page>
//   #/            finder (profile form + ranked results)
//   #/shoe/<id>     model page
//   #/similar[/<id>] "I like this model"
//   #/compare       comparator
//   #/how           how it works

import { useCallback, useEffect, useState } from "react";
import { Footer } from "./components/Footer";
import { Header } from "./components/Header";
import { useAppData } from "./data";
import { ComparePage } from "./pages/ComparePage";
import { FinderPage } from "./pages/FinderPage";
import { HowPage } from "./pages/HowPage";
import { ShoePage } from "./pages/ShoePage";
import { SimilarPage } from "./pages/SimilarPage";
import { decodeState, encodeState, type AppState } from "./url";

function useHashRoute(): string {
  const [hash, setHash] = useState(window.location.hash || "#/");
  useEffect(() => {
    const onChange = () => {
      setHash(window.location.hash || "#/");
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return hash;
}

function useUrlState(): [AppState, (next: AppState) => void] {
  const [state, setState] = useState<AppState>(() => decodeState(window.location.search));
  const update = useCallback((next: AppState) => {
    setState(next);
    const query = encodeState(next);
    // replaceState: editing the profile should not fill the browser history.
    window.history.replaceState(null, "", `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`);
  }, []);
  return [state, update];
}

export function App() {
  const { data, error } = useAppData();
  const route = useHashRoute();
  const [state, setState] = useUrlState();

  const [, section = "", param = null] = route.replace(/^#/, "").split("/");
  useEffect(() => {
    const titles: Record<string, string> = { "": "Find a shoe", shoe: "Model", similar: "I like this model", compare: "Compare", how: "How it works" };
    document.title = `${titles[section] ?? "Page not found"} · Trail Shoe Finder`;
  }, [section]);

  let page;
  if (error) page = <p role="alert" className="notice">The data could not be loaded: {error}</p>;
  else if (!data) page = <p className="notice" aria-live="polite">Loading the catalogue…</p>;
  else if (section === "") page = <FinderPage data={data} state={state} setState={setState} />;
  else if (section === "shoe" && param) page = <ShoePage data={data} state={state} setState={setState} shoeId={param} />;
  else if (section === "similar") page = <SimilarPage data={data} state={state} setState={setState} referenceId={param} />;
  else if (section === "compare") page = <ComparePage data={data} state={state} setState={setState} />;
  else if (section === "how") page = <HowPage data={data} />;
  else page = <p className="notice">This page does not exist. <a href="#/">Back to the finder</a></p>;

  return (
    <div className="app">
      <Header route={`#/${section}`} compareCount={state.compare.length} />
      <main id="main" className="main" tabIndex={-1}>{page}</main>
      {data && <Footer meta={data.meta} />}
    </div>
  );
}

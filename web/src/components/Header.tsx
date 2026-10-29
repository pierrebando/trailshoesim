export function Header({ route, compareCount }: { route: string; compareCount: number }) {
  const link = (href: string, text: string) => (
    <a href={href} aria-current={route === href ? "page" : undefined}>
      {text}
    </a>
  );
  return (
    <header className="header">
      <a className="skip-link" href="#main" onClick={(e) => { e.preventDefault(); document.getElementById("main")?.focus(); }}>
        Skip to content
      </a>
      <a href="#/" className="brand">Trail Shoe Finder</a>
      <nav aria-label="Main">
        {link("#/", "Find")}
        {link("#/similar", "I like this model")}
        {link("#/compare", `Compare (${compareCount})`)}
        {link("#/how", "How it works")}
      </nav>
    </header>
  );
}

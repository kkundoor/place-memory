import { FormEvent, useEffect, useState } from 'react';

import { MemoryCard } from './components/MemoryCard';
import { createMemory, getFeasible, listMemories } from './lib/api';
import type { FeasibleMemory, Memory } from './types';
import './styles.css';

export default function App() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [sourceText, setSourceText] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [query, setQuery] = useState('what from my saves is doable now?');
  const [minutes, setMinutes] = useState(120);
  const [results, setResults] = useState<FeasibleMemory[]>([]);
  const [message, setMessage] = useState('');

  async function refresh() {
    setMemories(await listMemories());
  }

  useEffect(() => {
    refresh().catch(() => setMessage('api is not running yet'));
  }, []);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!sourceText.trim()) return;
    await createMemory(sourceText.trim(), sourceUrl.trim());
    setSourceText('');
    setSourceUrl('');
    setMessage('saved — resolve step is next');
    await refresh();
  }

  async function checkNow() {
    setMessage('getting current location...');
    navigator.geolocation.getCurrentPosition(async (position) => {
      try {
        const next = await getFeasible(
          query,
          position.coords.latitude,
          position.coords.longitude,
          minutes,
        );
        setResults(next);
        setMessage('');
      } catch {
        setMessage('could not check right now');
      }
    }, () => setMessage('location permission is needed for this check'));
  }

  return (
    <main>
      <header>
        <p className="eyebrow">personal place memory</p>
        <h1>save it once. use it when you're actually there.</h1>
        <p className="lede">
          Turn scattered place saves into something you can search by context, location, and time.
        </p>
      </header>

      <section className="panel">
        <h2>add a save</h2>
        <form onSubmit={save}>
          <textarea
            value={sourceText}
            onChange={(event) => setSourceText(event.target.value)}
            placeholder="paste the place name, screenshot text, or what you remember"
          />
          <input
            value={sourceUrl}
            onChange={(event) => setSourceUrl(event.target.value)}
            placeholder="source link (optional)"
          />
          <button type="submit">save</button>
        </form>
      </section>

      <section className="panel">
        <h2>right now</h2>
        <div className="query-row">
          <input value={query} onChange={(event) => setQuery(event.target.value)} />
          <input
            className="minutes"
            type="number"
            min={15}
            max={720}
            value={minutes}
            onChange={(event) => setMinutes(Number(event.target.value))}
          />
          <button onClick={checkNow}>check</button>
        </div>
        {message && <p className="message">{message}</p>}
        <div className="results">
          {results.map((result) => (
            <article className="result-card" key={result.memory.id}>
              <span className={`result-status ${result.status}`}>{result.status}</span>
              <h3>{result.memory.place?.name}</h3>
              <p>{result.travel_minutes != null ? `${result.travel_minutes} min away` : 'travel time unavailable'}</p>
              <p className="muted">{result.reasons.join(' · ')}</p>
            </article>
          ))}
        </div>
      </section>

      <section>
        <div className="section-title">
          <h2>saved</h2>
          <span>{memories.length}</span>
        </div>
        <div className="grid">
          {memories.map((memory) => <MemoryCard key={memory.id} memory={memory} />)}
        </div>
      </section>
    </main>
  );
}

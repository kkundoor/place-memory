import { FormEvent, useEffect, useState } from 'react';

import { MemoryCard } from './components/MemoryCard';
import { confirmMemory, getFeasible, getMap, ingestImage, ingestMemory, listMemories } from './lib/api';
import type { FeasibleMemory, Memory, PlaceCandidate } from './types';
import './styles.css';

export default function App() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [sourceText, setSourceText] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [image, setImage] = useState<File | null>(null);
  const [query, setQuery] = useState('what from my saves is doable now?');
  const [minutes, setMinutes] = useState(120);
  const [results, setResults] = useState<FeasibleMemory[]>([]);
  const [message, setMessage] = useState('');
  const [mapImage, setMapImage] = useState('');
  const [busy, setBusy] = useState(false);

  async function refresh() {
    setMemories(await listMemories());
  }

  useEffect(() => {
    refresh().catch(() => setMessage('api is not running yet'));
  }, []);

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!sourceText.trim() && !image) return;
    setBusy(true);
    setMessage('resolving place...');
    try {
      const response = image
        ? await ingestImage(image, sourceUrl.trim())
        : await ingestMemory(sourceText.trim(), sourceUrl.trim());
      setSourceText('');
      setSourceUrl('');
      setImage(null);
      setMessage(response.warning || `saved as ${response.memory.resolution_status}`);
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'could not save');
    } finally {
      setBusy(false);
    }
  }

  async function confirm(memory: Memory, candidate: PlaceCandidate) {
    try {
      await confirmMemory(memory, candidate);
      setMessage('place confirmed');
      await refresh();
    } catch {
      setMessage('could not confirm place');
    }
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

        getMap(query, position.coords.latitude, position.coords.longitude, minutes)
          .then(setMapImage)
          .catch(() => setMapImage(''));
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
            placeholder="paste a place, caption, note, or screenshot text"
          />
          <input
            value={sourceUrl}
            onChange={(event) => setSourceUrl(event.target.value)}
            placeholder="source link (optional)"
          />
          <label className="file-input">
            <span>{image ? image.name : 'or add a screenshot'}</span>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={(event) => setImage(event.target.files?.[0] || null)}
            />
          </label>
          <button type="submit" disabled={busy}>{busy ? 'working...' : 'save + resolve'}</button>
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
        {mapImage && <img className="map" src={mapImage} alt="Saved places near the current location" />}
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
          {memories.map((memory) => (
            <MemoryCard key={memory.id} memory={memory} onConfirm={confirm} />
          ))}
        </div>
      </section>
    </main>
  );
}

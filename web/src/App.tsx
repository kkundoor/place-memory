import { FormEvent, useEffect, useState } from 'react';

import { MemoryCard } from './components/MemoryCard';
import {
  confirmMemory,
  deleteMemory,
  getFeasible,
  getMap,
  ingestImage,
  ingestMemory,
  listMemories,
  rejectCandidates,
} from './lib/api';
import type { FeasibleMemory, Memory, PlaceCandidate } from './types';
import './styles.css';

export default function App() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [sourceText, setSourceText] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [image, setImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState('');
  const [saveMessage, setSaveMessage] = useState('');
  const [query, setQuery] = useState('what from my saves is doable now?');
  const [minutes, setMinutes] = useState(120);
  const [results, setResults] = useState<FeasibleMemory[]>([]);
  const [nowMessage, setNowMessage] = useState('');
  const [mapImage, setMapImage] = useState('');
  const [busy, setBusy] = useState(false);

  async function refresh() {
    setMemories(await listMemories());
  }

  useEffect(() => {
    refresh().catch(() => setSaveMessage('API is not running yet.'));
  }, []);

  useEffect(() => {
    if (!image) {
      setImagePreview('');
      return;
    }
    const url = URL.createObjectURL(image);
    setImagePreview(url);
    return () => URL.revokeObjectURL(url);
  }, [image]);

  async function save(event: FormEvent) {
    event.preventDefault();
    const context = sourceText.trim();
    if (!context && !image) return;

    setBusy(true);
    setSaveMessage(image ? 'Analyzing screenshot…' : 'Resolving place…');

    try {
      const response = image
        ? await ingestImage(image, sourceUrl.trim(), context)
        : await ingestMemory(context, sourceUrl.trim());

      setSourceText('');
      setSourceUrl('');
      setImage(null);

      const statusMessage = {
        resolved: 'Place identified and saved.',
        needs_review: 'Saved — choose the right match below.',
        unresolved: "Saved, but I couldn't identify the place yet.",
      }[response.memory.resolution_status];

      setSaveMessage(response.warning || statusMessage);
      await refresh();
    } catch (error) {
      setSaveMessage(error instanceof Error ? error.message : 'Could not save.');
    } finally {
      setBusy(false);
    }
  }

  async function confirm(memory: Memory, candidate: PlaceCandidate) {
    try {
      await confirmMemory(memory, candidate);
      setSaveMessage('Place confirmed.');
      await refresh();
    } catch {
      setSaveMessage('Could not confirm place.');
    }
  }

  async function reject(memory: Memory) {
    try {
      await rejectCandidates(memory);
      setSaveMessage('Kept unresolved — none of those matches were right.');
      await refresh();
    } catch {
      setSaveMessage('Could not reject candidates.');
    }
  }

  async function remove(memory: Memory) {
    if (!window.confirm(`Remove ${memory.place?.name || memory.hint?.name || 'this save'}?`)) return;
    try {
      await deleteMemory(memory.id);
      setResults((current) => current.filter((result) => result.memory.id !== memory.id));
      setMapImage('');
      setSaveMessage('Save removed.');
      await refresh();
    } catch {
      setSaveMessage('Could not remove save.');
    }
  }

  async function checkNow() {
    setNowMessage('Getting current location…');
    navigator.geolocation.getCurrentPosition(async (position) => {
      try {
        const next = await getFeasible(
          query,
          position.coords.latitude,
          position.coords.longitude,
          minutes,
        );
        setResults(next);
        setNowMessage('');

        getMap(query, position.coords.latitude, position.coords.longitude, minutes)
          .then(setMapImage)
          .catch(() => setMapImage(''));
      } catch {
        setNowMessage('Could not check right now.');
      }
    }, () => setNowMessage('Location permission is needed for this check.'));
  }

  const canSave = Boolean(sourceText.trim() || image);

  return (
    <main>
      <header>
        <p className="eyebrow">personal place memory</p>
        <h1>save it once. use it when you're actually there.</h1>
        <p className="lede">
          Turn scattered place saves into something you can search by context, location, and time.
        </p>
      </header>

      <section className="panel save-panel">
        <div className="panel-heading">
          <div>
            <h2>add a save</h2>
            <p>Add whatever you have. Text and screenshots can work together.</p>
          </div>
        </div>

        <form onSubmit={save}>
          <label className="field">
            <span>What did you save? <em>optional if you attach a screenshot</em></span>
            <textarea
              value={sourceText}
              onChange={(event) => setSourceText(event.target.value)}
              placeholder="e.g. friend said this is in Golden Gate Park — want to rent a pedal boat"
            />
          </label>

          <label className={`upload-box compact ${image ? 'has-file' : ''}`}>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={(event) => setImage(event.target.files?.[0] || null)}
            />
            {imagePreview ? (
              <img className="upload-preview" src={imagePreview} alt="Selected screenshot preview" />
            ) : (
              <span className="upload-icon" aria-hidden="true">↑</span>
            )}
            <strong>{image ? image.name : 'Attach screenshot'}</strong>
            <span>{image ? 'Click to choose a different image' : 'PNG, JPG, or WebP · up to 8 MB'}</span>
          </label>

          <label className="field">
            <span>Source link <em>optional metadata</em></span>
            <input
              value={sourceUrl}
              onChange={(event) => setSourceUrl(event.target.value)}
              placeholder="https://…"
            />
          </label>

          <button type="submit" disabled={busy || !canSave}>
            {busy ? 'Working…' : 'Save + identify'}
          </button>
        </form>

        {saveMessage && <p className="message save-message">{saveMessage}</p>}
      </section>

      <section>
        <div className="section-title">
          <div>
            <h2>saved places</h2>
            <p>Review anything uncertain before it becomes canonical.</p>
          </div>
          <span className="count">{memories.length}</span>
        </div>

        {memories.length === 0 ? (
          <div className="empty-state">Your resolved and unresolved saves will appear here.</div>
        ) : (
          <div className="grid">
            {memories.map((memory) => (
              <MemoryCard
                key={memory.id}
                memory={memory}
                onConfirm={confirm}
                onReject={reject}
                onDelete={remove}
              />
            ))}
          </div>
        )}
      </section>

      <section className="panel right-now-panel">
        <div className="panel-heading">
          <div>
            <h2>what can I do right now?</h2>
            <p>Use your current location and available time to filter resolved saves.</p>
          </div>
        </div>

        <div className="query-row">
          <label className="field query-field">
            <span>Question</span>
            <input value={query} onChange={(event) => setQuery(event.target.value)} />
          </label>
          <label className="field minutes-field">
            <span>Minutes</span>
            <input
              className="minutes"
              type="number"
              min={15}
              max={720}
              value={minutes}
              onChange={(event) => setMinutes(Number(event.target.value))}
            />
          </label>
          <button onClick={checkNow}>Find doable saves</button>
        </div>

        {nowMessage && <p className="message">{nowMessage}</p>}
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

      <footer className="attribution">
        Place data © OpenStreetMap contributors. Live provider data may be used when configured.
      </footer>
    </main>
  );
}

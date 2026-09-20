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
  resolveDemoImage,
  resolveDemoMemory,
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
  const [demoResult, setDemoResult] = useState<Memory | null>(null);
  const demoMode = import.meta.env.VITE_DEMO_MODE === 'true';

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

    if (image && image.size > 8 * 1024 * 1024) {
      setSaveMessage('Image must be under 8 MB.');
      return;
    }

    setBusy(true);
    setSaveMessage(
      image
        ? 'Reading screenshot and checking real places…'
        : 'Reading your note and checking real places…',
    );

    try {
      const response = demoMode
        ? (
            image
              ? await resolveDemoImage(image, sourceUrl.trim(), context)
              : await resolveDemoMemory(context, sourceUrl.trim())
          )
        : (
            image
              ? await ingestImage(image, sourceUrl.trim(), context)
              : await ingestMemory(context, sourceUrl.trim())
          );

      const statusMessage = demoMode
        ? {
            resolved: 'Place identified.',
            needs_review: 'A likely match was found — choose the right one below.',
            unresolved: "There wasn't enough evidence to identify a specific place.",
          }[response.memory.resolution_status]
        : {
            resolved: 'Place identified and saved.',
            needs_review: 'Saved — choose the right match below.',
            unresolved: "Saved, but I couldn't identify the place yet.",
          }[response.memory.resolution_status];

      setSaveMessage(response.warning || statusMessage);

      if (demoMode) {
        setDemoResult(response.memory);
        return;
      }

      setSourceText('');
      setSourceUrl('');
      setImage(null);
      await refresh();
    } catch (error) {
      setSaveMessage(
        error instanceof Error
          ? error.message
          : 'Could not identify the place.',
      );
    } finally {
      setBusy(false);
    }
  }

  async function confirm(memory: Memory, candidate: PlaceCandidate) {
    if (demoMode && memory.id.startsWith('demo-live-')) {
      const confirmedCandidate: PlaceCandidate = {
        ...candidate,
        confidence_reasons: [
          ...(candidate.confidence_reasons || []),
          'confirmed by demo visitor',
        ],
      };

      const updated: Memory = {
        ...memory,
        place: confirmedCandidate,
        resolution_status: 'resolved',
        resolution_method: 'manual',
      };

      setDemoResult(updated);
      setSaveMessage('Match confirmed locally for this demo.');
      return;
    }

    try {
      await confirmMemory(memory, candidate);
      setSaveMessage('Place confirmed.');
      await refresh();
    } catch {
      setSaveMessage('Could not confirm place.');
    }
  }

  async function reject(memory: Memory) {
    if (demoMode && memory.id.startsWith('demo-live-')) {
      const updated: Memory = {
        ...memory,
        place: null,
        resolution_status: 'unresolved',
        resolution_method: 'abstained',
      };

      setDemoResult(updated);
      setSaveMessage('Kept unresolved — none of those matches were right.');
      return;
    }

    try {
      await rejectCandidates(memory);
      setSaveMessage('Kept unresolved — none of those matches were right.');
      await refresh();
    } catch {
      setSaveMessage('Could not reject candidates.');
    }
  }

  async function remove(memory: Memory) {
    if (demoMode && memory.id.startsWith('demo-live-')) {
      setDemoResult(null);
      setSaveMessage('');
      return;
    }

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

  function resetDemo() {
    setSourceText('');
    setSourceUrl('');
    setImage(null);
    setDemoResult(null);
    setSaveMessage('');
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

      {demoMode && (
        <section className="panel demo-panel">
          <p className="eyebrow">interactive public demo</p>
          <h2>Give it a messy place save.</h2>
          <p>
            Type a note or attach a screenshot. The live demo runs the same extraction, place retrieval, and resolver
            pipeline as the local app. Place Memory does not write demo inputs
            or results to its storage.
          </p>
        </section>
      )}

      <section className="panel save-panel">
        <div className="panel-heading">
          <div>
            <h2>{demoMode ? 'try it live' : 'add a save'}</h2>
            <p>
              {demoMode
                ? 'Use a note, screenshot, or both. The result appears below.'
                : 'Add whatever you have. Text and screenshots can work together.'}
            </p>
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

          {image && (
            <button
              type="button"
              className="secondary-action"
              onClick={() => setImage(null)}
              disabled={busy}
            >
              Remove screenshot
            </button>
          )}

          <label className="field">
            <span>Source link <em>optional metadata</em></span>
            <input
              value={sourceUrl}
              onChange={(event) => setSourceUrl(event.target.value)}
              placeholder="https://…"
            />
          </label>

          <button type="submit" disabled={busy || !canSave}>
            {busy
              ? image
                ? 'Analyzing screenshot...'
                : 'Identifying...'
              : demoMode
                ? 'Identify place'
                : 'Save + identify'}
          </button>
        </form>

        {demoMode && (
          <p className="demo-privacy">
            Demo inputs are not stored by Place Memory. Text and screenshots are
            processed by Gemini; extracted place hints may be sent to
            Photon/Nominatim for candidate lookup.
          </p>
        )}

        {saveMessage && <p className="message save-message">{saveMessage}</p>}
      </section>

      {demoMode && (
        <section className="demo-result-section">
          <div className="section-title">
            <div>
              <h2>latest result</h2>
              <p>
                This result was returned by the live extraction → retrieval → resolver
                path and is not written to Place Memory storage.
              </p>
            </div>
          </div>

          {demoResult ? (
            <div className="demo-result">
              <MemoryCard
                memory={demoResult}
                readOnly={false}
                onConfirm={confirm}
                onReject={reject}
                onDelete={remove}
              />

              <button
                type="button"
                className="secondary-action demo-reset"
                onClick={resetDemo}
                disabled={busy}
              >
                Try another save
              </button>
            </div>
          ) : (
            <div className="empty-state">
              Run a note or screenshot above to see the resolver decision here.
            </div>
          )}
        </section>
      )}

      <section>
        <div className="section-title">
          <div>
            <h2>{demoMode ? 'regression examples' : 'saved places'}</h2>
            <p>
              {demoMode
                ? 'Fixed cases below show the three intended resolver behaviors: resolve, review, and abstain.'
                : 'Review anything uncertain before it becomes canonical.'}
            </p>
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
                readOnly={demoMode}
                memory={memory}
                onConfirm={confirm}
                onReject={reject}
                onDelete={remove}
              />
            ))}
          </div>
        )}
      </section>

      <section className={`panel right-now-panel ${demoMode ? 'demo-hidden' : ''}`}>
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
        {' · '}
        <a href="https://github.com/kkundoor/place-memory" target="_blank" rel="noreferrer">
          GitHub
        </a>
      </footer>
    </main>
  );
}

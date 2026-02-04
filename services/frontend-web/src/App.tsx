import { useEffect, useRef, useState } from "react";

const gatewayUrl = import.meta.env.VITE_GATEWAY_URL || "http://localhost:8080";

const MODEL_PRESETS: Record<string, string[]> = {
  ollama: ["llama3.2:3b"],
  openai: ["gpt-4o-mini", "gpt-4o"],
  gemini: ["gemini-2.5-flash", "gemini-2.5-pro"]
};

type Message = {
  role: "user" | "assistant";
  content: string;
};

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [useRag, setUseRag] = useState(true);
  const [topK, setTopK] = useState(5);
  const [provider, setProvider] = useState("ollama");
  const [model, setModel] = useState(MODEL_PRESETS.ollama[0]);
  const [apiKey, setApiKey] = useState("");
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    const presets = MODEL_PRESETS[provider] || [];
    setModel(presets[0] || "");
  }, [provider]);

  useEffect(() => {
    if (folderInputRef.current) {
      folderInputRef.current.setAttribute("webkitdirectory", "");
      folderInputRef.current.setAttribute("directory", "");
    }
  }, []);

  const handleFolderSelect: React.ChangeEventHandler<HTMLInputElement> = async (
    event
  ) => {
    const files = Array.from(event.target.files ?? []);
    if (files.length === 0) {
      return;
    }

    setUploading(true);
    setUploadStatus(null);

    try {
      const formData = new FormData();
      files.forEach((file) => {
        const path = (file as File & { webkitRelativePath?: string })
          .webkitRelativePath;
        formData.append("files", file, path || file.name);
      });

      const response = await fetch(`${gatewayUrl}/v1/files/upload`, {
        method: "POST",
        body: formData
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        const message = data.detail || data.error || `Upload failed (${response.status})`;
        throw new Error(message);
      }

      const data = await response.json();
      setUploadedFiles(data.files || []);
      setUploadStatus(`Uploaded ${data.count} file(s).`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Upload failed";
      setUploadStatus(message);
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  };

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed || loading) {
      return;
    }

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setLoading(true);
    setError(null);

    try {
      const payload: Record<string, unknown> = {
        query: trimmed,
        use_rag: useRag,
        top_k: topK,
        stream: false,
        provider,
        model
      };
      if (apiKey) {
        payload.api_key = apiKey;
      }

      const response = await fetch(`${gatewayUrl}/v1/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        let message = `Request failed with status ${response.status}`;
        try {
          const data = await response.json();
          message = data.detail || data.error || message;
        } catch {
          const text = await response.text();
          if (text) {
            message = text;
          }
        }
        throw new Error(message);
      }

      const data = await response.json();
      setMessages((prev) => [...prev, { role: "assistant", content: data.answer }]);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Request failed";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const onKeyDown: React.KeyboardEventHandler<HTMLInputElement> = (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <p className="eyebrow">KnowledgeOps</p>
          <h1>Local-first chat workspace</h1>
          <p className="subhead">
            Gateway {"->"} Inference {"->"} Ollama
          </p>
        </div>
        <div className="status-group">
          <div className="status">MVP</div>
          <a
            className="github-link"
            href="https://github.com/KIMovchanin"
            target="_blank"
            rel="noreferrer"
          >
            GitHub
          </a>
        </div>
      </header>

      {error && <div className="toast">{error}</div>}

      <main className="layout">
        <section className="chat">
          <div className="messages">
            {messages.length === 0 && (
              <div className="empty">Ask a question to get started.</div>
            )}
            {messages.map((message, index) => (
              <div key={index} className={`message ${message.role}`}>
                <span>{message.content}</span>
              </div>
            ))}
            {loading && <div className="message assistant">Thinking...</div>}
            <div ref={endRef} />
          </div>

          <div className="composer">
            <input
              type="text"
              placeholder="Ask KnowledgeOps"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={onKeyDown}
            />
            <button onClick={sendMessage} disabled={loading}>
              {loading ? "Sending" : "Send"}
            </button>
          </div>
        </section>

        <aside className="settings">
          <h2>Settings</h2>
          <div className="field">
            <label htmlFor="provider">Provider</label>
            <select
              id="provider"
              value={provider}
              onChange={(event) => setProvider(event.target.value)}
            >
              <option value="ollama">Ollama (local)</option>
              <option value="openai">OpenAI</option>
              <option value="gemini">Gemini</option>
            </select>
          </div>

          <div className="field">
            <label htmlFor="model">Model</label>
            <select
              id="model"
              value={(MODEL_PRESETS[provider] || []).includes(model) ? model : "__custom__"}
              onChange={(event) => {
                if (event.target.value === "__custom__") {
                  return;
                }
                setModel(event.target.value);
              }}
            >
              {(MODEL_PRESETS[provider] || []).map((preset) => (
                <option key={preset} value={preset}>
                  {preset}
                </option>
              ))}
              <option value="__custom__">Custom</option>
            </select>
            <input
              type="text"
              value={model}
              onChange={(event) => setModel(event.target.value)}
              placeholder="Custom model"
            />
          </div>

          {(provider === "openai" || provider === "gemini") && (
            <div className="field">
              <label htmlFor="apiKey">API Key</label>
              <input
                id="apiKey"
                type="password"
                value={apiKey}
                onChange={(event) => setApiKey(event.target.value)}
                placeholder={`Enter ${provider} key`}
              />
              <div className="hint">Keys are kept in memory and not stored.</div>
            </div>
          )}

          <div className="field">
            <label htmlFor="folder">Folder</label>
            <input
              id="folder"
              ref={folderInputRef}
              type="file"
              multiple
              onChange={handleFolderSelect}
            />
            <div className="hint">
              Upload a folder to prepare files for future RAG indexing.
            </div>
            {uploadStatus && <div className="hint">{uploadStatus}</div>}
            {uploadedFiles.length > 0 && (
              <div className="hint">
                Latest upload: {uploadedFiles.slice(0, 3).join(", ")}
                {uploadedFiles.length > 3 ? "..." : ""}
              </div>
            )}
            {uploading && <div className="hint">Uploading...</div>}
          </div>

          <label className="toggle">
            <input
              type="checkbox"
              checked={useRag}
              onChange={(event) => setUseRag(event.target.checked)}
            />
            <span>Use RAG</span>
          </label>
          <div className="hint">
            Use RAG will use uploaded files once retrieval is enabled.
          </div>

          <div className="slider">
            <label htmlFor="topk">Top K</label>
            <input
              id="topk"
              type="range"
              min={1}
              max={20}
              value={topK}
              onChange={(event) => setTopK(Number(event.target.value))}
            />
            <div className="slider-value">{topK}</div>
          </div>
          <div className="hint">Top K controls how many snippets retrieval will consider.</div>

          <div className="hint">
            Requests are sent to <code>{gatewayUrl}</code>.
          </div>
        </aside>
      </main>
    </div>
  );
}

import { useState, useRef, useEffect } from "react";

export default function ChatInput({ onSend, disabled, isWaiting, onClear }) {
  const [value, setValue] = useState("");
  const textareaRef = useRef(null);

  useEffect(() => {
    if (!disabled) textareaRef.current?.focus();
  }, [disabled]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  return (
    <div className="chat-input-wrapper">
      <span className="input-prompt">{">"}</span>
      <textarea
        ref={textareaRef}
        className="chat-input"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={disabled ? "waiting for response..." : "Ask about skills, experience, projects..."}
        disabled={disabled}
        rows={1}
      />
      <div className="input-actions">
        {onClear && (
          <button className="btn-ghost btn-sm" onClick={onClear}>clear</button>
        )}
        <button
          className={`btn-send ${isWaiting ? "btn-send-waiting" : ""}`}
          onClick={submit}
          disabled={disabled || !value.trim()}
        >
          {isWaiting ? "waiting..." : disabled ? "streaming..." : "send ↵"}
        </button>
      </div>
    </div>
  );
}

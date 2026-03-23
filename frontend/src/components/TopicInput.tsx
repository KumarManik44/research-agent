import { useState } from 'react';

interface TopicInputProps {
  onSubmit: (topic: string) => void;
  disabled?: boolean;
}

export function TopicInput({ onSubmit, disabled }: TopicInputProps) {
  const [topic, setTopic] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const t = topic.trim();
    if (t && !disabled) {
      onSubmit(t);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <input
        type="text"
        value={topic}
        onChange={(e) => setTopic(e.target.value)}
        placeholder="Enter research topic..."
        disabled={disabled}
        className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-4 py-3 text-zinc-100 placeholder-zinc-500 focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500 focus:outline-none transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        autoFocus
      />
      <button
        type="submit"
        disabled={disabled || !topic.trim()}
        className="bg-amber-600 hover:bg-amber-500 text-zinc-950 font-medium px-6 py-3 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed self-center"
      >
        {disabled ? 'Researching...' : 'Search'}
      </button>
    </form>
  );
}

"use client";

import { useState } from "react";
import { Search } from "lucide-react";

const CHAINS = [
  { id: "ethereum", label: "Ethereum" },
  { id: "bsc", label: "BSC" },
  { id: "polygon", label: "Polygon" },
  { id: "arbitrum", label: "Arbitrum" },
  { id: "optimism", label: "Optimism" },
  { id: "base", label: "Base" },
  { id: "avalanche", label: "Avalanche" },
];

interface AddressInputProps {
  onSubmit: (address: string, chain: string) => void;
  loading?: boolean;
}

export function AddressInput({ onSubmit, loading }: AddressInputProps) {
  const [address, setAddress] = useState("");
  const [chain, setChain] = useState("ethereum");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;
    onSubmit(address.trim(), chain);
  };

  const isValid = /^0x[0-9a-fA-F]{40}$/.test(address.trim());

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="flex gap-2">
        <select
          value={chain}
          onChange={(e) => setChain(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-green-500/50"
        >
          {CHAINS.map((c) => (
            <option key={c.id} value={c.id}>
              {c.label}
            </option>
          ))}
        </select>
        <input
          type="text"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          placeholder="0x... contract address"
          className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-sm text-gray-200 placeholder-gray-500 font-mono focus:outline-none focus:ring-2 focus:ring-green-500/50"
        />
      </div>
      <button
        type="submit"
        disabled={!isValid || loading}
        className="w-full flex items-center justify-center gap-2 bg-green-600 hover:bg-green-500 disabled:bg-gray-700 disabled:text-gray-500 text-white font-semibold py-2.5 rounded-lg transition-colors"
      >
        <Search className="w-4 h-4" />
        {loading ? "Fetching..." : "Fetch & Scan"}
      </button>
      {address && !isValid && (
        <p className="text-red-400 text-xs">Enter a valid 0x Ethereum address</p>
      )}
    </form>
  );
}

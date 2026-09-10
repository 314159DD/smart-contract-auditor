"use client";

import { useCallback, useState } from "react";
import { Upload, FileCode, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface ContractUploadProps {
  value: string;
  onChange: (source: string, filename?: string) => void;
}

export function ContractUpload({ value, onChange }: ContractUploadProps) {
  const [dragging, setDragging] = useState(false);
  const [filename, setFilename] = useState<string | null>(null);

  const handleFile = useCallback(
    (file: File) => {
      if (!file.name.endsWith(".sol")) return;
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string;
        onChange(text, file.name);
        setFilename(file.name);
      };
      reader.readAsText(file);
    },
    [onChange]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const onFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const clear = () => {
    onChange("", undefined);
    setFilename(null);
  };

  return (
    <div className="space-y-3">
      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cn(
          "border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors",
          dragging
            ? "border-green-500 bg-green-500/10"
            : "border-gray-700 hover:border-gray-500"
        )}
      >
        <input
          type="file"
          accept=".sol"
          className="hidden"
          id="sol-upload"
          onChange={onFileInput}
        />
        <label htmlFor="sol-upload" className="cursor-pointer">
          {filename ? (
            <div className="flex items-center justify-center gap-2 text-green-400">
              <FileCode className="w-5 h-5" />
              <span className="font-mono text-sm">{filename}</span>
            </div>
          ) : (
            <div className="space-y-1">
              <Upload className="w-6 h-6 text-gray-500 mx-auto" />
              <p className="text-sm text-gray-400">
                Drop a <span className="text-green-400 font-mono">.sol</span> file here
              </p>
              <p className="text-xs text-gray-600">or click to browse</p>
            </div>
          )}
        </label>
      </div>

      {/* Paste textarea */}
      <div className="relative">
        <textarea
          value={value}
          onChange={(e) => { onChange(e.target.value); setFilename(null); }}
          placeholder={`// SPDX-License-Identifier: MIT\npragma solidity ^0.8.0;\n\ncontract MyContract {\n  // Paste your Solidity here...\n}`}
          rows={10}
          className="w-full bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-200 placeholder-gray-600 font-mono focus:outline-none focus:ring-2 focus:ring-green-500/50 resize-none"
          spellCheck={false}
        />
        {value && (
          <button
            onClick={clear}
            className="absolute top-2 right-2 p-1 text-gray-500 hover:text-gray-300 rounded"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}

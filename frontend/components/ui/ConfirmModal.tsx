"use client";

import { useRef } from "react";

import { HiveModalShell } from "@/components/hive/hive-modal-shell";

interface P {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  danger?: boolean;
}

/** Global confirmation dialog — HiveModalShell (Whole-App UI Reorder 11.4). */
export function ConfirmModal({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  onConfirm,
  onCancel,
  danger,
}: P) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  return (
    <HiveModalShell
      open={open}
      onClose={onCancel}
      labelledBy="hive-confirm-title"
      describedBy="hive-confirm-message"
      initialFocusRef={cancelRef}
      panelClassName="bg-[#0d0d2b] border border-[#1a1a3e] rounded-xl p-6 max-w-sm w-full"
    >
      <h3 id="hive-confirm-title" className="text-white font-semibold text-lg mb-2">
        {title}
      </h3>
      <p id="hive-confirm-message" className="text-gray-400 text-sm mb-6">
        {message}
      </p>
      <div className="flex gap-3 justify-end">
        <button
          ref={cancelRef}
          type="button"
          onClick={onCancel}
          className="px-4 py-2 rounded-lg bg-[#1a1a3e] text-gray-300 text-sm hover:bg-[#252550]"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={onConfirm}
          className={`px-4 py-2 rounded-lg text-sm font-medium ${danger ? "bg-[#FF3366] hover:bg-[#cc2952] text-white" : "bg-[#FFB800] hover:bg-[#cc9400] text-black"}`}
        >
          {confirmLabel}
        </button>
      </div>
    </HiveModalShell>
  );
}

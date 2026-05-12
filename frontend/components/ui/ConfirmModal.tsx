"use client";

interface P {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  danger?: boolean;
}

export function ConfirmModal({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  onConfirm,
  onCancel,
  danger,
}: P) {
  if (!open) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4"
      role="presentation"
      onClick={onCancel}
    >
      <div
        role="dialog"
        aria-labelledby="hive-confirm-title"
        aria-describedby="hive-confirm-message"
        className="bg-[#0d0d2b] border border-[#1a1a3e] rounded-xl p-6 max-w-sm w-full"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 id="hive-confirm-title" className="text-white font-semibold text-lg mb-2">
          {title}
        </h3>
        <p id="hive-confirm-message" className="text-gray-400 text-sm mb-6">
          {message}
        </p>
        <div className="flex gap-3 justify-end">
          <button
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
      </div>
    </div>
  );
}

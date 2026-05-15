import { SettingsApiKeysPanel } from "@/components/hive/settings-api-keys-panel";
import { API_KEY_MANAGEMENT_ENABLED } from "@/lib/feature-flags";

export default function ApiKeysSettingsPage() {
  if (!API_KEY_MANAGEMENT_ENABLED) {
    return (
      <div className="rounded-2xl border border-cyan/20 bg-black/30 p-5">
        <p className="font-[family-name:var(--font-poppins)] text-sm text-zinc-300">
          API key management is disabled. Enable <code>NEXT_PUBLIC_API_KEY_MANAGEMENT_ENABLED=true</code> to manage
          scripted credentials.
        </p>
      </div>
    );
  }
  return <SettingsApiKeysPanel />;
}

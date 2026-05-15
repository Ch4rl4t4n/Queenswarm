import { Security2FASettings } from "@/components/hive/security-2fa-settings";
import { SECURITY_2FA_ADVANCED_ENABLED } from "@/lib/feature-flags";

export default function SecuritySettingsPage() {
  if (!SECURITY_2FA_ADVANCED_ENABLED) {
    return (
      <div className="rounded-2xl border border-cyan/20 bg-black/30 p-5">
        <p className="font-[family-name:var(--font-poppins)] text-sm text-zinc-300">
          Advanced 2FA settings are disabled. Enable <code>NEXT_PUBLIC_SECURITY_2FA_ADVANCED_ENABLED=true</code> to
          manage advanced authenticator controls.
        </p>
      </div>
    );
  }
  return <Security2FASettings />;
}

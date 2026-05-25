import React from "react";

const RISK_COLORS = {
  RED:   { header: "bg-red-700",   badge: "bg-red-600 text-white"   },
  AMBER: { header: "bg-amber-600", badge: "bg-amber-500 text-white" },
  GREEN: { header: "bg-teal-700",  badge: "bg-teal-600 text-white"  },
};

export default function PolicyDetail({ policy, onClose }) {
  const cls = policy.classification;
  const orig = policy.original || {};
  const colors = RISK_COLORS[cls] || RISK_COLORS.GREEN;

  const handleDownloadFix = () => {
    const blob = new Blob(
      [JSON.stringify(policy.suggested_policy, null, 2)],
      { type: "application/json" }
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${orig.policy_name || "policy"}-fixed.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-5xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className={`${colors.header} rounded-t-2xl p-5 flex items-center justify-between`}>
          <div>
            <span className="bg-white/20 text-white text-xs font-bold px-2 py-1 rounded-md mr-3">
              {cls}
            </span>
            <span className="text-white font-bold text-lg">{orig.policy_name || "Policy Detail"}</span>
          </div>
          <button onClick={onClose} className="text-white/70 hover:text-white text-2xl leading-none">
            ×
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Meta */}
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: "Attached To", value: orig.attached_to || "—" },
              { label: "Entity Name", value: orig.entity_name || "—" },
              { label: "Last Used",   value: orig.last_used_days_ago === 9999 ? "Never" : `${orig.last_used_days_ago} days ago` },
            ].map((m) => (
              <div key={m.label} className="bg-gray-800 rounded-xl p-4">
                <div className="text-xs text-gray-400 mb-1">{m.label}</div>
                <div className="text-sm font-semibold text-white capitalize">{m.value}</div>
              </div>
            ))}
          </div>

          {/* Risk assessment */}
          <div className="bg-gray-800 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-gray-300 mb-2">Risk Assessment</h3>
            <p className="text-sm text-gray-200 leading-relaxed">{policy.justification}</p>
          </div>

          {/* Risk factors */}
          {policy.risk_factors?.length > 0 && (
            <div className="bg-gray-800 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">Risk Factors</h3>
              <ul className="space-y-2">
                {policy.risk_factors.map((rf, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-200">
                    <span className="text-red-400 mt-0.5">⚠</span>
                    {rf}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Side by side policy diff */}
          <div className="grid grid-cols-2 gap-4">
            {/* Original */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="w-2 h-2 rounded-full bg-red-500"></span>
                <h3 className="text-sm font-semibold text-gray-300">Current Policy (Risky)</h3>
              </div>
              <div className="bg-gray-950 border border-red-900/50 rounded-xl p-4 overflow-auto max-h-80">
                <pre className="text-xs text-red-200 whitespace-pre-wrap">
                  {JSON.stringify(orig.document, null, 2)}
                </pre>
              </div>
            </div>

            {/* Suggested */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="w-2 h-2 rounded-full bg-teal-500"></span>
                <h3 className="text-sm font-semibold text-gray-300">Suggested Replacement (Safe)</h3>
              </div>
              <div className="bg-gray-950 border border-teal-900/50 rounded-xl p-4 overflow-auto max-h-80">
                <pre className="text-xs text-teal-200 whitespace-pre-wrap">
                  {JSON.stringify(policy.suggested_policy, null, 2)}
                </pre>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              onClick={handleDownloadFix}
              className="flex items-center gap-2 bg-teal-600 hover:bg-teal-500 text-white px-5 py-2.5 rounded-lg text-sm font-semibold transition-all"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download Fixed Policy JSON
            </button>
            <button
              onClick={onClose}
              className="bg-gray-800 hover:bg-gray-700 text-gray-300 px-5 py-2.5 rounded-lg text-sm font-semibold transition-all"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

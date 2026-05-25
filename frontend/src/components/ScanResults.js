import React, { useState } from "react";

const STATUS_LABELS = {
  triggered:  { label: "Triggered",   color: "text-blue-400",  bg: "bg-blue-900/30"  },
  collecting: { label: "Collecting IAM Policies...", color: "text-yellow-400", bg: "bg-yellow-900/30" },
  analysing:  { label: "AI Analysing...", color: "text-purple-400", bg: "bg-purple-900/30" },
  complete:   { label: "Complete",    color: "text-teal-400",  bg: "bg-teal-900/30"  },
  error:      { label: "Error",       color: "text-red-400",   bg: "bg-red-900/30"   },
};

const RISK_STYLES = {
  RED:   { bg: "bg-red-900/30",   border: "border-red-700",   badge: "bg-red-600 text-white",   dot: "bg-red-500"   },
  AMBER: { bg: "bg-amber-900/20", border: "border-amber-700", badge: "bg-amber-500 text-white", dot: "bg-amber-500" },
  GREEN: { bg: "bg-teal-900/20",  border: "border-teal-700",  badge: "bg-teal-600 text-white",  dot: "bg-teal-500"  },
};

export default function ScanResults({ scanData, onSelectPolicy, onDownload }) {
  const [filter, setFilter] = useState("ALL");
  const [search, setSearch] = useState("");

  const status = STATUS_LABELS[scanData.status] || STATUS_LABELS.triggered;
  const isComplete = scanData.status === "complete";
  const policies = scanData.policies || [];

  const filtered = policies.filter((p) => {
    const matchFilter = filter === "ALL" || p.classification === filter;
    const matchSearch =
      search === "" ||
      p.original?.policy_name?.toLowerCase().includes(search.toLowerCase()) ||
      p.original?.entity_name?.toLowerCase().includes(search.toLowerCase());
    return matchFilter && matchSearch;
  });

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-bold text-white">
            {scanData.account_name || "Scan Results"}
          </h2>
          <div className={`flex items-center gap-2 mt-1 px-3 py-1 rounded-full w-fit text-xs font-medium ${status.bg} ${status.color}`}>
            {!isComplete && scanData.status !== "error" && (
              <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
              </svg>
            )}
            {status.label}
          </div>
        </div>

        {isComplete && (
          <button
            onClick={onDownload}
            className="flex items-center gap-2 bg-teal-600 hover:bg-teal-500 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-all"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download PDF Report
          </button>
        )}
      </div>

      {/* Summary cards */}
      {isComplete && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[
            { label: "Total Scanned", value: scanData.total, color: "text-white", bg: "bg-gray-800" },
            { label: "🔴 Critical (RED)", value: scanData.red, color: "text-red-400", bg: "bg-red-900/20 border border-red-800" },
            { label: "🟡 Moderate (AMBER)", value: scanData.amber, color: "text-amber-400", bg: "bg-amber-900/20 border border-amber-800" },
            { label: "🟢 Safe (GREEN)", value: scanData.green, color: "text-teal-400", bg: "bg-teal-900/20 border border-teal-800" },
          ].map((card) => (
            <div key={card.label} className={`rounded-xl p-4 ${card.bg}`}>
              <div className={`text-3xl font-bold ${card.color}`}>{card.value}</div>
              <div className="text-xs text-gray-400 mt-1">{card.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      {isComplete && policies.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <input
            type="text"
            placeholder="Search policy or entity name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-2 w-64 outline-none focus:border-teal-500"
          />
          <div className="flex gap-2">
            {["ALL", "RED", "AMBER", "GREEN"].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  filter === f
                    ? f === "RED" ? "bg-red-600 text-white"
                    : f === "AMBER" ? "bg-amber-500 text-white"
                    : f === "GREEN" ? "bg-teal-600 text-white"
                    : "bg-teal-600 text-white"
                    : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
          <span className="text-xs text-gray-500">{filtered.length} shown</span>
        </div>
      )}

      {/* Policy table */}
      {isComplete && filtered.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-gray-800">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-800 text-gray-400 text-xs uppercase tracking-wider">
                <th className="px-4 py-3 text-left">Risk</th>
                <th className="px-4 py-3 text-left">Policy Name</th>
                <th className="px-4 py-3 text-left">Attached To</th>
                <th className="px-4 py-3 text-left">Entity</th>
                <th className="px-4 py-3 text-left">Last Used</th>
                <th className="px-4 py-3 text-left">Justification</th>
                <th className="px-4 py-3 text-left">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {filtered.map((policy, i) => {
                const cls = policy.classification;
                const orig = policy.original || {};
                const style = RISK_STYLES[cls] || RISK_STYLES.GREEN;

                return (
                  <tr key={i} className={`${style.bg} hover:bg-gray-800/50 transition-colors`}>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded-md text-xs font-bold ${style.badge}`}>
                        {cls}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-200 max-w-[200px] truncate">
                      {orig.policy_name || "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs capitalize">
                      {orig.attached_to || "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-300 text-xs max-w-[150px] truncate">
                      {orig.entity_name || "—"}
                    </td>
                    <td className="px-4 py-3 text-xs">
                      {orig.last_used_days_ago === 9999 ? (
                        <span className="text-red-400">Never</span>
                      ) : (
                        <span className={orig.last_used_days_ago > 90 ? "text-red-400" : orig.last_used_days_ago > 30 ? "text-amber-400" : "text-teal-400"}>
                          {orig.last_used_days_ago}d ago
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs max-w-[250px]">
                      <span className="line-clamp-2">{policy.justification}</span>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => onSelectPolicy(policy)}
                        className="text-teal-400 hover:text-teal-300 text-xs font-medium underline underline-offset-2"
                      >
                        View Fix →
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Empty state */}
      {isComplete && policies.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No policies found in this account.
        </div>
      )}

      {/* Error state */}
      {scanData.status === "error" && (
        <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 text-red-300 text-sm">
          <strong>Scan failed:</strong> {scanData.error || "Unknown error"}
        </div>
      )}
    </div>
  );
}

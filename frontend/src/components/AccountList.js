import React from "react";

const ACCOUNT_COLORS = [
  "bg-purple-600",
  "bg-blue-600",
  "bg-indigo-600",
  "bg-cyan-600",
];

export default function AccountList({ accounts, onScan, scanning, activeAccountId }) {
  return (
    <div className="mb-8">
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
        AWS Accounts ({accounts.length})
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {accounts.map((account, i) => {
          const isActive = activeAccountId === account.account_id;
          const isScanning = scanning && isActive;

          return (
            <div
              key={account.account_id}
              className={`bg-gray-900 border rounded-xl p-5 flex flex-col gap-4 transition-all ${
                isActive
                  ? "border-teal-500 shadow-lg shadow-teal-900/30"
                  : "border-gray-800 hover:border-gray-600"
              }`}
            >
              {/* Account icon + name */}
              <div className="flex items-center gap-3">
                <div
                  className={`w-10 h-10 rounded-lg ${ACCOUNT_COLORS[i % ACCOUNT_COLORS.length]} flex items-center justify-center text-white font-bold text-sm flex-shrink-0`}
                >
                  {account.account_name.charAt(0)}
                </div>
                <div className="min-w-0">
                  <div className="font-semibold text-white text-sm truncate">
                    {account.account_name}
                  </div>
                  <div className="text-xs text-gray-500 font-mono">
                    {account.account_id}
                  </div>
                </div>
              </div>

              {/* Badge */}
              {account.is_master && (
                <span className="self-start px-2 py-0.5 bg-purple-900 text-purple-300 text-xs rounded-full font-medium">
                  Master
                </span>
              )}

              {/* Scan button */}
              <button
                onClick={() => onScan(account.account_id)}
                disabled={scanning}
                className={`w-full py-2 rounded-lg text-sm font-semibold transition-all ${
                  isScanning
                    ? "bg-teal-700 text-teal-200 cursor-wait"
                    : scanning
                    ? "bg-gray-800 text-gray-500 cursor-not-allowed"
                    : "bg-teal-600 hover:bg-teal-500 text-white"
                }`}
              >
                {isScanning ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                    </svg>
                    Scanning...
                  </span>
                ) : (
                  "Scan"
                )}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

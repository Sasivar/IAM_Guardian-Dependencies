import React, { useState, useEffect } from "react";
import AccountList from "./components/AccountList";
import ScanResults from "./components/ScanResults";
import PolicyDetail from "./components/PolicyDetail";

const API = "http://52.203.149.106:8000";

export default function App() {
  const [accounts, setAccounts] = useState([]);
  const [activeScan, setActiveScan] = useState(null);
  const [scanData, setScanData] = useState(null);
  const [selectedPolicy, setSelectedPolicy] = useState(null);
  const [polling, setPolling] = useState(false);

  // Load accounts on mount
  useEffect(() => {
    fetch(`${API}/accounts`)
      .then((r) => r.json())
      .then(setAccounts)
      .catch((e) => console.error("Failed to load accounts:", e));
  }, []);

  // Poll for scan results
  useEffect(() => {
    if (!activeScan || !polling) return;

    const interval = setInterval(() => {
      fetch(`${API}/scan/${activeScan}`)
        .then((r) => r.json())
        .then((data) => {
          setScanData(data);
          if (data.status === "complete" || data.status === "error") {
            setPolling(false);
            clearInterval(interval);
          }
        })
        .catch(console.error);
    }, 4000);

    return () => clearInterval(interval);
  }, [activeScan, polling]);

  const handleScan = async (accountId) => {
    setScanData(null);
    setSelectedPolicy(null);

    const res = await fetch(`${API}/scan/${accountId}`, { method: "POST" });
    const data = await res.json();
    setActiveScan(data.scan_id);
    setPolling(true);
    setScanData({ status: "triggered", account_id: accountId });
  };

  const handleDownload = () => {
    if (!activeScan) return;
    window.open(`${API}/scan/${activeScan}/report`, "_blank");
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 font-sans">
      {/* Top Nav */}
      <nav className="bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center gap-3">
        <div className="w-8 h-8 bg-teal-500 rounded-lg flex items-center justify-center">
          <span className="text-white font-bold text-sm">IG</span>
        </div>
        <span className="text-xl font-bold text-white">IAM Guardian</span>
        <span className="ml-2 px-2 py-0.5 bg-teal-900 text-teal-300 text-xs rounded-full font-medium">
          OUTINNOVATE
        </span>
      </nav>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Page title */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white">AWS Account Scanner</h1>
          <p className="text-gray-400 mt-1">
            Select an account and click Scan to analyse IAM policies for security risks.
          </p>
        </div>

        {/* Account list */}
        <AccountList
          accounts={accounts}
          onScan={handleScan}
          scanning={polling}
          activeAccountId={scanData?.account_id}
        />

        {/* Scan status / results */}
        {scanData && (
          <ScanResults
            scanData={scanData}
            onSelectPolicy={setSelectedPolicy}
            onDownload={handleDownload}
          />
        )}

        {/* Policy detail modal */}
        {selectedPolicy && (
          <PolicyDetail
            policy={selectedPolicy}
            onClose={() => setSelectedPolicy(null)}
          />
        )}
      </div>
    </div>
  );
}

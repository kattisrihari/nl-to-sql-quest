import React, { useState } from 'react';
import * as XLSX from 'xlsx';

export interface SearchResponse {
  summary: string;
  sql_query?: string | null;
  data?: Record<string, any>[];
  total_rows?: number;
}

const SearchIcon = () => (
  <svg className="w-5 h-5 text-[#66A3BF]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
    <circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" />
  </svg>
);

const SparklesIcon = () => (
  <svg className="w-5 h-5 text-[#66A3BF]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
    <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3z" />
  </svg>
);

const TerminalIcon = () => (
  <svg className="w-4 h-4 text-[#66A3BF]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
    <polyline points="4 17 10 11 4 5" /><line x1="12" y1="19" x2="20" y2="19" />
  </svg>
);

const TableIcon = () => (
  <svg className="w-5 h-5 text-[#66A3BF]" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
    <rect width="18" height="18" x="3" y="3" rx="2" /><path d="M3 9h18M3 15h18M9 3v18" />
  </svg>
);

const ChevronDownIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
    <path d="m6 9 6 6 6-6" />
  </svg>
);

const ChevronUpIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
    <path d="m18 15-6-6-6 6" />
  </svg>
);

const DownloadIcon = () => (
  <svg className="w-3 h-3" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="7 10 12 15 17 10" />
    <line x1="12" y1="15" x2="12" y2="3" />
  </svg>
);

export default function App() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSql, setShowSql] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showTable, setShowTable] = useState(false);
  const [execTime, setExecTime] = useState<number | null>(null);
  const [dark, setDark] = useState(true);

  const t = {
    page:        dark ? 'bg-[#0f172a]'    : 'bg-[#F2EFE7]',
    card:        dark ? 'bg-[#1e293b]'    : 'bg-white',
    border:      dark ? 'border-slate-600': 'border-[#C8DFDB]',
    input:       dark ? 'bg-[#1e293b] text-slate-100 placeholder-slate-500' : 'bg-white text-gray-800 placeholder-gray-400',
    collapseBtn: dark ? 'bg-[#0f172a] hover:bg-slate-800' : 'bg-gray-50 hover:bg-gray-100',
    chevron:     dark ? 'text-slate-400'  : 'text-gray-500',
    summaryText: dark ? 'text-slate-300'  : 'text-gray-700',
    subtitle:    dark ? 'text-slate-400'  : 'text-gray-600',
    tableHead:   dark ? 'bg-slate-800'    : 'bg-[#F2EFE7]',
    tableBody:   dark ? 'bg-[#1e293b] divide-slate-700' : 'bg-white divide-[#C8DFDB]',
    tableRow:    dark ? 'hover:bg-slate-700' : 'hover:bg-gray-50',
    tableCell:   dark ? 'text-slate-300'  : 'text-gray-600',
    tableDivide: dark ? 'divide-slate-700': 'divide-[#C8DFDB]',
    error:       dark ? 'bg-red-950 border-red-800 text-red-400' : 'bg-red-50 border-red-200 text-red-700',
    toggleBtn:   dark ? 'border-slate-500 text-slate-400 hover:bg-slate-700' : 'border-gray-400 text-gray-500 hover:bg-gray-200',
    badge:       dark ? 'bg-slate-700 text-slate-300' : 'bg-amber-50 text-amber-700 border border-amber-200',
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setExecTime(null);
    const startTime = Date.now();
    try {
      const response = await fetch('http://127.0.0.1:8000/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      if (!response.ok) throw new Error(`Server returned status: ${response.status}`);
      const data: SearchResponse = await response.json();
      setExecTime((Date.now() - startTime) / 1000);
      setResult(data);
      setShowTable(false);
      setShowSql(false);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch query results');
    } finally {
      setLoading(false);
    }
  };

  const copySqlToClipboard = () => {
    if (result?.sql_query) {
      navigator.clipboard.writeText(result.sql_query);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const downloadCsv = () => {
    if (!result?.data || result.data.length === 0) return;
    const headers = Object.keys(result.data[0]);
    const rows = result.data.map(row => headers.map(h => JSON.stringify(row[h] ?? '')).join(','));
    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'query_results.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadXlsx = () => {
    if (!result?.data || result.data.length === 0) return;
    const ws = XLSX.utils.json_to_sheet(result.data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Query Results');
    XLSX.writeFile(wb, 'query_results.xlsx');
  };

  const isTruncated = result?.total_rows !== undefined && result.data !== undefined && result.total_rows > 50;

  return (
    <div className={`min-h-screen ${t.page} py-10 px-4 sm:px-6 lg:px-8 transition-colors duration-300`}>
      <div className="max-w-4xl mx-auto space-y-6">

        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold tracking-tight text-[#3368A0]">
            AI summarized Database results in an instant
          </h1>
          <h2 className={t.subtitle}>Your go to NL-to-SQL assistant, Ask away:)</h2>
          <p className={t.subtitle}>
            Ask natural language questions to query your database and see execution details, SQL query and resultant table.
          </p>
          <button
            onClick={() => setDark(!dark)}
            className={`mt-2 px-4 py-1.5 rounded-full text-xs font-medium border transition-colors ${t.toggleBtn}`}
          >
            {dark ? '☀️ Light Mode' : '🌙 Dark Mode'}
          </button>
        </div>

        {/* Search Bar */}
        <form onSubmit={handleSearch} className="relative shadow-sm rounded-xl overflow-hidden">
          <div className={`flex items-center border focus-within:ring-2 focus-within:ring-[#3368A0] ${t.card} ${t.border}`}>
            <div className="pl-4"><SearchIcon /></div>
            <input
              type="text"
              className={`w-full py-3.5 px-3 focus:outline-none bg-transparent text-sm sm:text-base ${t.input}`}
              placeholder="e.g., What is the average booking value by hotel star rating?"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <button
              type="submit"
              disabled={loading}
              className="bg-[#3368A0] hover:bg-[#285584] text-white font-medium px-6 py-3.5 transition-colors duration-150 disabled:opacity-50 text-sm sm:text-base"
            >
              {loading ? 'Analyzing...' : 'Search'}
            </button>
          </div>
        </form>

        {/* Error */}
        {error && (
          <div className={`p-4 border rounded-lg text-sm ${t.error}`}>{error}</div>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-4">

            {/* AI Summary */}
            <div className={`${t.card} border ${t.border} rounded-xl p-5 shadow-sm`}>
              <div className="flex items-center justify-between mb-2.5">
                <div className="flex items-center gap-2 text-[#3368A0] font-semibold">
                  <SparklesIcon />
                  <h2>AI Summary</h2>
                </div>
                {execTime !== null && execTime > 0 && (
                  <span className={`text-xs px-2 py-1 rounded-full ${t.badge}`}>
                    ⏱ {execTime.toFixed(2)}s
                  </span>
                )}
              </div>
              <p className={`leading-relaxed whitespace-pre-wrap text-sm sm:text-base ${t.summaryText}`}>
                {result.summary}
              </p>
            </div>

            {/* Side by side: Table left, SQL right */}
            <div className="flex flex-col lg:flex-row gap-4">

              {/* Data Table — collapsible, left */}
              {result.data && result.data.length > 0 && (
                <div className={`flex-1 border ${t.border} rounded-xl overflow-hidden ${t.card} shadow-sm`}>
                  <button
                    type="button"
                    onClick={() => setShowTable(!showTable)}
                    className={`w-full flex items-center justify-between px-5 py-3.5 transition-colors text-left ${t.collapseBtn}`}
                  >
                    <div className="flex items-center gap-2 text-[#3368A0] font-medium text-sm">
                      <TableIcon />
                      <span>
                        Data Preview ({result.data.length}
                        {isTruncated ? ` of ${result.total_rows} records — showing first 50` : ' records'})
                      </span>
                    </div>
                    <div className={t.chevron}>
                      {showTable ? <ChevronUpIcon /> : <ChevronDownIcon />}
                    </div>
                  </button>

                  {showTable && (
                    <>
                      {/* Truncation warning + download buttons */}
                      {isTruncated && (
                        <div className={`flex items-center justify-between px-5 py-2 text-xs border-b ${t.border} ${t.badge}`}>
                          <span>⚠️ Showing 50 of {result.total_rows} rows</span>
                          <div className="flex gap-2">
                            <button
                              onClick={downloadCsv}
                              className="flex items-center gap-1 px-3 py-1 rounded bg-[#3368A0] text-white hover:bg-[#285584] transition-colors"
                            >
                              <DownloadIcon />
                              CSV
                            </button>
                            <button
                              onClick={downloadXlsx}
                              className="flex items-center gap-1 px-3 py-1 rounded bg-emerald-600 text-white hover:bg-emerald-700 transition-colors"
                            >
                              <DownloadIcon />
                              XLSX
                            </button>
                          </div>
                        </div>
                      )}

                      <div className={`overflow-x-auto border-t ${t.border}`}>
                        <table className={`min-w-full text-left text-sm divide-y ${t.tableDivide}`}>
                          <thead className={t.tableHead}>
                            <tr>
                              {Object.keys(result.data[0]).map((key) => (
                                <th key={key} className="px-4 py-2.5 font-semibold text-[#3368A0] whitespace-nowrap">
                                  {key}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className={`divide-y ${t.tableBody}`}>
                            {result.data.map((row, idx) => (
                              <tr key={idx} className={t.tableRow}>
                                {Object.values(row).map((val: any, cellIdx) => (
                                  <td key={cellIdx} className={`px-4 py-2 whitespace-nowrap ${t.tableCell}`}>
                                    {typeof val === 'object' && val !== null ? JSON.stringify(val) : String(val)}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* SQL Query — collapsible, right */}
              {result.sql_query && (
                <div className={`flex-1 border ${t.border} rounded-xl overflow-hidden ${t.card} shadow-sm`}>
                  <button
                    type="button"
                    onClick={() => setShowSql(!showSql)}
                    className={`w-full flex items-center justify-between px-5 py-3.5 transition-colors text-left ${t.collapseBtn}`}
                  >
                    <div className="flex items-center gap-2 text-[#3368A0] font-medium text-sm">
                      <TerminalIcon />
                      <span>Generated SQL Query</span>
                    </div>
                    <div className={t.chevron}>
                      {showSql ? <ChevronUpIcon /> : <ChevronDownIcon />}
                    </div>
                  </button>

                  {showSql && (
                    <div className="relative p-4 bg-gray-900 text-gray-100 h-full">
                      <button
                        onClick={copySqlToClipboard}
                        className="absolute top-3 right-3 px-2 py-1 rounded bg-gray-800 hover:bg-gray-700 text-xs text-gray-300 transition-colors"
                      >
                        {copied ? 'Copied!' : 'Copy'}
                      </button>
                      <pre className="text-xs sm:text-sm font-mono overflow-x-auto pr-16 py-1 leading-relaxed text-emerald-400">
                        <code>{result.sql_query}</code>
                      </pre>
                    </div>
                  )}
                </div>
              )}

            </div>
          </div>
        )}

      </div>
    </div>
  );
}

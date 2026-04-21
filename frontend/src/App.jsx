import { useState, useRef, useEffect } from "react"
import axios from "axios"
import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from "recharts"
import { themes, getTheme, saveTheme, loadTheme } from "./themes"

const BACKEND = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"

const METRICS = [
  { value: "Rainfall (mm) Total", label: "Rainfall (mm)" },
  { value: "Total Geographical Area (ha) Total", label: "Total Geographical Area (ha)" },
  { value: "Ground Water Recharge (ham) Total", label: "Ground Water Recharge (ham)" },
  { value: "Annual Ground water Recharge (ham) Total", label: "Annual Ground water Recharge (ham)" },
  { value: "Annual Extractable Ground water Resource (ham) Total", label: "Annual Extractable Ground water Resource (ham)" },
  { value: "Ground Water Extraction for all uses (ha.m) Total", label: "Ground Water Extraction (ha.m)" },
  { value: "Stage of Ground Water Extraction (%) Total", label: "Stage of Ground Water Extraction (%)" },
  { value: "Environmental Flows (ham) Total", label: "Environmental Flows (ham)" },
  { value: "Net Annual Ground Water Availability for Future Use (ham) Total", label: "Net Annual GW Availability (ham)" },
  { value: "Total Ground Water Availability in the area (ham) Fresh", label: "Total Ground Water Availability (ham)" },
]

const STATES = [
  "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
  "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
  "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
  "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
  "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
  "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi", "Jammu and Kashmir",
  "Ladakh", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
  "Lakshadweep", "Puducherry", "Andaman and Nicobar Islands"
]

const YEARS = ["2016_17", "2019_20", "2021_22", "2022_23", "2023_24", "2024_25"]

const QUICK_QUERIES = [
  "Which state has the highest ground water availability?",
  "Show rainfall data for Punjab in 2022-23",
  "Top 5 districts by ground water recharge",
  "What is the stage of ground water extraction in Punjab?",
]

let _id = 0
const uid = () => `chat_${++_id}_${Date.now()}`

// Multi-Select Dropdown Component
function MultiSelectDropdown({ options, selected, onChange, placeholder, theme, searchable = true }) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchTerm, setSearchTerm] = useState("")
  const dropdownRef = useRef(null)
  const colors = theme.colors

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false)
        setSearchTerm("")
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const filteredOptions = searchable
    ? options.filter(opt => opt.toLowerCase().includes(searchTerm.toLowerCase()))
    : options

  const toggleOption = (option) => {
    if (selected.includes(option)) {
      onChange(selected.filter(s => s !== option))
    } else {
      onChange([...selected, option])
    }
  }

  const displayText = selected.length === 0
    ? placeholder
    : selected.length === 1
    ? selected[0]
    : `${selected.length} selected`

  return (
    <div ref={dropdownRef} className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full px-3 py-2 border rounded-lg ${colors.input} ${colors.inputFocus} text-sm text-left flex items-center justify-between transition-colors`}
      >
        <span className={selected.length === 0 ? colors.textTertiary : colors.text}>
          {displayText}
        </span>
        <svg
          className={`w-4 h-4 ${colors.textSecondary} transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className={`absolute z-50 w-full mt-1 ${colors.panel} border ${colors.border} rounded-lg shadow-xl max-h-64 overflow-hidden`}>
          {searchable && (
            <div className="p-2 border-b">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search..."
                className={`w-full px-3 py-1.5 border rounded ${colors.input} text-sm`}
                onClick={(e) => e.stopPropagation()}
              />
            </div>
          )}
          <div className="overflow-y-auto max-h-52">
            {filteredOptions.length === 0 ? (
              <div className={`p-3 text-sm ${colors.textTertiary} text-center`}>No options found</div>
            ) : (
              filteredOptions.map(option => (
                <label
                  key={option}
                  className={`flex items-center gap-2 px-3 py-2 hover:${colors.listItem} cursor-pointer transition-colors`}
                  onClick={(e) => e.stopPropagation()}
                >
                  <input
                    type="checkbox"
                    checked={selected.includes(option)}
                    onChange={() => toggleOption(option)}
                    className="w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                  />
                  <span className={`text-sm ${colors.text}`}>{option}</span>
                </label>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function parseAnswer(text) {
  const numberedList = text.match(/\d+\.\s+.+/g)
  if (numberedList && numberedList.length >= 2) {
    const intro = text.split(/1\.\s/)[0].trim()
    const items = numberedList.map(line => {
      const match = line.match(/\d+\.\s+(.+?):\s*(.+)/)
      if (match) return { label: match[1].trim(), value: match[2].trim() }
      return { label: line.replace(/^\d+\.\s*/, '').trim(), value: null }
    })
    return { type: "list", intro, items }
  }
  return { type: "text", content: text }
}

function extractChartData(items) {
  return items
    .map(item => {
      if (!item.value) return null
      const numMatch = item.value.match(/[\d,]+\.?\d*/)
      if (!numMatch) return null
      const num = parseFloat(numMatch[0].replace(/,/g, ''))
      if (isNaN(num)) return null
      return { name: item.label.length > 14 ? item.label.slice(0, 14) + "…" : item.label, value: num, full: item.label }
    })
    .filter(Boolean)
}

const CHART_COLORS = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316", "#06b6d4"]

function CustomTooltip({ active, payload, theme }) {
  if (!active || !payload?.length) return null
  const colors = theme.colors
  return (
    <div className={`${colors.panel} ${colors.border} border rounded-lg shadow-lg p-3`}>
      <div className={`font-semibold ${colors.text} mb-1`}>{payload[0].payload.full || payload[0].payload.name}</div>
      <div className="text-blue-600 font-medium">{payload[0].value?.toLocaleString()}</div>
    </div>
  )
}

function DataChart({ items, theme }) {
  const data = extractChartData(items)
  if (!data || data.length < 2) return null
  const isTimeSeries = items.some(i => /\d{4}/.test(i.label))
  const colors = theme.colors

  return (
    <div className={`mt-4 p-4 ${colors.chart} rounded-xl border`}>
      <div className={`text-xs font-semibold ${colors.textTertiary} uppercase tracking-wide mb-3`}>
        {isTimeSeries ? "Trend" : "Comparison"} Chart
      </div>
      <ResponsiveContainer width="100%" height={200}>
        {isTimeSeries ? (
          <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="name" tick={{ fill: "#6b7280", fontSize: 11 }} />
            <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} width={50} />
            <Tooltip content={<CustomTooltip theme={theme} />} />
            <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2.5} dot={{ fill: "#3b82f6", r: 4 }} />
          </LineChart>
        ) : (
          <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
            <XAxis dataKey="name" tick={{ fill: "#6b7280", fontSize: 11 }} />
            <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} width={50} />
            <Tooltip content={<CustomTooltip theme={theme} />} />
            <Bar dataKey="value" radius={[6, 6, 0, 0]}>
              {data.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
            </Bar>
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}

function RankedList({ intro, items, theme }) {
  const chartData = extractChartData(items)
  const showChart = chartData && chartData.length >= 2
  const colors = theme.colors

  return (
    <div>
      {intro && <p className={`text-sm ${colors.textSecondary} mb-3`}>{intro}</p>}
      <div className="space-y-2">
        {items.map((item, i) => {
          const medals = ["#f59e0b", "#94a3b8", "#cd7c2f"]
          const badgeColor = i < 3 ? medals[i] : "#3b82f6"
          return (
            <div key={i} className={`flex items-center gap-3 p-3 ${colors.listItem} border rounded-lg transition-colors`}>
              <div className="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
                   style={{ backgroundColor: badgeColor, boxShadow: i < 3 ? `0 0 10px ${badgeColor}66` : 'none' }}>
                {i + 1}
              </div>
              <div className="flex-1 min-w-0">
                <div className={`font-medium ${colors.text} truncate`}>{item.label}</div>
                {item.value && <div className="text-sm text-blue-600">{item.value}</div>}
              </div>
            </div>
          )
        })}
      </div>
      {showChart && <DataChart items={items} theme={theme} />}
    </div>
  )
}

function BotMessage({ text, theme }) {
  const parsed = parseAnswer(text)
  return (
    <div>
      {parsed.type === "list"
        ? <RankedList intro={parsed.intro} items={parsed.items} theme={theme} />
        : <span className="whitespace-pre-wrap leading-relaxed">{text}</span>
      }
    </div>
  )
}

function DataTable({ data, metric, theme }) {
  if (!data || data.length === 0) return null
  const colors = theme.colors
  
  return (
    <div className={`mt-4 ${colors.panel} border ${colors.border} rounded-xl overflow-hidden`}>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className={`${colors.listItem} border-b ${colors.border}`}>
            <tr>
              <th className={`px-4 py-3 text-left text-xs font-semibold ${colors.text} uppercase tracking-wider`}>State</th>
              {data[0].year && <th className={`px-4 py-3 text-left text-xs font-semibold ${colors.text} uppercase tracking-wider`}>Year</th>}
              <th className={`px-4 py-3 text-right text-xs font-semibold ${colors.text} uppercase tracking-wider`}>Value</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {data.map((row, i) => (
              <tr key={i} className="hover:bg-opacity-50 hover:bg-gray-50 transition-colors">
                <td className={`px-4 py-3 text-sm ${colors.text}`}>{row.state}</td>
                {row.year && <td className={`px-4 py-3 text-sm ${colors.textSecondary}`}>{row.year.replace('_', '-')}</td>}
                <td className={`px-4 py-3 text-sm font-medium ${colors.text} text-right`}>{row.value.toLocaleString(undefined, {maximumFractionDigits: 2})}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function App() {
  const [messages, setMessages] = useState([])
  const [question, setQuestion] = useState("")
  const [loading, setLoading] = useState(false)
  const [filtersPanelOpen, setFiltersPanelOpen] = useState(true)
  const [currentTheme, setCurrentTheme] = useState(loadTheme())
  
  const [selectedMetric, setSelectedMetric] = useState("")
  const [selectedStates, setSelectedStates] = useState([])
  const [selectedYears, setSelectedYears] = useState([])
  
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  const theme = getTheme(currentTheme)
  const colors = theme.colors

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = "46px"
    el.style.height = Math.min(el.scrollHeight, 120) + "px"
  }, [question])

  const changeTheme = (themeName) => {
    setCurrentTheme(themeName)
    saveTheme(themeName)
  }

  const send = async (q) => {
    const text = (q || question).trim()
    if (!text || loading) return

    const userMsg = { role: "user", text, id: uid() }
    setMessages(prev => [...prev, userMsg])
    setQuestion("")
    setLoading(true)

    try {
      const res = await axios.post(`${BACKEND}/chat`, { question: text })
      const botMsg = { role: "bot", text: res.data.answer, id: uid() }
      setMessages(prev => [...prev, botMsg])
    } catch {
      const errMsg = { role: "bot", text: "⚠️ Could not reach the backend. Make sure the server is running on port 8000.", id: uid() }
      setMessages(prev => [...prev, errMsg])
    } finally {
      setLoading(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send() }
  }

  const runFilterQuery = async () => {
    if (!selectedMetric) {
      alert("Please select a metric")
      return
    }
    
    const userMsg = {
      role: "user",
      text: `Show ${selectedMetric}${selectedStates.length > 0 ? ` for ${selectedStates.join(", ")}` : ""}${selectedYears.length > 0 ? ` in ${selectedYears.map(y => y.replace("_", "-")).join(", ")}` : ""}`,
      id: uid()
    }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      const res = await axios.post(`${BACKEND}/filter_query`, {
        metric: selectedMetric,
        states: selectedStates,
        years: selectedYears
      })
      
      if (res.data.success && res.data.data.length > 0) {
        const botMsg = {
          role: "bot",
          text: res.data.message,
          id: uid(),
          data: res.data.data,
          metric: res.data.metric,
          queryType: res.data.query_type
        }
        setMessages(prev => [...prev, botMsg])
      } else {
        const botMsg = {
          role: "bot",
          text: res.data.message || "No data available for the selected query",
          id: uid()
        }
        setMessages(prev => [...prev, botMsg])
      }
    } catch (error) {
      const errMsg = {
        role: "bot",
        text: "⚠️ Error executing query. Please try again.",
        id: uid()
      }
      setMessages(prev => [...prev, errMsg])
    } finally {
      setLoading(false)
    }
  }

  const resetFilters = () => {
    setSelectedMetric("")
    setSelectedStates([])
    setSelectedYears([])
  }

  const resetMetric = () => setSelectedMetric("")
  const resetStates = () => setSelectedStates([])
  const resetYears = () => setSelectedYears([])

  return (
    <div className={`flex h-screen bg-gradient-to-br ${colors.bg} transition-colors duration-300`}>
      {/* Filter Panel */}
      <div className={`${filtersPanelOpen ? 'w-80' : 'w-0'} transition-all duration-300 ${colors.panel} border-r ${colors.border} flex flex-col overflow-hidden`}>
        <div className={`p-6 border-b ${colors.border}`}>
          <div className="flex items-center gap-3 mb-2">
            <div className={`w-10 h-10 rounded-xl ${colors.avatar} flex items-center justify-center`}>
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
              </svg>
            </div>
            <div>
              <h2 className={`text-lg font-bold ${colors.text}`}>Filters</h2>
              <p className={`text-xs ${colors.textTertiary}`}>Explore data visually</p>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Metric Selector */}
          <div>
            <label className={`block text-sm font-semibold ${colors.text} mb-2`}>Metric</label>
            <div className="flex gap-2">
              <select
                value={selectedMetric}
                onChange={(e) => setSelectedMetric(e.target.value)}
                className={`flex-1 px-3 py-2 border rounded-lg ${colors.input} ${colors.inputFocus} text-sm transition-colors`}
              >
                <option value="">Select metric...</option>
                {METRICS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
              <button
                onClick={resetMetric}
                disabled={!selectedMetric}
                className={`px-3 py-2 border rounded-lg text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${colors.buttonSecondary}`}
                title="Reset metric"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* State Selector */}
          <div>
            <label className={`block text-sm font-semibold ${colors.text} mb-2`}>
              States {selectedStates.length > 0 && `(${selectedStates.length} selected)`}
            </label>
            <div className="flex gap-2">
              <div className="flex-1">
                <MultiSelectDropdown
                  options={STATES}
                  selected={selectedStates}
                  onChange={setSelectedStates}
                  placeholder="Select states..."
                  theme={theme}
                  searchable={true}
                />
              </div>
              <button
                onClick={resetStates}
                disabled={selectedStates.length === 0}
                className={`px-3 py-2 border rounded-lg text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${colors.buttonSecondary}`}
                title="Reset states"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            {selectedStates.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {selectedStates.map(state => (
                  <span
                    key={state}
                    className={`inline-flex items-center gap-1 px-2 py-1 ${colors.badge} border rounded-full text-xs`}
                  >
                    {state.length > 15 ? state.slice(0, 15) + '...' : state}
                    <button
                      onClick={() => setSelectedStates(prev => prev.filter(s => s !== state))}
                      className="hover:text-red-600 transition-colors"
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Year Selector */}
          <div>
            <label className={`block text-sm font-semibold ${colors.text} mb-2`}>
              Years {selectedYears.length > 0 && `(${selectedYears.length} selected)`}
            </label>
            <div className="flex gap-2">
              <div className="flex-1">
                <MultiSelectDropdown
                  options={YEARS.map(y => y.replace("_", "-"))}
                  selected={selectedYears.map(y => y.replace("_", "-"))}
                  onChange={(years) => setSelectedYears(years.map(y => y.replace("-", "_")))}
                  placeholder="Select years..."
                  theme={theme}
                  searchable={false}
                />
              </div>
              <button
                onClick={resetYears}
                disabled={selectedYears.length === 0}
                className={`px-3 py-2 border rounded-lg text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${colors.buttonSecondary}`}
                title="Reset years"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            {selectedYears.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {selectedYears.map(year => (
                  <span
                    key={year}
                    className={`inline-flex items-center gap-1 px-2 py-1 ${colors.badge} border rounded-full text-xs`}
                  >
                    {year.replace("_", "-")}
                    <button
                      onClick={() => setSelectedYears(prev => prev.filter(y => y !== year))}
                      className="hover:text-red-600 transition-colors"
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Action Buttons - Fixed at bottom */}
        <div className={`p-6 border-t ${colors.border} space-y-2`}>
          <button
            onClick={runFilterQuery}
            disabled={!selectedMetric}
            className={`w-full py-3 ${colors.button} text-white font-semibold rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg flex items-center justify-center gap-2`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            Run Query
          </button>
          <button
            onClick={resetFilters}
            disabled={!selectedMetric && selectedStates.length === 0 && selectedYears.length === 0}
            className={`w-full py-2 border rounded-lg font-medium transition-colors text-sm disabled:opacity-40 disabled:cursor-not-allowed ${colors.buttonSecondary} flex items-center justify-center gap-2`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Reset All Filters
          </button>
        </div>
      </div>

      {/* Main Chat Panel */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className={`${colors.panel} border-b ${colors.border} px-6 py-4 flex items-center justify-between shadow-sm`}>
          <div className="flex items-center gap-4">
            <button
              onClick={() => setFiltersPanelOpen(!filtersPanelOpen)}
              className={`p-2 hover:${colors.listItem} rounded-lg transition-colors`}
            >
              <svg className={`w-5 h-5 ${colors.textSecondary}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <div>
              <h1 className={`text-xl font-bold ${colors.text}`}>INGRES Groundwater AI</h1>
              <p className={`text-sm ${colors.textTertiary}`}>Central Ground Water Board · India</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* Theme Switcher */}
            <div className="flex gap-1">
              {Object.keys(themes).map(themeName => (
                <button
                  key={themeName}
                  onClick={() => changeTheme(themeName)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    currentTheme === themeName
                      ? `${colors.button} text-white shadow-md`
                      : `${colors.buttonSecondary}`
                  }`}
                  title={themes[themeName].name}
                >
                  {themes[themeName].icon}
                </button>
              ))}
            </div>
            <div className={`flex items-center gap-2 px-3 py-1.5 ${colors.badge} border rounded-full`}>
              <div className={`w-2 h-2 ${colors.badgeDot} rounded-full animate-pulse`}></div>
              <span className="text-xs font-medium">Live</span>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.length === 0 && (
              <div className="text-center py-12">
                <div className={`w-16 h-16 mx-auto mb-4 rounded-2xl ${colors.avatar} flex items-center justify-center shadow-lg`}>
                  <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                  </svg>
                </div>
                <h2 className={`text-2xl font-bold ${colors.text} mb-2`}>Ask about groundwater data</h2>
                <p className={`${colors.textSecondary} mb-6`}>Use filters or ask questions about rainfall, recharge, extraction rates</p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {QUICK_QUERIES.map((q, i) => (
                    <button
                      key={i}
                      onClick={() => send(q)}
                      className={`px-4 py-2 ${colors.panel} border ${colors.border} rounded-full text-sm ${colors.text} hover:shadow-md transition-all`}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {msg.role === 'bot' && (
                  <div className={`w-8 h-8 rounded-full ${colors.avatar} flex items-center justify-center flex-shrink-0 shadow-md`}>
                    <span className="text-white text-xs font-bold">AI</span>
                  </div>
                )}
                <div className={`max-w-2xl p-4 rounded-2xl ${
                  msg.role === 'user'
                    ? `${colors.userMessage}`
                    : `${colors.botMessage} border shadow-sm`
                }`}>
                  {msg.role === 'bot' ? (
                    <>
                      <BotMessage text={msg.text} theme={theme} />
                      {msg.data && <DataTable data={msg.data} metric={msg.metric} theme={theme} />}
                    </>
                  ) : (
                    <span className="whitespace-pre-wrap">{msg.text}</span>
                  )}
                </div>
                {msg.role === 'user' && (
                  <div className={`w-8 h-8 rounded-full ${colors.userAvatar} flex items-center justify-center flex-shrink-0`}>
                    <span className="text-xs font-bold">You</span>
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex gap-3">
                <div className={`w-8 h-8 rounded-full ${colors.avatar} flex items-center justify-center flex-shrink-0 shadow-md`}>
                  <span className="text-white text-xs font-bold">AI</span>
                </div>
                <div className={`${colors.botMessage} border p-4 rounded-2xl shadow-sm`}>
                  <div className="flex gap-2">
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Input Area */}
        <div className={`${colors.panel} border-t ${colors.border} p-4 shadow-lg`}>
          <div className="max-w-4xl mx-auto flex gap-3">
            <textarea
              ref={textareaRef}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Use filters or ask about groundwater data..."
              rows={1}
              className={`flex-1 px-4 py-3 border rounded-xl ${colors.input} ${colors.inputFocus} resize-none text-sm transition-colors`}
            />
            <button
              onClick={() => send()}
              disabled={loading || !question.trim()}
              className={`px-6 py-3 ${colors.button} text-white font-semibold rounded-xl disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg`}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
          <p className={`text-center text-xs ${colors.textTertiary} mt-2`}>INGRES · Ministry of Jal Shakti · Data: CGWB</p>
        </div>
      </div>
    </div>
  )
}

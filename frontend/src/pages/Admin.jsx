import { useEffect, useState } from 'react'
import {
  getMembers, getMeetings,
  setBulkAttendance, updateSmallGroup,
  adjustDeposit, fullRefresh,
} from '../api/client'

const MEETING_LABELS = { 1: '3/14', 2: '4/25', 3: '6/13', 4: '7/18' }
const TABS = ['정기모임 출석', '조모임', '수동 조정', '새로고침']

// ── 공통 유틸 ─────────────────────────────────────────────────────────────────

function Msg({ msg }) {
  if (!msg) return null
  const isErr = msg.type === 'error'
  return (
    <div className={`rounded-lg px-4 py-2 text-sm mt-3 ${isErr ? 'bg-red-50 border border-red-200 text-red-600' : 'bg-green-50 border border-green-200 text-green-700'}`}>
      {msg.text}
    </div>
  )
}

// ── 정기모임 출석 탭 ──────────────────────────────────────────────────────────

function AttendanceTab({ members, meetings }) {
  const [selectedMeeting, setSelectedMeeting] = useState(null)
  const [attMap, setAttMap] = useState({}) // member_id → true | false | null
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState(null)

  function selectMeeting(mt) {
    setSelectedMeeting(mt)
    const map = {}
    for (const m of members) {
      const att = m.meeting_attendances?.find(a => a.meeting_id === mt.id)
      map[m.id] = att ? att.is_attended : null
    }
    setAttMap(map)
    setMsg(null)
  }

  function toggle(memberId, val) {
    setAttMap(prev => ({ ...prev, [memberId]: prev[memberId] === val ? null : val }))
  }

  async function handleSave() {
    if (!selectedMeeting) return
    const attendances = members
      .filter(m => attMap[m.id] !== null && attMap[m.id] !== undefined)
      .map(m => ({ member_id: m.id, is_attended: attMap[m.id] }))
    if (!attendances.length) { setMsg({ type: 'error', text: '입력된 출석 정보가 없습니다.' }); return }
    setSaving(true)
    try {
      await setBulkAttendance(selectedMeeting.id, { attendances })
      setMsg({ type: 'ok', text: `저장 완료 (${attendances.length}명)` })
    } catch {
      setMsg({ type: 'error', text: '저장에 실패했습니다.' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      {/* 회차 선택 */}
      <div className="flex gap-2 mb-6">
        {meetings.map(mt => (
          <button
            key={mt.id}
            onClick={() => selectMeeting(mt)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
              selectedMeeting?.id === mt.id
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {MEETING_LABELS[mt.sequence] ?? mt.meeting_date}
          </button>
        ))}
      </div>

      {!selectedMeeting && <p className="text-gray-400 text-sm">회차를 선택해주세요.</p>}

      {selectedMeeting && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
            {members.map(m => {
              const val = attMap[m.id]
              return (
                <div key={m.id} className="bg-white border border-gray-200 rounded-lg p-3">
                  <p className="text-sm font-medium mb-2">{m.name}</p>
                  <div className="flex gap-1">
                    <button
                      onClick={() => toggle(m.id, true)}
                      className={`flex-1 py-1 rounded text-xs font-medium transition ${val === true ? 'bg-green-500 text-white' : 'bg-gray-100 text-gray-500 hover:bg-green-100'}`}
                    >참석</button>
                    <button
                      onClick={() => toggle(m.id, false)}
                      className={`flex-1 py-1 rounded text-xs font-medium transition ${val === false ? 'bg-red-400 text-white' : 'bg-gray-100 text-gray-500 hover:bg-red-100'}`}
                    >불참</button>
                  </div>
                </div>
              )
            })}
          </div>
          <button
            onClick={handleSave}
            disabled={saving}
            className="bg-indigo-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition"
          >
            {saving ? '저장 중...' : '저장'}
          </button>
          <Msg msg={msg} />
        </>
      )}
    </div>
  )
}

// ── 조모임 탭 ─────────────────────────────────────────────────────────────────

function SmallGroupTab({ members, onMembersChange }) {
  const [sgMap, setSgMap] = useState({})
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState(null)

  useEffect(() => {
    const map = {}
    for (const m of members) map[m.id] = m.small_group_satisfied ?? null
    setSgMap(map)
  }, [members])

  function cycle(memberId) {
    setSgMap(prev => {
      const cur = prev[memberId]
      const next = cur === null ? true : cur === true ? false : null
      return { ...prev, [memberId]: next }
    })
  }

  async function handleSave() {
    setSaving(true)
    setMsg(null)
    try {
      await Promise.all(
        members.map(m => updateSmallGroup(m.id, sgMap[m.id]))
      )
      setMsg({ type: 'ok', text: '저장 완료' })
      onMembersChange()
    } catch {
      setMsg({ type: 'error', text: '저장에 실패했습니다.' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <p className="text-xs text-gray-400 mb-4">클릭하면 충족 → 미충족 → 미입력 순으로 변경됩니다.</p>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
        {members.map(m => {
          const val = sgMap[m.id]
          return (
            <button
              key={m.id}
              onClick={() => cycle(m.id)}
              className={`p-3 rounded-lg border text-sm font-medium text-left transition ${
                val === true  ? 'bg-green-50 border-green-300 text-green-700' :
                val === false ? 'bg-red-50 border-red-300 text-red-600' :
                                'bg-gray-50 border-gray-200 text-gray-400'
              }`}
            >
              <span className="block font-semibold">{m.name}</span>
              <span className="text-xs">{val === true ? '충족' : val === false ? '미충족' : '미입력'}</span>
            </button>
          )
        })}
      </div>
      <button
        onClick={handleSave}
        disabled={saving}
        className="bg-indigo-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition"
      >
        {saving ? '저장 중...' : '저장'}
      </button>
      <Msg msg={msg} />
    </div>
  )
}

// ── 수동 조정 탭 ──────────────────────────────────────────────────────────────

function ManualTab({ members }) {
  const [memberId, setMemberId] = useState('')
  const [amount, setAmount] = useState('')
  const [reason, setReason] = useState('')
  const [memo, setMemo] = useState('')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!memberId || !amount || !reason) { setMsg({ type: 'error', text: '멤버, 금액, 사유를 입력해주세요.' }); return }
    const amt = parseInt(amount, 10)
    if (isNaN(amt)) { setMsg({ type: 'error', text: '금액은 숫자로 입력해주세요.' }); return }
    setSaving(true)
    setMsg(null)
    try {
      const res = await adjustDeposit(memberId, { amount: amt, reason, memo: memo || undefined })
      setMsg({ type: 'ok', text: `저장 완료 — 잔액: ${res.deposit_balance.toLocaleString()}원` })
      setAmount(''); setReason(''); setMemo('')
    } catch {
      setMsg({ type: 'error', text: '저장에 실패했습니다.' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-md space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">멤버</label>
        <select
          value={memberId}
          onChange={e => setMemberId(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
        >
          <option value="">선택</option>
          {members.map(m => <option key={m.id} value={m.id}>{m.name} ({m.deposit_balance.toLocaleString()}원)</option>)}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">금액 (음수: 차감, 양수: 환급)</label>
        <input
          type="number"
          value={amount}
          onChange={e => setAmount(e.target.value)}
          placeholder="-10000"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">사유</label>
        <input
          type="text"
          value={reason}
          onChange={e => setReason(e.target.value)}
          placeholder="예: 수동 차감"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">메모 (선택)</label>
        <textarea
          value={memo}
          onChange={e => setMemo(e.target.value)}
          rows={2}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
      </div>
      <button
        type="submit"
        disabled={saving}
        className="bg-indigo-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition"
      >
        {saving ? '저장 중...' : '저장'}
      </button>
      <Msg msg={msg} />
    </form>
  )
}

// ── 새로고침 탭 ───────────────────────────────────────────────────────────────

function ForceRefreshTab() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [msg, setMsg] = useState(null)

  async function handleForce() {
    if (!window.confirm('쿨타임을 무시하고 강제 새로고침하시겠습니까?\n(잔액 초기화 → 밴드 싱크 → 차감 적용)')) return
    setLoading(true)
    setResult(null)
    setMsg(null)
    try {
      const res = await fullRefresh(true)
      setResult(res)
      setMsg({ type: 'ok', text: '완료됐습니다.' })
    } catch {
      setMsg({ type: 'error', text: '실패했습니다.' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <p className="text-sm text-gray-500 mb-4">쿨타임을 무시하고 전체 데이터를 강제로 새로 계산합니다.</p>
      <button
        onClick={handleForce}
        disabled={loading}
        className="flex items-center gap-2 bg-red-500 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-red-600 disabled:opacity-50 transition"
      >
        {loading ? (
          <>
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
            </svg>
            실행 중...
          </>
        ) : '강제 새로고침'}
      </button>
      <Msg msg={msg} />

      {result && (
        <div className="mt-6 space-y-4">
          <div>
            <p className="text-sm font-semibold text-gray-700 mb-1">싱크된 일지 ({result.synced_journals.length}건)</p>
            <div className="flex flex-wrap gap-2">
              {result.synced_journals.map(h => (
                <span key={h} className="bg-green-100 text-green-700 text-xs px-2 py-1 rounded">{h}</span>
              ))}
              {result.synced_journals.length === 0 && <span className="text-gray-400 text-xs">없음</span>}
            </div>
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-700 mb-1">스킵된 일지 ({result.skipped_journals.length}건)</p>
            <div className="flex flex-wrap gap-2">
              {result.skipped_journals.map(h => (
                <span key={h} className="bg-gray-100 text-gray-500 text-xs px-2 py-1 rounded">{h}</span>
              ))}
            </div>
          </div>
          <div>
            <p className="text-sm font-semibold text-gray-700 mb-2">적용된 차감 ({result.applied_deductions.filter(d => d.applied.length > 0).length}명)</p>
            <div className="space-y-1">
              {result.applied_deductions
                .filter(d => d.applied.length > 0)
                .map(d => (
                  <div key={d.member_id} className="text-xs bg-white border border-gray-200 rounded px-3 py-2">
                    <span className="font-medium">{d.name}</span>
                    <span className="text-gray-400 ml-2">→ {d.deposit_balance.toLocaleString()}원</span>
                    <span className="text-red-500 ml-2">{d.applied.map(a => a.reason).join(', ')}</span>
                  </div>
                ))}
              {result.applied_deductions.filter(d => d.applied.length > 0).length === 0 && (
                <p className="text-gray-400 text-xs">차감 없음</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Admin 메인 ────────────────────────────────────────────────────────────────

export default function Admin() {
  const [activeTab, setActiveTab] = useState(0)
  const [members, setMembers] = useState([])
  const [meetings, setMeetings] = useState([])
  const [loading, setLoading] = useState(true)

  const loadMembers = () => getMembers().then(setMembers)

  useEffect(() => {
    Promise.all([loadMembers(), getMeetings().then(setMeetings)])
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-center py-20 text-gray-400">불러오는 중...</p>

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">관리자 페이지</h1>

      {/* 탭 */}
      <div className="flex border-b border-gray-200 mb-6">
        {TABS.map((tab, i) => (
          <button
            key={i}
            onClick={() => setActiveTab(i)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition -mb-px ${
              activeTab === i
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* 탭 컨텐츠 */}
      {activeTab === 0 && <AttendanceTab members={members} meetings={meetings} />}
      {activeTab === 1 && <SmallGroupTab members={members} onMembersChange={loadMembers} />}
      {activeTab === 2 && <ManualTab members={members} />}
      {activeTab === 3 && <ForceRefreshTab />}
    </div>
  )
}

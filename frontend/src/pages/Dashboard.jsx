import { useEffect, useState, useCallback } from 'react'
import { getMembers, getJournals, getMeetings, fullRefresh, getRefreshStatus } from '../api/client'

const MEETING_LABELS = ['3/14', '4/25', '6/13', '7/18']

function cell(val, trueLabel, falseLabel) {
  if (val === true)  return <span className="text-green-600 font-medium">{trueLabel}</span>
  if (val === false) return <span className="text-red-500 font-medium">{falseLabel}</span>
  return <span className="text-gray-400">-</span>
}

function buildSummary(members) {
  let totalDeduction = 0
  let deductedCount = 0
  let noDeductionCount = 0
  for (const m of members) {
    const ded = 50000 - m.deposit_balance
    if (ded > 0) { totalDeduction += ded; deductedCount++ }
    else noDeductionCount++
  }
  const perPerson = noDeductionCount > 0 ? Math.floor(totalDeduction / noDeductionCount) : null
  const rate = perPerson ? ((perPerson / 50000) * 100).toFixed(1) : null
  return { totalDeduction, deductedCount, noDeductionCount, perPerson, rate }
}

function minutesUntil(isoStr) {
  if (!isoStr) return 0
  return Math.max(0, Math.ceil((new Date(isoStr) - Date.now()) / 60000))
}

function fmtDatetime(isoStr) {
  if (!isoStr) return null
  const d = new Date(isoStr)
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export default function Dashboard() {
  const [members, setMembers] = useState([])
  const [journals, setJournals] = useState([])
  const [meetings, setMeetings] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)
  const [refreshError, setRefreshError] = useState(null)
  const [status, setStatus] = useState(null) // { last_refresh_at, next_available_at, is_cooling_down }

  const loadData = useCallback(() =>
    Promise.all([getMembers(), getJournals(), getMeetings()])
      .then(([m, j, mt]) => {
        setMembers(m)
        setJournals(j.sort((a, b) => a.check_date.localeCompare(b.check_date)))
        setMeetings(mt.sort((a, b) => a.sequence - b.sequence))
      }), [])

  const loadStatus = useCallback(() =>
    getRefreshStatus().then(setStatus).catch(() => {}), [])

  useEffect(() => {
    Promise.all([loadData(), loadStatus()])
      .catch(() => setError('데이터를 불러오지 못했습니다.'))
      .finally(() => setLoading(false))
  }, [loadData, loadStatus])

  // 쿨타임 카운트다운 (1분마다 갱신)
  useEffect(() => {
    if (!status?.is_cooling_down) return
    const id = setInterval(() => loadStatus(), 60000)
    return () => clearInterval(id)
  }, [status?.is_cooling_down, loadStatus])

  async function handleRefresh() {
    setRefreshing(true)
    setRefreshError(null)
    try {
      await fullRefresh(false)
      await Promise.all([loadData(), loadStatus()])
    } catch (e) {
      const detail = e?.response?.data?.detail
      if (detail?.next_available_at) {
        await loadStatus()
        setRefreshError(`쿨타임 중입니다. ${minutesUntil(detail.next_available_at)}분 후 가능합니다.`)
      } else {
        setRefreshError('새로고침에 실패했습니다.')
      }
    } finally {
      setRefreshing(false)
    }
  }

  if (loading) return <p className="text-center py-20 text-gray-400">불러오는 중...</p>
  if (error)   return <p className="text-center py-20 text-red-400">{error}</p>

  const { totalDeduction, deductedCount, noDeductionCount, perPerson, rate } = buildSummary(members)
  const minsLeft = status?.is_cooling_down ? minutesUntil(status.next_available_at) : 0
  const isCooling = status?.is_cooling_down && minsLeft > 0

  return (
    <div className="px-4 py-8 max-w-full">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-6 gap-4 flex-wrap">
        <h1 className="text-2xl font-bold">똑똑 — 활동 현황</h1>
        <div className="flex items-center gap-3">
          {status?.last_refresh_at && (
            <span className="text-xs text-gray-400">
              마지막 업데이트: {fmtDatetime(status.last_refresh_at)}
            </span>
          )}
          <button
            onClick={handleRefresh}
            disabled={refreshing || isCooling}
            className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {refreshing ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                </svg>
                새로고침 중...
              </>
            ) : isCooling ? `${minsLeft}분 후 가능` : '새로고침'}
          </button>
        </div>
      </div>

      {refreshError && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-600 rounded-lg px-4 py-2 text-sm">
          {refreshError}
        </div>
      )}

      {/* 요약 카드 */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <p className="text-xs text-gray-500 mb-1">벌금 총합</p>
          <p className="text-xl font-bold text-red-500">
            {totalDeduction > 0 ? `-${totalDeduction.toLocaleString()}원` : '0원'}
          </p>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <p className="text-xs text-gray-500 mb-1">n빵 수익 ({noDeductionCount}명 기준)</p>
          {perPerson !== null ? (
            <p className="text-xl font-bold text-green-600">
              +{perPerson.toLocaleString()}원
              <span className="text-sm font-normal text-gray-400 ml-1">(+{rate}%)</span>
            </p>
          ) : <p className="text-xl font-bold text-gray-400">-</p>}
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
          <p className="text-xs text-gray-500 mb-1">차감 발생 인원</p>
          <p className="text-xl font-bold text-orange-500">{deductedCount}명</p>
        </div>
      </div>

      {/* 테이블 */}
      <div className="overflow-x-auto rounded-xl border border-gray-200 shadow-sm">
        <table className="text-sm border-collapse min-w-max w-full">
          <thead>
            <tr className="bg-gray-100 sticky top-0 z-10">
              <th rowSpan={2} className="border border-gray-200 px-3 py-2 text-left font-semibold min-w-[80px] sticky left-0 bg-gray-100 z-20">이름</th>
              {journals.map(j => (
                <th key={j.id} colSpan={2} className="border border-gray-200 px-2 py-2 text-center font-semibold">
                  {j.label.match(/^(\d+월)/)?.[0] ?? j.label}
                </th>
              ))}
              <th colSpan={meetings.length} className="border border-gray-200 px-2 py-2 text-center font-semibold">정모</th>
              <th rowSpan={2} className="border border-gray-200 px-3 py-2 text-center font-semibold">조모임</th>
              <th colSpan={2} className="border border-gray-200 px-2 py-2 text-center font-semibold">합계</th>
            </tr>
            <tr className="bg-gray-50 sticky top-[37px] z-10">
              {journals.map(j => (
                <>
                  <th key={`${j.id}-w`} className="border border-gray-200 px-2 py-1 text-center text-xs font-medium text-gray-500">일지</th>
                  <th key={`${j.id}-c`} className="border border-gray-200 px-2 py-1 text-center text-xs font-medium text-gray-500">댓글</th>
                </>
              ))}
              {meetings.map((mt, i) => (
                <th key={mt.id} className="border border-gray-200 px-2 py-1 text-center text-xs font-medium text-gray-500">
                  {MEETING_LABELS[i] ?? mt.meeting_date?.slice(5).replace('-', '/')}
                </th>
              ))}
              <th className="border border-gray-200 px-2 py-1 text-center text-xs font-medium text-gray-500">총 차감</th>
              <th className="border border-gray-200 px-2 py-1 text-center text-xs font-medium text-gray-500">잔액</th>
            </tr>
          </thead>
          <tbody>
            {members.map((m, i) => {
              const totalDed = m.deposit_history?.reduce((s, h) => s + h.amount, 0) ?? 0
              return (
                <tr key={m.id} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                  <td className={`border border-gray-200 px-3 py-2 font-medium sticky left-0 z-10 ${i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}`}>
                    {m.name}
                  </td>
                  {journals.map(j => {
                    const jc = m.journal_checks?.find(c => c.journal_id === j.id)
                    const cc = m.comment_checks?.find(c => c.journal_id === j.id)
                    return (
                      <>
                        <td key={`${m.id}-${j.id}-w`} className="border border-gray-200 px-2 py-2 text-center">
                          {jc ? cell(jc.is_written, '✅', '❌') : <span className="text-gray-300">-</span>}
                        </td>
                        <td key={`${m.id}-${j.id}-c`} className="border border-gray-200 px-2 py-2 text-center">
                          {cc ? cell(cc.is_satisfied, '✅', '❌') : <span className="text-gray-300">-</span>}
                        </td>
                      </>
                    )
                  })}
                  {meetings.map(mt => {
                    const att = m.meeting_attendances?.find(a => a.meeting_id === mt.id)
                    return (
                      <td key={`${m.id}-${mt.id}`} className="border border-gray-200 px-2 py-2 text-center">
                        {att ? att.is_attended
                          ? <span className="text-green-600 font-medium">참석</span>
                          : <span className="text-red-500 font-medium">불참</span>
                          : <span className="text-gray-400">-</span>}
                      </td>
                    )
                  })}
                  <td className="border border-gray-200 px-2 py-2 text-center">
                    {m.small_group_satisfied === true  && <span className="text-green-600 font-medium">충족</span>}
                    {m.small_group_satisfied === false && <span className="text-red-500 font-medium">미충족</span>}
                    {(m.small_group_satisfied == null) && <span className="text-gray-400">-</span>}
                  </td>
                  <td className="border border-gray-200 px-3 py-2 text-center font-medium text-red-600">
                    {totalDed < 0 ? `-${Math.abs(totalDed).toLocaleString()}` : '0원'}
                  </td>
                  <td className="border border-gray-200 px-3 py-2 text-center font-semibold">
                    {m.deposit_balance.toLocaleString()}원
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

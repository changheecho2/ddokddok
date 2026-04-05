import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
})

// ── Members ──────────────────────────────────────────────────────────────────

export const getMembers = () => api.get('/members').then(r => r.data)
export const getMember = (id) => api.get(`/members/${id}`).then(r => r.data)
export const adjustDeposit = (id, body) =>
  api.post(`/members/${id}/deposit`, body).then(r => r.data)
export const updateSmallGroup = (id, satisfied) =>
  api.patch(`/members/${id}/small-group`, { satisfied }).then(r => r.data)

// ── Journals ─────────────────────────────────────────────────────────────────

export const getJournals = () => api.get('/journals').then(r => r.data)
export const createJournal = (body) => api.post('/journals', body).then(r => r.data)
export const deleteJournal = (id) => api.delete(`/journals/${id}`).then(r => r.data)

// ── Meetings ─────────────────────────────────────────────────────────────────

export const getMeetings = () => api.get('/meetings').then(r => r.data)
export const createMeeting = (body) => api.post('/meetings', body).then(r => r.data)
export const setAttendance = (meetingId, body) =>
  api.post(`/meetings/${meetingId}/attendance`, body).then(r => r.data)
export const setBulkAttendance = (meetingId, body) =>
  api.post(`/meetings/${meetingId}/attendance/bulk`, body).then(r => r.data)


// ── Band Sync ─────────────────────────────────────────────────────────────────

export const syncJournal = (journalId) =>
  api.post(`/band/sync/${journalId}`).then(r => r.data)
export const getSyncResult = (journalId) =>
  api.get(`/band/sync/${journalId}/result`).then(r => r.data)

// ── Refresh ───────────────────────────────────────────────────────────────────

export const getRefreshStatus = () => api.get('/refresh/status').then(r => r.data)
export const fullRefresh = (force = false) => api.post(`/refresh?force=${force}`).then(r => r.data)

// ── Deposit ───────────────────────────────────────────────────────────────────

export const calculateDeposit = () => api.get('/deposit/calculate').then(r => r.data)
export const calculateMemberDeposit = (id) =>
  api.get(`/deposit/calculate/${id}`).then(r => r.data)
export const applyDeposit = () => api.post('/deposit/apply').then(r => r.data)
export const applyMemberDeposit = (id) =>
  api.post(`/deposit/apply/${id}`).then(r => r.data)

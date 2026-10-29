import axios from 'axios'

const TOKEN_KEY = 'scomp-auth-token'

export const getAuthToken = () => localStorage.getItem(TOKEN_KEY)

export const setAuthToken = (token) => {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
    axios.defaults.headers.common.Authorization = `Bearer ${token}`
  } else {
    localStorage.removeItem(TOKEN_KEY)
    delete axios.defaults.headers.common.Authorization
  }
}

export const initialiseAuth = () => setAuthToken(getAuthToken())

export async function login(username, password) {
  const response = await axios.post('/api/auth/login', { username, password })
  setAuthToken(response.data.token)
  return response.data.user
}

export async function loadCurrentUser() {
  const token = getAuthToken()
  if (!token) return null
  initialiseAuth()
  try {
    const response = await axios.get('/api/auth/me')
    return response.data
  } catch {
    setAuthToken(null)
    return null
  }
}

export function logout() {
  setAuthToken(null)
}

export async function completePasswordAction(path, token, password) {
  const response = await axios.post(`/api/auth/${path}`, { token, password })
  return response.data
}

export async function loadPasswordActionInfo(mode, token) {
  const response = await axios.post('/api/auth/password-action', { mode, token })
  return response.data
}

import { createContext, useContext, useState } from 'react'
import { api } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem('soc_user')
    return raw ? JSON.parse(raw) : null
  })

  async function login(username, password) {
    const res = await api.login(username, password)
    localStorage.setItem('soc_token', res.access_token)
    const userObj = { role: res.role, displayName: res.display_name }
    localStorage.setItem('soc_user', JSON.stringify(userObj))
    setUser(userObj)
    return userObj
  }

  function logout() {
    localStorage.removeItem('soc_token')
    localStorage.removeItem('soc_user')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}

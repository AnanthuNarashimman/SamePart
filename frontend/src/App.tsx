import { Navigate, Route, Routes } from 'react-router-dom'
import { Sidebar } from './components/layout/Sidebar'
import { Dashboard } from './pages/Dashboard'
import { Import } from './pages/Import'
import { ReconciliationDesk } from './pages/ReconciliationDesk'
import { Questions } from './pages/Questions'
import { DuplicateCheck } from './pages/DuplicateCheck'
import { Insights } from './pages/Insights'
import { RelationshipGraph } from './pages/RelationshipGraph'
import { Landing } from './pages/Landing'
import { Login } from './pages/Login'
import { AuditTrail } from './pages/AuditTrail'
import { useAuth } from './lib/auth'

function App() {
  const { session } = useAuth()

  // Signed out, the door is a landing page rather than a login form: anyone arriving at this
  // host is far more likely to be evaluating the idea than holding a seat. The form stays one
  // click away at /login, and every stale in-app URL falls through to the landing page.
  if (!session) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Landing />} />
      </Routes>
    )
  }

  return (
    <div className="flex h-screen w-screen app-canvas">
      <Sidebar />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/import" element={<Import />} />
        <Route path="/desk" element={<ReconciliationDesk />} />
        <Route path="/questions" element={<Questions />} />
        <Route path="/check" element={<DuplicateCheck />} />
        <Route path="/graph" element={<RelationshipGraph />} />
        <Route path="/insights" element={<Insights />} />
        <Route path="/audit" element={<AuditTrail />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}

export default App

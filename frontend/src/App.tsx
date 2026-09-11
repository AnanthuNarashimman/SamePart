import { Route, Routes } from 'react-router-dom'
import { Sidebar } from './components/layout/Sidebar'
import { Dashboard } from './pages/Dashboard'
import { Import } from './pages/Import'
import { ReconciliationDesk } from './pages/ReconciliationDesk'
import { Questions } from './pages/Questions'
import { DuplicateCheck } from './pages/DuplicateCheck'
import { Insights } from './pages/Insights'
import { RelationshipGraph } from './pages/RelationshipGraph'
import { Login } from './pages/Login'
import { useAuth } from './lib/auth'

function App() {
  const { session } = useAuth()
  if (!session) return <Login />
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
      </Routes>
    </div>
  )
}

export default App

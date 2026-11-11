import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import EventIntelligence from './pages/EventIntelligence'
import PortfolioAnalyzer from './pages/PortfolioAnalyzer'
import RippleGraph from './pages/RippleGraph'
import ScenarioSimulator from './pages/ScenarioSimulator'
import PersonaComparison from './pages/PersonaComparison'
import InvestigationReportPage from './pages/InvestigationReportPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="events" element={<EventIntelligence />} />
        <Route path="portfolio" element={<PortfolioAnalyzer />} />
        <Route path="graph" element={<RippleGraph />} />
        <Route path="scenarios" element={<ScenarioSimulator />} />
        <Route path="personas" element={<PersonaComparison />} />
        <Route path="report" element={<InvestigationReportPage />} />
      </Route>
    </Routes>
  )
}

import demoAnalysis from '../data/demoAnalysis.json'
import type { DemoAnalysisPayload } from '../types'

// VITE_API_BASE_URL is unset in the demo build, so the app runs entirely off the
// real (not fabricated) demo analysis output baked at build time by
// scripts/run_full_investigation_demo.py's underlying orchestrator -- see
// frontend/README.md for how to regenerate it, and set VITE_API_BASE_URL to point
// at a deployed API Gateway URL once the backend is live.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string | undefined

export const DEMO_ANALYSIS = demoAnalysis as unknown as DemoAnalysisPayload

export async function fetchDemoAnalysis(): Promise<DemoAnalysisPayload> {
  if (!API_BASE_URL) {
    return DEMO_ANALYSIS
  }
  const response = await fetch(`${API_BASE_URL}/api/analyses/${DEMO_ANALYSIS.analysis.analysis_id}`)
  if (!response.ok) {
    throw new Error(`API error ${response.status}`)
  }
  return response.json()
}

export function isLiveApiConfigured(): boolean {
  return Boolean(API_BASE_URL)
}

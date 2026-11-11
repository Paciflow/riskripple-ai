import { useMemo, useState } from 'react'
import ReactFlow, { Background, Controls, type Edge, type Node } from 'reactflow'
import 'reactflow/dist/style.css'
import { DEMO_ANALYSIS } from '../lib/api'
import { Card, PageHeader, Pill, SimulationBanner } from '../components/ui'

const HOLDINGS = new Set(['NVDA', 'AMD', 'INTC'])

export default function RippleGraph() {
  const { exposure_graph } = DEMO_ANALYSIS.analysis
  const [selectedEdge, setSelectedEdge] = useState<number | null>(null)

  const { nodes, edges } = useMemo(() => {
    if (!exposure_graph) return { nodes: [] as Node[], edges: [] as Edge[] }

    const holdingNodes = exposure_graph.nodes.filter((n) => HOLDINGS.has(n))
    const supplierNodes = exposure_graph.nodes.filter((n) => !HOLDINGS.has(n))

    const nodes: Node[] = [
      ...holdingNodes.map((id, i) => ({
        id,
        data: { label: `${id} (portfolio holding)` },
        position: { x: 60, y: 60 + i * 110 },
        style: {
          background: 'var(--color-accent)',
          color: '#0b1220',
          borderRadius: 8,
          fontSize: 12,
          fontWeight: 600,
          border: 'none',
        },
      })),
      ...supplierNodes.map((id, i) => ({
        id,
        data: { label: id },
        position: { x: 420, y: 20 + i * 70 },
        style: {
          background: 'var(--color-surface-2)',
          color: 'var(--color-text)',
          borderRadius: 8,
          fontSize: 12,
          border: '1px solid var(--color-border)',
        },
      })),
    ]

    const edges: Edge[] = exposure_graph.edges.map((e, i) => ({
      id: `e${i}`,
      source: e.source,
      target: e.target,
      label: e.relationship_type,
      animated: true,
      style: { stroke: 'var(--color-accent)' },
      labelStyle: { fill: 'var(--color-text-dim)', fontSize: 10 },
    }))

    return { nodes, edges }
  }, [exposure_graph])

  const selected = selectedEdge !== null ? exposure_graph?.edges[selectedEdge] : null

  return (
    <div>
      <PageHeader
        title="Ripple Graph"
        subtitle="Verified supplier relationships extracted from each company's actual 10-K filing text."
      />
      <SimulationBanner />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 p-0 overflow-hidden" style={{ height: 480 }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onEdgeClick={(_, edge) => setSelectedEdge(Number(edge.id.replace('e', '')))}
            fitView
            proOptions={{ hideAttribution: true }}
          >
            <Background color="var(--color-border)" gap={24} />
            <Controls />
          </ReactFlow>
        </Card>

        <Card>
          <h3 className="text-sm font-medium mb-3" style={{ color: 'var(--color-text-dim)' }}>
            Evidence
          </h3>
          {selected ? (
            <div className="text-sm space-y-2">
              <div className="flex items-center gap-2">
                <span className="font-medium">{selected.source}</span>
                <span style={{ color: 'var(--color-text-dim)' }}>→</span>
                <span className="font-medium">{selected.target}</span>
              </div>
              <Pill tone={selected.confidence === 'verified' ? 'good' : 'warn'}>{selected.confidence}</Pill>
              <p className="text-xs italic" style={{ color: 'var(--color-text-dim)' }}>
                {selected.evidence_source}
              </p>
            </div>
          ) : (
            <p className="text-sm" style={{ color: 'var(--color-text-dim)' }}>
              Click an edge in the graph to see the exact filing sentence that
              supports that relationship. Every edge here was found by a literal
              keyword match in a real SEC 10-K — nothing was inferred from
              same-industry membership alone.
            </p>
          )}
        </Card>
      </div>
    </div>
  )
}

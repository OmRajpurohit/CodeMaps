import React, { useEffect, useRef, useState, useMemo } from 'react';
import * as d3 from 'd3';
import {
  Search,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Sparkles,
  Zap,
  ArrowRight,
  X,
} from 'lucide-react';
import type { DependencyGraph, GraphNode, CyclesData } from '../types';

interface GraphViewerProps {
  graphData: DependencyGraph;
  cyclesData?: CyclesData | null;
  onSelectImpactNode: (nodeId: string) => void;
  onExplainNode: (filePath: string) => void;
}

export const GraphViewer: React.FC<GraphViewerProps> = ({
  graphData,
  cyclesData,
  onSelectImpactNode,
  onExplainNode,
}) => {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [nodeTypeFilter, setNodeTypeFilter] = useState<'all' | 'file' | 'class' | 'function'>('all');
  const [edgeTypeFilters, setEdgeTypeFilters] = useState<Record<string, boolean>>({
    imports: true,
    calls: true,
    inherits: true,
    implements: true,
    contains: false,
  });
  const [highlightCycles, setHighlightCycles] = useState(true);

  // Set of cyclic node IDs from cyclesData
  const cyclicNodeSet = useMemo(() => {
    const set = new Set<string>();
    if (!cyclesData) return set;
    for (const c of cyclesData.cycles) {
      c.nodes.forEach((n) => set.add(n));
    }
    for (const scc of cyclesData.scc_clusters) {
      if (scc.size > 1) {
        scc.nodes.forEach((n) => set.add(n));
      }
    }
    return set;
  }, [cyclesData]);

  // Filtered nodes and edges
  const { filteredNodes, filteredEdges } = useMemo(() => {
    let nodes = graphData.nodes;
    if (nodeTypeFilter !== 'all') {
      nodes = nodes.filter((n) => n.node_type === nodeTypeFilter);
    }
    const nodeIds = new Set(nodes.map((n) => n.id));

    const edges = graphData.edges.filter((e) => {
      const srcId = typeof e.source === 'object' ? (e.source as GraphNode).id : e.source;
      const tgtId = typeof e.target === 'object' ? (e.target as GraphNode).id : e.target;
      return (
        nodeIds.has(srcId) &&
        nodeIds.has(tgtId) &&
        (edgeTypeFilters[e.edge_type] ?? true)
      );
    });

    return { filteredNodes: nodes, filteredEdges: edges };
  }, [graphData, nodeTypeFilter, edgeTypeFilters]);

  // Incoming and outgoing connections for selected node
  const connections = useMemo(() => {
    if (!selectedNode) return { incoming: [], outgoing: [] };
    const inc: GraphNode[] = [];
    const out: GraphNode[] = [];

    const nodeMap = new Map(graphData.nodes.map((n) => [n.id, n]));

    graphData.edges.forEach((e) => {
      const srcId = typeof e.source === 'object' ? (e.source as GraphNode).id : e.source;
      const tgtId = typeof e.target === 'object' ? (e.target as GraphNode).id : e.target;

      if (tgtId === selectedNode.id && srcId !== selectedNode.id) {
        const srcNode = nodeMap.get(srcId);
        if (srcNode) inc.push(srcNode);
      }
      if (srcId === selectedNode.id && tgtId !== selectedNode.id) {
        const tgtNode = nodeMap.get(tgtId);
        if (tgtNode) out.push(tgtNode);
      }
    });

    return { incoming: inc, outgoing: out };
  }, [selectedNode, graphData]);

  // Node Color Helper
  const getNodeColor = React.useCallback(
    (node: GraphNode) => {
      if (highlightCycles && cyclicNodeSet.has(node.id)) {
        return '#ef4444'; // Red for cycles
      }
      switch (node.node_type) {
        case 'file':
          return '#38bdf8'; // Sky blue
        case 'class':
          return '#c084fc'; // Purple
        case 'function':
          return '#34d399'; // Emerald
        case 'method':
          return '#fbbf24'; // Amber
        case 'package':
          return '#818cf8'; // Indigo
        default:
          return '#94a3b8';
      }
    },
    [highlightCycles, cyclicNodeSet]
  );

  const getEdgeColor = (edgeType: string) => {
    switch (edgeType) {
      case 'imports':
        return '#60a5fa';
      case 'calls':
        return '#34d399';
      case 'inherits':
        return '#f59e0b';
      case 'implements':
        return '#c084fc';
      case 'contains':
        return '#475569';
      default:
        return '#64748b';
    }
  };

  // D3 Force Simulation Setup
  useEffect(() => {
    if (!svgRef.current || !containerRef.current || filteredNodes.length === 0) return;

    const width = containerRef.current.clientWidth || 900;
    const height = containerRef.current.clientHeight || 650;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    // Define Arrow Marker definitions
    const defs = svg.append('defs');
    ['imports', 'calls', 'inherits', 'implements', 'contains', 'cycle'].forEach((type) => {
      const color = type === 'cycle' ? '#ef4444' : getEdgeColor(type);
      defs
        .append('marker')
        .attr('id', `arrow-${type}`)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 22)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', color);
    });

    const g = svg.append('g').attr('class', 'graph-viewport');

    // Setup Zoom Behavior
    const zoomBehavior = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });

    svg.call(zoomBehavior);

    // Deep copy nodes and edges for D3 simulation
    const nodesCopy: GraphNode[] = filteredNodes.map((n) => ({ ...n }));
    const edgesCopy = filteredEdges.map((e) => ({
      ...e,
      source: typeof e.source === 'object' ? (e.source as GraphNode).id : e.source,
      target: typeof e.target === 'object' ? (e.target as GraphNode).id : e.target,
    }));

    // Simulation
    const simulation = d3
      .forceSimulation<GraphNode>(nodesCopy)
      .force(
        'link',
        d3
          .forceLink<GraphNode, any>(edgesCopy)
          .id((d) => d.id)
          .distance(90)
      )
      .force('charge', d3.forceManyBody().strength(-240))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collide', d3.forceCollide().radius(25));

    // Draw Links
    const link = g
      .append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(edgesCopy)
      .enter()
      .append('line')
      .attr('stroke', (d) => getEdgeColor(d.edge_type))
      .attr('stroke-opacity', 0.55)
      .attr('stroke-width', (d) => (d.edge_type === 'imports' ? 1.5 : 1))
      .attr('marker-end', (d) => `url(#arrow-${d.edge_type})`);

    // Draw Node Groups
    const node = g
      .append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(nodesCopy)
      .enter()
      .append('g')
      .attr('class', 'node')
      .style('cursor', 'pointer')
      .call(
        d3
          .drag<SVGGElement, GraphNode>()
          .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on('drag', (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      )
      .on('click', (_event, d) => {
        const found = graphData.nodes.find((n) => n.id === d.id);
        setSelectedNode(found || d);
      });

    // Node Circle
    node
      .append('circle')
      .attr('r', (d) => {
        if (d.node_type === 'file') return 12;
        return 9;
      })
      .attr('fill', (d) => getNodeColor(d))
      .attr('stroke', (d) => (cyclicNodeSet.has(d.id) && highlightCycles ? '#ef4444' : '#0f172a'))
      .attr('stroke-width', (d) => (cyclicNodeSet.has(d.id) && highlightCycles ? 3 : 2))
      .attr('filter', (d) => (cyclicNodeSet.has(d.id) && highlightCycles ? 'drop-shadow(0 0 6px rgba(239, 68, 68, 0.8))' : 'none'));

    // Node Labels
    node
      .append('text')
      .text((d) => d.name)
      .attr('x', 14)
      .attr('y', 4)
      .attr('fill', '#e2e8f0')
      .attr('font-size', '10px')
      .attr('font-family', 'ui-monospace, monospace')
      .attr('pointer-events', 'none');

    // Simulation Tick
    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => d.source.x)
        .attr('y1', (d: any) => d.source.y)
        .attr('x2', (d: any) => d.target.x)
        .attr('y2', (d: any) => d.target.y);

      node.attr('transform', (d) => `translate(${d.x},${d.y})`);
    });

    return () => {
      simulation.stop();
    };
  }, [filteredNodes, filteredEdges, highlightCycles, cyclicNodeSet, getNodeColor, graphData.nodes]);

  // Zoom Controls
  const handleZoom = (factor: number) => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.transition().duration(300).call(d3.zoom<SVGSVGElement, unknown>().scaleBy as any, factor);
  };

  const handleResetZoom = () => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.transition().duration(500).call(d3.zoom<SVGSVGElement, unknown>().transform as any, d3.zoomIdentity);
  };

  return (
    <div className="relative w-full h-[750px] rounded-2xl border border-slate-800 bg-slate-950 overflow-hidden flex flex-col">
      {/* Top Controls Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 border-b border-slate-800 bg-slate-900/70 backdrop-blur-md z-10">
        <div className="flex items-center gap-3">
          {/* Search Box */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search symbol or file..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1.5 text-xs rounded-lg bg-slate-800 border border-slate-700 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-52"
            />
          </div>

          {/* Node Filter */}
          <div className="flex items-center gap-1 bg-slate-800/80 p-1 rounded-lg border border-slate-700 text-xs">
            {(['all', 'file', 'class', 'function'] as const).map((type) => (
              <button
                key={type}
                onClick={() => setNodeTypeFilter(type)}
                className={`px-2.5 py-1 rounded font-medium capitalize transition-colors ${
                  nodeTypeFilter === type
                    ? 'bg-indigo-600 text-white shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {type}
              </button>
            ))}
          </div>

          {/* Cycle Highlighting Toggle */}
          <button
            onClick={() => setHighlightCycles(!highlightCycles)}
            className={`flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-lg border transition-all ${
              highlightCycles
                ? 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-slate-300'
            }`}
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Cycle Glow</span>
          </button>
        </div>

        {/* Edge Type Filters & Zoom buttons */}
        <div className="flex items-center gap-2">
          {/* Edge Filter Pills */}
          <div className="hidden lg:flex items-center gap-2 mr-2 text-xs">
            {Object.entries(edgeTypeFilters).map(([type, active]) => (
              <button
                key={type}
                onClick={() => setEdgeTypeFilters({ ...edgeTypeFilters, [type]: !active })}
                className={`flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium border transition-colors ${
                  active
                    ? 'bg-slate-800 text-slate-200 border-slate-600'
                    : 'bg-slate-900 text-slate-500 border-slate-800 hover:border-slate-700'
                }`}
              >
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: getEdgeColor(type) }}
                />
                <span className="capitalize">{type}</span>
              </button>
            ))}
          </div>

          {/* Zoom controls */}
          <div className="flex items-center gap-1 bg-slate-800/80 p-0.5 rounded-lg border border-slate-700">
            <button
              onClick={() => handleZoom(1.2)}
              title="Zoom In"
              className="p-1.5 text-slate-400 hover:text-white rounded hover:bg-slate-700 transition-colors"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => handleZoom(0.8)}
              title="Zoom Out"
              className="p-1.5 text-slate-400 hover:text-white rounded hover:bg-slate-700 transition-colors"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={handleResetZoom}
              title="Reset View"
              className="p-1.5 text-slate-400 hover:text-white rounded hover:bg-slate-700 transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* SVG Canvas Area */}
      <div ref={containerRef} className="relative flex-1 w-full h-full overflow-hidden">
        <svg ref={svgRef} className="w-full h-full select-none" />

        {/* Legend */}
        <div className="absolute bottom-4 left-4 p-3 rounded-xl bg-slate-900/90 border border-slate-800 text-xs backdrop-blur-md shadow-lg pointer-events-none">
          <span className="text-[10px] font-semibold uppercase text-slate-400 tracking-wider block mb-2">
            Node Legend
          </span>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-sky-400" />
              <span className="text-slate-300">File</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-400" />
              <span className="text-slate-300">Class</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
              <span className="text-slate-300">Function</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
              <span className="text-slate-300">Method</span>
            </div>
          </div>
        </div>

        {/* Slide-out Node Inspector Panel */}
        {selectedNode && (
          <div className="absolute top-0 right-0 w-96 h-full bg-slate-900/95 border-l border-slate-800 p-5 overflow-y-auto backdrop-blur-lg shadow-2xl z-20 flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-start justify-between pb-3 border-b border-slate-800">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-2.5 h-2.5 rounded-full"
                      style={{ backgroundColor: getNodeColor(selectedNode) }}
                    />
                    <span className="text-xs uppercase font-bold tracking-wider text-slate-400">
                      {selectedNode.node_type}
                    </span>
                    {cyclicNodeSet.has(selectedNode.id) && (
                      <span className="px-1.5 py-0.5 text-[10px] font-bold rounded bg-rose-500/10 text-rose-400 border border-rose-500/30">
                        In Cycle
                      </span>
                    )}
                  </div>
                  <h3 className="text-base font-bold text-white break-all">{selectedNode.name}</h3>
                </div>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Path */}
              {selectedNode.file_path && (
                <div>
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">File Path</span>
                  <p className="text-xs font-mono text-slate-300 bg-slate-800/80 p-2 rounded-lg mt-1 break-all">
                    {selectedNode.file_path}
                  </p>
                </div>
              )}

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-lg bg-slate-800/60 border border-slate-750">
                  <span className="text-[10px] text-slate-400 uppercase font-medium">Fan-In (Dependents)</span>
                  <p className="text-lg font-bold text-sky-400 mt-0.5">{selectedNode.fan_in}</p>
                </div>
                <div className="p-3 rounded-lg bg-slate-800/60 border border-slate-750">
                  <span className="text-[10px] text-slate-400 uppercase font-medium">Fan-Out (Dependencies)</span>
                  <p className="text-lg font-bold text-indigo-400 mt-0.5">{selectedNode.fan_out}</p>
                </div>
                <div className="p-3 rounded-lg bg-slate-800/60 border border-slate-750">
                  <span className="text-[10px] text-slate-400 uppercase font-medium">Instability (I)</span>
                  <p className="text-lg font-bold text-amber-400 mt-0.5">
                    {selectedNode.instability !== undefined ? selectedNode.instability.toFixed(2) : '0.00'}
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-slate-800/60 border border-slate-750">
                  <span className="text-[10px] text-slate-400 uppercase font-medium">Complexity</span>
                  <p className="text-lg font-bold text-emerald-400 mt-0.5">
                    {selectedNode.complexity !== null && selectedNode.complexity !== undefined
                      ? selectedNode.complexity.toFixed(1)
                      : 'N/A'}
                  </p>
                </div>
              </div>

              {/* Connections breakdown */}
              <div className="space-y-3 pt-2">
                <div>
                  <span className="text-xs font-semibold text-slate-300 flex items-center justify-between">
                    <span>Incoming ({connections.incoming.length})</span>
                    <span className="text-[10px] text-slate-500">Modules importing this</span>
                  </span>
                  <div className="max-h-28 overflow-y-auto mt-1.5 space-y-1">
                    {connections.incoming.length === 0 ? (
                      <p className="text-xs text-slate-500 italic">No incoming dependencies</p>
                    ) : (
                      connections.incoming.map((inc) => (
                        <div
                          key={inc.id}
                          onClick={() => setSelectedNode(inc)}
                          className="flex items-center justify-between p-1.5 text-xs rounded bg-slate-800/40 hover:bg-slate-800 text-slate-300 cursor-pointer transition-colors"
                        >
                          <span className="truncate">{inc.name}</span>
                          <ArrowRight className="w-3 h-3 text-slate-500 shrink-0" />
                        </div>
                      ))
                    )}
                  </div>
                </div>

                <div>
                  <span className="text-xs font-semibold text-slate-300 flex items-center justify-between">
                    <span>Outgoing ({connections.outgoing.length})</span>
                    <span className="text-[10px] text-slate-500">Modules imported by this</span>
                  </span>
                  <div className="max-h-28 overflow-y-auto mt-1.5 space-y-1">
                    {connections.outgoing.length === 0 ? (
                      <p className="text-xs text-slate-500 italic">No outgoing dependencies</p>
                    ) : (
                      connections.outgoing.map((out) => (
                        <div
                          key={out.id}
                          onClick={() => setSelectedNode(out)}
                          className="flex items-center justify-between p-1.5 text-xs rounded bg-slate-800/40 hover:bg-slate-800 text-slate-300 cursor-pointer transition-colors"
                        >
                          <span className="truncate">{out.name}</span>
                          <ArrowRight className="w-3 h-3 text-slate-500 shrink-0" />
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Actions Footer */}
            <div className="pt-4 border-t border-slate-800 space-y-2">
              <button
                onClick={() => onSelectImpactNode(selectedNode.id)}
                className="w-full flex items-center justify-center gap-2 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors"
              >
                <Zap className="w-3.5 h-3.5" />
                <span>Calculate Blast Radius</span>
              </button>
              <button
                onClick={() => onExplainNode(selectedNode.file_path || selectedNode.name)}
                className="w-full flex items-center justify-center gap-2 py-2 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-750 text-indigo-300 border border-indigo-500/30 transition-colors"
              >
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                <span>Explain Module with AI</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

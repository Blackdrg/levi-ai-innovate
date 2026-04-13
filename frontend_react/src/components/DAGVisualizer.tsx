// frontend_react/src/components/DAGVisualizer.tsx
import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import './DAGVisualizer.css';

/**
 * LeviBrain v15.0: Interactive Force-Directed DAG Visualizer.
 * Displays mission nodes and their dependencies in real-time.
 */

interface DAGNode extends d3.SimulationNodeDatum {
  id: string;
  agent: string;
  status: string;
}

interface DAGLink extends d3.SimulationLinkDatum<DAGNode> {
  source: string | DAGNode;
  target: string | DAGNode;
}

interface DAGProps {
  nodes: DAGNode[];
  links: DAGLink[];
  width?: number;
  height?: number;
}

export const DAGVisualizer = ({ nodes, links, width = 800, height = 400 }: DAGProps) => {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove(); // Clear previous render

    const simulation = d3.forceSimulation<DAGNode>(nodes)
      .force("link", d3.forceLink<DAGNode, DAGLink>(links).id((d: DAGNode) => d.id).distance(100))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2));

    const linkSelection = svg.append("g")
      .attr("stroke", "#333")
      .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke-width", 2);

    const nodeSelection = svg.append("g")
      .attr("stroke", "#fff")
      .attr("stroke-width", 1.5)
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr("r", 20)
      .attr("fill", (d: DAGNode) => {
        switch (d.status) {
          case 'completed': return '#00ff00';
          case 'running': return '#00ffcc';
          case 'failed': return '#ff3333';
          default: return '#555';
        }
      })
      .call(d3.drag<SVGCircleElement, DAGNode>()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

    nodeSelection.append("title").text((d: DAGNode) => `${d.id} (${d.agent})`);

    const labelSelection = svg.append("g")
      .selectAll("text")
      .data(nodes)
      .join("text")
      .text((d: DAGNode) => d.agent.split('_')[0])
      .attr("font-size", "10px")
      .attr("fill", "#fff")
      .attr("text-anchor", "middle")
      .attr("dy", ".35em");

    simulation.on("tick", () => {
      linkSelection
        .attr("x1", (d: DAGLink) => (d.source as any).x)
        .attr("y1", (d: DAGLink) => (d.source as any).y)
        .attr("x2", (d: DAGLink) => (d.target as any).x)
        .attr("y2", (d: DAGLink) => (d.target as any).y);

      nodeSelection
        .attr("cx", (d: DAGNode) => (d as any).x)
        .attr("cy", (d: DAGNode) => (d as any).y);

      labelSelection
        .attr("x", (d: DAGNode) => (d as any).x)
        .attr("y", (d: DAGNode) => (d as any).y);
    });

    function dragstarted(event: d3.D3DragEvent<SVGCircleElement, DAGNode, DAGNode>) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }

    function dragged(event: d3.D3DragEvent<SVGCircleElement, DAGNode, DAGNode>) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragended(event: d3.D3DragEvent<SVGCircleElement, DAGNode, DAGNode>) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }

    return () => simulation.stop();
  }, [nodes, links, width, height]);

  return (
    <div className="dag-container">
      <svg ref={svgRef} width={width} height={height}></svg>
    </div>
  );
};

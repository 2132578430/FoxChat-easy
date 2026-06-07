#!/usr/bin/env node
'use strict';

const fs = require('fs');

const inputPath = process.argv[2];
const outputPath = process.argv[3];

if (!inputPath || !outputPath) {
  console.error('Usage: node ua-tour-analyze.js <input.json> <output.json>');
  process.exit(1);
}

try {
  const data = JSON.parse(fs.readFileSync(inputPath, 'utf-8'));
  const { nodes, edges, layers } = data;

  // Build adjacency maps
  const nodeMap = new Map();
  nodes.forEach(n => nodeMap.set(n.id, n));

  const fanIn = new Map();
  const fanOut = new Map();
  const edgesBySource = new Map(); // source -> [{target, type}]
  const edgesByTarget = new Map(); // target -> [{source, type}]

  nodes.forEach(n => {
    fanIn.set(n.id, 0);
    fanOut.set(n.id, 0);
    edgesBySource.set(n.id, []);
    edgesByTarget.set(n.id, []);
  });

  edges.forEach(e => {
    // Fan-in: edges pointing TO a node
    fanIn.set(e.target, (fanIn.get(e.target) || 0) + 1);
    // Fan-out: edges FROM a node
    fanOut.set(e.source, (fanOut.get(e.source) || 0) + 1);
    // Track edges
    if (edgesBySource.has(e.source)) {
      edgesBySource.get(e.source).push({ target: e.target, type: e.type });
    }
    if (edgesByTarget.has(e.target)) {
      edgesByTarget.get(e.target).push({ source: e.source, type: e.type });
    }
  });

  // A. Fan-In Ranking
  const fanInRanking = [...fanIn.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 20)
    .map(([id, count]) => ({
      id,
      fanIn: count,
      name: nodeMap.get(id)?.name || id
    }));

  // B. Fan-Out Ranking
  const fanOutRanking = [...fanOut.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 20)
    .map(([id, count]) => ({
      id,
      fanOut: count,
      name: nodeMap.get(id)?.name || id
    }));

  // C. Entry Point Candidates
  const entryPointNames = [
    'index.ts', 'index.js', 'main.ts', 'main.js', 'app.ts', 'app.js',
    'server.ts', 'server.js', 'mod.rs', 'main.go', 'main.py', 'main.rs',
    'manage.py', 'app.py', 'wsgi.py', 'asgi.py', 'run.py', '__main__.py',
    'Application.java', 'Main.java', 'Program.cs', 'config.ru', 'index.php',
    'App.swift', 'Application.kt', 'main.cpp', 'main.c'
  ];

  const fanOutValues = [...fanOut.values()].filter(v => v > 0).sort((a, b) => a - b);
  const fanOutP90 = fanOutValues[Math.floor(fanOutValues.length * 0.9)] || 0;
  const fanInValues = [...fanIn.values()].sort((a, b) => a - b);
  const fanInP25 = fanInValues[Math.floor(fanInValues.length * 0.25)] || 0;

  const entryScores = nodes.map(n => {
    let score = 0;
    if (n.type === 'file' || n.type === 'service') {
      const name = n.name.toLowerCase();
      if (entryPointNames.some(ep => name === ep.toLowerCase())) score += 3;
      // File at root or one level deep
      const depth = (n.filePath || '').split('/').length;
      if (depth <= 2) score += 1;
      // High fan-out
      if ((fanOut.get(n.id) || 0) >= fanOutP90) score += 1;
      // Low fan-in
      if ((fanIn.get(n.id) || 0) <= fanInP25) score += 1;
    }
    if (n.type === 'document') {
      if (n.name === 'README.md') {
        const depth = (n.filePath || '').split('/').length;
        if (depth <= 1) score += 5;
        else score += 2;
      }
      if (n.name.endsWith('.md') && (n.filePath || '').split('/').length <= 1) score += 2;
    }
    return { id: n.id, score, name: n.name, summary: n.summary || '' };
  });

  const entryPointCandidates = entryScores
    .filter(e => e.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 10);

  // D. BFS from top code entry point
  const topCodeEntry = entryScores
    .filter(e => {
      const n = nodeMap.get(e.id);
      return n && (n.type === 'file' || n.type === 'service') && e.score > 0;
    })
    .sort((a, b) => b.score - a.score)[0];

  const bfsTraversal = { startNode: '', order: [], depthMap: {}, byDepth: {} };

  if (topCodeEntry) {
    bfsTraversal.startNode = topCodeEntry.id;
    const visited = new Set();
    const queue = [{ id: topCodeEntry.id, depth: 0 }];
    visited.add(topCodeEntry.id);

    while (queue.length > 0) {
      const { id, depth } = queue.shift();
      bfsTraversal.order.push(id);
      bfsTraversal.depthMap[id] = depth;
      if (!bfsTraversal.byDepth[depth]) bfsTraversal.byDepth[depth] = [];
      bfsTraversal.byDepth[depth].push(id);

      // Follow imports and calls edges forward
      const outEdges = edgesBySource.get(id) || [];
      for (const edge of outEdges) {
        if ((edge.type === 'imports' || edge.type === 'calls' || edge.type === 'depends_on') && !visited.has(edge.target)) {
          visited.add(edge.target);
          queue.push({ id: edge.target, depth: depth + 1 });
        }
      }
    }
  }

  // E. Non-Code File Inventory
  const nonCodeFiles = {
    documentation: [],
    infrastructure: [],
    data: [],
    config: []
  };

  nodes.forEach(n => {
    const entry = { id: n.id, name: n.name, summary: n.summary || '', type: n.type };
    if (n.type === 'document') {
      nonCodeFiles.documentation.push(entry);
    } else if (n.type === 'service' || n.type === 'pipeline') {
      nonCodeFiles.infrastructure.push(entry);
    } else if (n.type === 'table' || n.type === 'schema' || n.type === 'endpoint') {
      nonCodeFiles.data.push(entry);
    } else if (n.type === 'config') {
      nonCodeFiles.config.push(entry);
    }
  });

  // F. Tightly Coupled Clusters
  // Find bidirectional edges
  const edgeSet = new Set();
  edges.forEach(e => edgeSet.add(`${e.source}->${e.target}`));

  const bidirectionalPairs = [];
  edges.forEach(e => {
    if (edgeSet.has(`${e.target}->${e.source}`) && e.source < e.target) {
      bidirectionalPairs.push([e.source, e.target]);
    }
  });

  // Build clusters from bidirectional pairs
  const clusterMap = new Map(); // node -> cluster index
  const clusters = [];

  for (const [a, b] of bidirectionalPairs) {
    const clusterA = clusterMap.get(a);
    const clusterB = clusterMap.get(b);
    if (clusterA !== undefined && clusterB !== undefined) {
      if (clusterA !== clusterB) {
        // Merge clusters
        const sourceCluster = clusters[clusterA];
        const targetCluster = clusters[clusterB];
        for (const node of targetCluster) {
          sourceCluster.add(node);
          clusterMap.set(node, clusterA);
        }
        clusters[clusterB] = null;
      }
    } else if (clusterA !== undefined) {
      clusters[clusterA].add(b);
      clusterMap.set(b, clusterA);
    } else if (clusterB !== undefined) {
      clusters[clusterB].add(a);
      clusterMap.set(a, clusterB);
    } else {
      const idx = clusters.length;
      const newCluster = new Set([a, b]);
      clusters.push(newCluster);
      clusterMap.set(a, idx);
      clusterMap.set(b, idx);
    }
  }

  // Expand clusters: add nodes that connect to 2+ existing cluster members
  let changed = true;
  while (changed) {
    changed = false;
    for (const cluster of clusters) {
      if (!cluster) continue;
      for (const n of nodes) {
        if (cluster.has(n.id)) continue;
        const outEdges = edgesBySource.get(n.id) || [];
        const inEdges = edgesByTarget.get(n.id) || [];
        const connections = new Set();
        outEdges.forEach(e => { if (cluster.has(e.target)) connections.add(e.target); });
        inEdges.forEach(e => { if (cluster.has(e.source)) connections.add(e.source); });
        if (connections.size >= 2 && cluster.size < 8) {
          cluster.add(n.id);
          clusterMap.set(n.id, clusters.indexOf(cluster));
          changed = true;
        }
      }
    }
  }

  // Count edges within each cluster
  const clusterResults = clusters
    .filter(c => c && c.size >= 2 && c.size <= 8)
    .map(c => {
      const nodeIds = [...c];
      let edgeCount = 0;
      for (const e of edges) {
        if (c.has(e.source) && c.has(e.target)) edgeCount++;
      }
      return { nodes: nodeIds, edgeCount, size: nodeIds.length };
    })
    .sort((a, b) => b.edgeCount - a.edgeCount)
    .slice(0, 10);

  // G. Layer List
  const layerList = {
    count: layers.length,
    list: layers.map(l => ({ id: l.id, name: l.name, description: l.description || '' }))
  };

  // H. Node Summary Index
  const nodeSummaryIndex = {};
  nodes.forEach(n => {
    nodeSummaryIndex[n.id] = {
      name: n.name,
      type: n.type,
      summary: n.summary || '',
      filePath: n.filePath || ''
    };
  });

  // Output
  const result = {
    scriptCompleted: true,
    entryPointCandidates,
    fanInRanking,
    fanOutRanking,
    bfsTraversal,
    nonCodeFiles,
    clusters: clusterResults,
    layers: layerList,
    nodeSummaryIndex,
    totalNodes: nodes.length,
    totalEdges: edges.length
  };

  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2), 'utf-8');
  console.log('Analysis complete. Output written to', outputPath);
  process.exit(0);

} catch (err) {
  console.error('Error:', err.message);
  process.exit(1);
}

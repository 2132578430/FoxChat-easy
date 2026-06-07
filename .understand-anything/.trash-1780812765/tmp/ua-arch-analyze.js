const fs = require('fs');

const inputPath = process.argv[2];
const outputPath = process.argv[3];

if (!inputPath || !outputPath) {
  console.error('Usage: node ua-arch-analyze.js <input.json> <output.json>');
  process.exit(1);
}

try {
  const data = JSON.parse(fs.readFileSync(inputPath, 'utf-8'));
  const { fileNodes, importEdges, allEdges } = data;

  // A. Directory Grouping - monorepo-aware
  // First, detect top-level project directories
  const topDirs = new Set();
  fileNodes.forEach(n => {
    const parts = n.filePath.split('/');
    topDirs.add(parts[0]);
  });

  // For monorepo projects (FoxChat-java, FoxChatRAG-python, FoxChat-vue),
  // group by sub-module. For others, group by first dir.
  function getGroup(filePath) {
    const parts = filePath.split('/');

    // FoxChat-java: group by foxChat-* module
    if (parts[0] === 'FoxChat-java') {
      if (parts.length <= 2) return 'FoxChat-java:root';
      const module = parts[1]; // foxChat-common, foxChat-pojo, etc.
      if (module.startsWith('foxChat-')) return `FoxChat-java:${module}`;
      if (module === '.mvn') return 'FoxChat-java:root';
      return 'FoxChat-java:root';
    }

    // FoxChatRAG-python: group by app/* subdirectory (2 levels deep)
    if (parts[0] === 'FoxChatRAG-python') {
      if (parts.length <= 2) return 'FoxChatRAG-python:root';
      if (parts[1] === 'proto') return 'FoxChatRAG-python:proto';
      if (parts[1] === 'test') return 'FoxChatRAG-python:test';
      if (parts[1] === 'openspec') return 'FoxChatRAG-python:openspec';
      if (parts[1] === 'app') {
        if (parts.length <= 3) return 'FoxChatRAG-python:app';
        // Group by app/{module} - use 2 levels for deeper nesting
        const subModule = parts[2];
        // For service/chat/* group deeper
        if (subModule === 'service' && parts.length > 4) {
          return `FoxChatRAG-python:app/service/${parts[3]}`;
        }
        return `FoxChatRAG-python:app/${subModule}`;
      }
      return 'FoxChatRAG-python:root';
    }

    // FoxChat-vue: group by src/* subdirectory
    if (parts[0] === 'FoxChat-vue') {
      if (parts.length <= 2) return 'FoxChat-vue:root';
      if (parts[1] === 'src') {
        if (parts.length <= 3) return 'FoxChat-vue:src';
        // Group by src/{module}
        return `FoxChat-vue:src/${parts[2]}`;
      }
      if (parts[1] === 'electron') return 'FoxChat-vue:electron';
      if (parts[1] === 'frontend') return 'FoxChat-vue:frontend';
      return 'FoxChat-vue:root';
    }

    // deploy/* group by subdir
    if (parts[0] === 'deploy') {
      if (parts.length > 2) return `deploy:${parts[1]}`;
      return 'deploy:root';
    }

    // docs/*
    if (parts[0] === 'docs') return 'docs';

    // openspec/*
    if (parts[0] === 'openspec') return 'openspec';

    // .github, .gitea
    if (parts[0] === '.github') return 'ci-cd';
    if (parts[0] === '.gitea') return 'ci-cd';

    // .reasonix, .understand-anything - tooling artifacts
    if (parts[0].startsWith('.')) return 'tooling';

    // Root files
    if (parts.length === 1) return 'root';

    return parts[0];
  }

  const directoryGroups = {};
  for (const node of fileNodes) {
    const group = getGroup(node.filePath);
    if (!directoryGroups[group]) directoryGroups[group] = [];
    directoryGroups[group].push(node.id);
  }

  // B. Node Type Grouping
  const nodeTypeGroups = {};
  for (const node of fileNodes) {
    if (!nodeTypeGroups[node.type]) nodeTypeGroups[node.type] = [];
    nodeTypeGroups[node.type].push(node.id);
  }

  // C. Import Adjacency
  const fileFanIn = {};
  const fileFanOut = {};
  for (const node of fileNodes) {
    fileFanIn[node.id] = 0;
    fileFanOut[node.id] = 0;
  }
  for (const edge of importEdges) {
    if (fileFanOut[edge.source] !== undefined) fileFanOut[edge.source]++;
    if (fileFanIn[edge.target] !== undefined) fileFanIn[edge.target]++;
  }

  // D. Cross-Category Edge Analysis
  const crossCatMap = {};
  for (const edge of allEdges) {
    const srcNode = fileNodes.find(n => n.id === edge.source);
    const tgtNode = fileNodes.find(n => n.id === edge.target);
    if (!srcNode || !tgtNode) continue;
    const key = `${srcNode.type} -> ${tgtNode.type}: ${edge.type}`;
    if (!crossCatMap[key]) crossCatMap[key] = { fromType: srcNode.type, toType: tgtNode.type, edgeType: edge.type, count: 0 };
    crossCatMap[key].count++;
  }
  const crossCategoryEdges = Object.values(crossCatMap);

  // E. Inter-Group Import Frequency
  const nodeIdToGroup = {};
  for (const [group, ids] of Object.entries(directoryGroups)) {
    for (const id of ids) nodeIdToGroup[id] = group;
  }
  const interGroupMap = {};
  for (const edge of importEdges) {
    const srcGroup = nodeIdToGroup[edge.source];
    const tgtGroup = nodeIdToGroup[edge.target];
    if (!srcGroup || !tgtGroup) continue;
    if (srcGroup === tgtGroup) continue;
    const key = `${srcGroup} -> ${tgtGroup}`;
    if (!interGroupMap[key]) interGroupMap[key] = { from: srcGroup, to: tgtGroup, count: 0 };
    interGroupMap[key].count++;
  }
  const interGroupImports = Object.values(interGroupMap).sort((a, b) => b.count - a.count);

  // F. Intra-Group Import Density
  const intraGroupDensity = {};
  for (const [group, ids] of Object.entries(directoryGroups)) {
    const idSet = new Set(ids);
    let internalEdges = 0;
    let totalEdges = 0;
    for (const edge of importEdges) {
      const srcIn = idSet.has(edge.source);
      const tgtIn = idSet.has(edge.target);
      if (srcIn || tgtIn) {
        totalEdges++;
        if (srcIn && tgtIn) internalEdges++;
      }
    }
    intraGroupDensity[group] = {
      internalEdges,
      totalEdges,
      density: totalEdges > 0 ? Math.round((internalEdges / totalEdges) * 100) / 100 : 0
    };
  }

  // G. Pattern Matching
  function getPatternForGroup(group) {
    const lower = group.toLowerCase();

    // Java Spring Boot modules
    if (lower.includes('web') || lower.includes('controller')) return 'api';
    if (lower.includes('service') && !lower.includes('client')) return 'service';
    if (lower.includes('pojo') || lower.includes('dto') || lower.includes('vo') || lower.includes('domain')) return 'types';
    if (lower.includes('common') || lower.includes('util')) return 'utility';
    if (lower.includes('netty') || lower.includes('handler') || lower.includes('interceptor')) return 'middleware';
    if (lower.includes('config') || lower.includes('settings')) return 'config';
    if (lower.includes('mapper') || lower.includes('repository') || lower.includes('model') || lower.includes('data')) return 'data';

    // Python modules
    if (lower.includes('/api') || lower.includes('api/')) return 'api';
    if (lower.includes('/schemas') || lower.includes('schemas/')) return 'types';
    if (lower.includes('/models') || lower.includes('models/')) return 'data';
    if (lower.includes('/core') || lower.includes('core/')) return 'service';
    if (lower.includes('/service') || lower.includes('service/')) return 'service';
    if (lower.includes('/common') || lower.includes('common/')) return 'utility';
    if (lower.includes('/util') || lower.includes('util/')) return 'utility';
    if (lower.includes('/exception') || lower.includes('exception/')) return 'middleware';
    if (lower.includes('/grpc') || lower.includes('grpc/')) return 'middleware';
    if (lower.includes('/retriever') || lower.includes('retriever/')) return 'service';
    if (lower.includes('/chroma') || lower.includes('chroma/')) return 'data';
    if (lower.includes('/proto') || lower.includes('proto/')) return 'types';
    if (lower.includes('test')) return 'test';

    // Vue modules
    if (lower.includes('/components') || lower.includes('components/')) return 'ui';
    if (lower.includes('/views') || lower.includes('views/')) return 'ui';
    if (lower.includes('/composables') || lower.includes('composables/')) return 'service';
    if (lower.includes('/router') || lower.includes('router/')) return 'config';
    if (lower.includes('/store') || lower.includes('store/')) return 'state';
    if (lower.includes('/electron') || lower.includes('electron/')) return 'infrastructure';

    // Infrastructure
    if (lower.includes('deploy') || lower.includes('infra')) return 'infrastructure';
    if (lower.includes('ci-cd') || lower.includes('.gitea')) return 'ci-cd';
    if (lower.includes('docs') || lower.includes('openspec')) return 'documentation';
    if (lower.includes('root')) return 'config';
    if (lower.includes('tooling')) return 'config';

    return null;
  }

  const patternMatches = {};
  for (const group of Object.keys(directoryGroups)) {
    const pattern = getPatternForGroup(group);
    if (pattern) patternMatches[group] = pattern;
  }

  // H. Deployment Topology
  const allPaths = fileNodes.map(n => n.filePath);
  const hasDockerfile = allPaths.some(p => /Dockerfile/i.test(p));
  const hasCompose = allPaths.some(p => /docker-compose/i.test(p));
  const hasK8s = allPaths.some(p => /k8s|kubernetes/i.test(p));
  const hasTerraform = allPaths.some(p => /\.tf$/i.test(p));
  const hasCI = allPaths.some(p => /\.github|\.gitlab|\.circleci|\.gitea|Jenkinsfile/i.test(p));
  const infraFiles = allPaths.filter(p =>
    /Dockerfile|docker-compose|\.github|\.gitlab|\.circleci|\.gitea|Jenkinsfile|deploy/i.test(p)
  );

  const deploymentTopology = {
    hasDockerfile, hasCompose, hasK8s, hasTerraform, hasCI,
    infraFiles: infraFiles.slice(0, 30)
  };

  // I. Data Pipeline Detection
  const schemaFiles = allPaths.filter(p => /\.(graphql|gql|proto|prisma)$/i.test(p));
  const migrationFiles = allPaths.filter(p => /migration/i.test(p));
  const dataModelFiles = allPaths.filter(p => /(model|entity|domain)/i.test(p) && /\.(java|py|ts|js)$/i.test(p));
  const apiHandlerFiles = allPaths.filter(p => /(controller|handler|router|api)/i.test(p) && /\.(java|py|ts|js)$/i.test(p));

  const dataPipeline = {
    schemaFiles: schemaFiles.slice(0, 20),
    migrationFiles: migrationFiles.slice(0, 20),
    dataModelFiles: dataModelFiles.slice(0, 30),
    apiHandlerFiles: apiHandlerFiles.slice(0, 30)
  };

  // J. Documentation Coverage
  const groupsWithDocs = new Set();
  for (const node of fileNodes) {
    if (node.type === 'document' || /\.(md|rst)$/i.test(node.name)) {
      const group = nodeIdToGroup[node.id];
      groupsWithDocs.add(group);
    }
  }
  const totalGroups = Object.keys(directoryGroups).length;
  const docCoverage = {
    groupsWithDocs: groupsWithDocs.size,
    totalGroups,
    coverageRatio: Math.round((groupsWithDocs.size / totalGroups) * 100) / 100,
    undocumentedGroups: Object.keys(directoryGroups).filter(g => !groupsWithDocs.has(g))
  };

  // K. Dependency Direction
  const groupPairMap = {};
  for (const edge of importEdges) {
    const srcGroup = nodeIdToGroup[edge.source];
    const tgtGroup = nodeIdToGroup[edge.target];
    if (!srcGroup || !tgtGroup || srcGroup === tgtGroup) continue;
    const pairKey = [srcGroup, tgtGroup].sort().join('|||');
    if (!groupPairMap[pairKey]) groupPairMap[pairKey] = { a: srcGroup, b: tgtGroup, aToB: 0, bToA: 0 };
    if (srcGroup === groupPairMap[pairKey].a) {
      groupPairMap[pairKey].aToB++;
    } else {
      groupPairMap[pairKey].bToA++;
    }
  }
  const dependencyDirection = Object.values(groupPairMap).map(pair => {
    if (pair.aToB >= pair.bToA) {
      return { dependent: pair.b, dependsOn: pair.a };
    } else {
      return { dependent: pair.a, dependsOn: pair.b };
    }
  });

  // File stats
  const filesPerGroup = {};
  for (const [group, ids] of Object.entries(directoryGroups)) {
    filesPerGroup[group] = ids.length;
  }
  const nodeTypeCounts = {};
  for (const [type, ids] of Object.entries(nodeTypeGroups)) {
    nodeTypeCounts[type] = ids.length;
  }

  const result = {
    scriptCompleted: true,
    directoryGroups,
    nodeTypeGroups,
    crossCategoryEdges,
    interGroupImports,
    intraGroupDensity,
    patternMatches,
    deploymentTopology,
    dataPipeline,
    docCoverage,
    dependencyDirection,
    fileStats: {
      totalFileNodes: fileNodes.length,
      filesPerGroup,
      nodeTypeCounts
    },
    fileFanIn: Object.fromEntries(Object.entries(fileFanIn).filter(([k,v]) => v > 0).sort((a,b) => b[1] - a[1]).slice(0, 30)),
    fileFanOut: Object.fromEntries(Object.entries(fileFanOut).filter(([k,v]) => v > 0).sort((a,b) => b[1] - a[1]).slice(0, 30))
  };

  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2), 'utf-8');
  console.log('Analysis complete. Output written to', outputPath);
  process.exit(0);
} catch (err) {
  console.error('Error:', err.message);
  console.error(err.stack);
  process.exit(1);
}

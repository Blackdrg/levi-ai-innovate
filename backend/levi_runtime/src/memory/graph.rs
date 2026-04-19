// backend/levi_runtime/src/memory/graph.rs
use std::collections::{HashMap, HashSet};
use serde::{Serialize, Deserialize};
use anyhow::Result;
use tracing::info;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Node {
    pub id: String,
    pub label: String,
    pub properties: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Edge {
    pub from: String,
    pub to: String,
    pub relationship: String,
}

pub struct MemoryGraph {
    nodes: HashMap<String, Node>,
    edges: Vec<Edge>,
}

impl MemoryGraph {
    pub fn new() -> Self {
        Self {
            nodes: HashMap::new(),
            edges: Vec::new(),
        }
    }

    pub fn add_node(&mut self, node: Node) {
        self.nodes.insert(node.id.clone(), node);
    }

    pub fn add_edge(&mut self, edge: Edge) {
        self.edges.push(edge);
    }

    pub fn get_neighbors(&self, node_id: &str) -> Vec<&Node> {
        self.edges.iter()
            .filter(|e| e.from == node_id)
            .filter_map(|e| self.nodes.get(&e.to))
            .collect()
    }

    pub fn search(&self, query: &str) -> Vec<&Node> {
        info!(" [Graph] Searching for '{}' in cognitive memory graph...", query);
        self.nodes.values()
            .filter(|n| n.label.contains(query) || n.id.contains(query) )
            .collect()
    }
}

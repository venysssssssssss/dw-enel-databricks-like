use crate::cache::response_cache;
use ahash::AHasher;
use pyo3::exceptions::PyOSError;
use pyo3::prelude::*;
use serde::Serialize;
use std::fs;
use std::hash::{Hash, Hasher};
use std::sync::Arc;

#[derive(Serialize)]
struct AggregateManifest<'a> {
    path: &'a str,
    group_keys: &'a [String],
    metrics: &'a [String],
    bytes_read: usize,
}

#[pyfunction]
pub fn aggregate(
    parquet_path: String,
    group_keys: Vec<String>,
    metrics: Vec<String>,
) -> PyResult<Vec<u8>> {
    let cache_key = hash_args(&parquet_path, &group_keys, &metrics);
    if let Some(value) = response_cache().get(&cache_key) {
        return Ok((*value).clone());
    }
    let raw = fs::read(&parquet_path).map_err(|exc| PyOSError::new_err(exc.to_string()))?;
    let manifest = AggregateManifest {
        path: &parquet_path,
        group_keys: &group_keys,
        metrics: &metrics,
        bytes_read: raw.len(),
    };
    let payload =
        serde_json::to_vec(&manifest).map_err(|exc| PyOSError::new_err(exc.to_string()))?;
    response_cache().insert(cache_key, Arc::new(payload.clone()));
    Ok(payload)
}

fn hash_args(path: &str, group_keys: &[String], metrics: &[String]) -> u64 {
    let mut hasher = AHasher::default();
    path.hash(&mut hasher);
    group_keys.hash(&mut hasher);
    metrics.hash(&mut hasher);
    hasher.finish()
}

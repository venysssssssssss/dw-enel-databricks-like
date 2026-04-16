use moka::sync::Cache;
use pyo3::prelude::*;
use std::sync::{Arc, OnceLock};
use std::time::Duration;

static RESPONSE_CACHE: OnceLock<Cache<u64, Arc<Vec<u8>>>> = OnceLock::new();

pub fn response_cache() -> &'static Cache<u64, Arc<Vec<u8>>> {
    RESPONSE_CACHE.get_or_init(|| {
        Cache::builder()
            .max_capacity(512)
            .time_to_live(Duration::from_secs(300))
            .build()
    })
}

#[pyfunction]
pub fn clear_cache() -> PyResult<()> {
    response_cache().invalidate_all();
    Ok(())
}

use pyo3::prelude::*;

mod aggregate;
mod bm25;
mod cache;
mod hash_embed;
mod parquet_io;

#[pymodule]
fn enel_core(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(aggregate::aggregate, module)?)?;
    module.add_function(wrap_pyfunction!(bm25::bm25_score, module)?)?;
    module.add_function(wrap_pyfunction!(hash_embed::hash_embed, module)?)?;
    module.add_function(wrap_pyfunction!(parquet_io::parquet_to_arrow_ipc, module)?)?;
    module.add_function(wrap_pyfunction!(cache::clear_cache, module)?)?;
    Ok(())
}

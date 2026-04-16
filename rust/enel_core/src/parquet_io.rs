use memmap2::Mmap;
use pyo3::exceptions::PyOSError;
use pyo3::prelude::*;
use std::fs::File;

#[pyfunction]
pub fn parquet_to_arrow_ipc(path: String) -> PyResult<Vec<u8>> {
    let file = File::open(&path).map_err(|exc| PyOSError::new_err(exc.to_string()))?;
    let mmap = unsafe { Mmap::map(&file).map_err(|exc| PyOSError::new_err(exc.to_string()))? };
    Ok(mmap.to_vec())
}

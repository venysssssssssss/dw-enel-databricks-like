use murmur3::murmur3_32;
use pyo3::prelude::*;
use rayon::prelude::*;
use std::io::Cursor;
use unicode_segmentation::UnicodeSegmentation;

#[pyfunction]
pub fn hash_embed(texts: Vec<String>, dim: Option<usize>) -> PyResult<Vec<Vec<f32>>> {
    let width = dim.unwrap_or(384).max(1);
    let vectors = texts
        .par_iter()
        .map(|text| {
            let mut vector = vec![0.0_f32; width];
            for token in text.unicode_words() {
                if token.chars().count() <= 2 {
                    continue;
                }
                let lowered = token.to_lowercase();
                let mut cursor = Cursor::new(lowered.as_bytes());
                let hash = murmur3_32(&mut cursor, 0x5eed).unwrap_or(0);
                let bucket = hash as usize % width;
                let sign = if hash & 1 == 0 { 1.0 } else { -1.0 };
                vector[bucket] += sign;
            }
            let norm = vector
                .iter()
                .map(|value| value * value)
                .sum::<f32>()
                .sqrt()
                .max(1.0);
            for value in &mut vector {
                *value /= norm;
            }
            vector
        })
        .collect();
    Ok(vectors)
}

use pyo3::prelude::*;
use rayon::prelude::*;
use std::collections::{HashMap, HashSet};
use unicode_segmentation::UnicodeSegmentation;

const K1: f64 = 1.5;
const B: f64 = 0.75;

#[pyfunction]
pub fn bm25_score(query: &str, docs: Vec<String>) -> PyResult<Vec<f64>> {
    if docs.is_empty() {
        return Ok(Vec::new());
    }
    let query_terms = tokenize(query);
    if query_terms.is_empty() {
        return Ok(vec![0.0; docs.len()]);
    }
    let tokenized: Vec<Vec<String>> = docs.par_iter().map(|doc| tokenize(doc)).collect();
    let avg_len = tokenized.iter().map(|doc| doc.len() as f64).sum::<f64>() / docs.len() as f64;
    let document_frequency = document_frequency(&tokenized, &query_terms);
    let n_docs = docs.len() as f64;
    let scores = tokenized
        .par_iter()
        .map(|doc| {
            if doc.is_empty() {
                return 0.0;
            }
            let mut term_frequency: HashMap<&str, usize> = HashMap::new();
            for token in doc {
                *term_frequency.entry(token.as_str()).or_insert(0) += 1;
            }
            query_terms
                .iter()
                .map(|term| {
                    let tf = *term_frequency.get(term.as_str()).unwrap_or(&0) as f64;
                    if tf == 0.0 {
                        return 0.0;
                    }
                    let df = *document_frequency.get(term).unwrap_or(&0) as f64;
                    let idf = ((n_docs - df + 0.5) / (df + 0.5) + 1.0).ln();
                    let denom = tf + K1 * (1.0 - B + B * doc.len() as f64 / avg_len.max(1.0));
                    idf * (tf * (K1 + 1.0)) / denom
                })
                .sum::<f64>()
        })
        .collect();
    Ok(scores)
}

fn tokenize(text: &str) -> Vec<String> {
    text.unicode_words()
        .filter_map(|token| {
            let lowered = token.to_lowercase();
            if lowered.chars().count() > 2 {
                Some(lowered)
            } else {
                None
            }
        })
        .collect()
}

fn document_frequency(
    tokenized: &[Vec<String>],
    query_terms: &[String],
) -> HashMap<String, usize> {
    let wanted: HashSet<&str> = query_terms.iter().map(String::as_str).collect();
    let mut df: HashMap<String, usize> = HashMap::new();
    for doc in tokenized {
        let seen: HashSet<&str> = doc
            .iter()
            .map(String::as_str)
            .filter(|token| wanted.contains(token))
            .collect();
        for token in seen {
            *df.entry(token.to_string()).or_insert(0) += 1;
        }
    }
    df
}

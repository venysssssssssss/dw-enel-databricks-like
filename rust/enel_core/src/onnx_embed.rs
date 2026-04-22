use ort::session::{builder::GraphOptimizationLevel, Session};
use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use std::path::Path;
use tokenizers::Tokenizer;

#[pyclass]
pub struct OnnxEmbedder {
    session: Session,
    tokenizer: Tokenizer,
}

#[pymethods]
impl OnnxEmbedder {
    #[new]
    pub fn new(model_dir: &str) -> PyResult<Self> {
        let dir_path = Path::new(model_dir);
        let model_path = dir_path.join("model.onnx");
        let tokenizer_path = dir_path.join("tokenizer.json");

        if !model_path.exists() {
            return Err(PyRuntimeError::new_err(format!(
                "Modelo não encontrado: {:?}",
                model_path
            )));
        }
        if !tokenizer_path.exists() {
            return Err(PyRuntimeError::new_err(format!(
                "Tokenizer não encontrado: {:?}",
                tokenizer_path
            )));
        }

        // ort::init() is implicitly handled in ort 2.0+ for default execution providers
        let session = Session::builder()
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?
            .with_intra_threads(4)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?
            .with_optimization_level(GraphOptimizationLevel::Level3)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?
            .commit_from_file(&model_path)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

        let tokenizer = Tokenizer::from_file(&tokenizer_path)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

        Ok(Self { session, tokenizer })
    }

    pub fn embed(&mut self, texts: Vec<String>) -> PyResult<Vec<Vec<f32>>> {
        if texts.is_empty() {
            return Ok(vec![]);
        }

        let batch_size = texts.len();

        // Tokenize without padding first to find max length, or configure padding on tokenizer.
        // For simplicity, we can clone and pad, but it's better to configure it temporarily.
        let mut tokenizer = self.tokenizer.clone();
        tokenizer.with_padding(Some(tokenizers::PaddingParams {
            strategy: tokenizers::PaddingStrategy::BatchLongest,
            ..Default::default()
        }));
        tokenizer
            .with_truncation(Some(tokenizers::TruncationParams {
                max_length: 512,
                ..Default::default()
            }))
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

        let encodings = tokenizer
            .encode_batch(texts, true)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

        let seq_len = encodings[0].get_ids().len();

        let mut input_ids = Vec::with_capacity(batch_size * seq_len);
        let mut attention_mask = Vec::with_capacity(batch_size * seq_len);
        let mut token_type_ids = Vec::with_capacity(batch_size * seq_len);

        for encoding in &encodings {
            let ids = encoding.get_ids();
            let mask = encoding.get_attention_mask();
            let types = encoding.get_type_ids();

            input_ids.extend_from_slice(ids);

            // convert u32 to i64
            for &m in mask {
                attention_mask.push(m as i64);
            }
            for &t in types {
                token_type_ids.push(t as i64);
            }
        }

        // cast input_ids to i64 as ONNX usually expects i64 for these
        let input_ids_i64: Vec<i64> = input_ids.into_iter().map(|x| x as i64).collect();

        let shape = vec![batch_size, seq_len];

        let input_ids_tensor = ort::value::Value::from_array((shape.clone(), input_ids_i64))
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        let attention_mask_tensor =
            ort::value::Value::from_array((shape.clone(), attention_mask.clone()))
                .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        let token_type_ids_tensor = ort::value::Value::from_array((shape, token_type_ids))
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

        let inputs = ort::inputs![
            "input_ids" => input_ids_tensor,
            "attention_mask" => attention_mask_tensor,
            "token_type_ids" => token_type_ids_tensor,
        ];

        let outputs = self
            .session
            .run(inputs)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

        if let Some(sentence_output) = outputs.get("sentence_embedding") {
            let (shape, data) = sentence_output
                .try_extract_tensor::<f32>()
                .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
            let embedding_dim = shape[1] as usize;
            let mut embeddings = Vec::with_capacity(batch_size);

            for i in 0..batch_size {
                let start = i * embedding_dim;
                let end = start + embedding_dim;
                embeddings.push(data[start..end].to_vec());
            }

            return Ok(embeddings);
        }

        // Backward compatibility for older exports: pool last_hidden_state here.
        let (shape, data) = outputs["last_hidden_state"]
            .try_extract_tensor::<f32>()
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

        let hidden_size = shape[2] as usize;

        let mut embeddings = Vec::with_capacity(batch_size);

        for i in 0..batch_size {
            let mut pooled = vec![0.0f32; hidden_size];
            let mut sum_mask = 0.0f32;

            for j in 0..seq_len {
                let mask_val = attention_mask[i * seq_len + j] as f32;
                for k in 0..hidden_size {
                    let val = data[(i * seq_len + j) * hidden_size + k];
                    pooled[k] += val * mask_val;
                }
                sum_mask += mask_val;
            }

            let mut norm = 0.0f32;
            for k in 0..hidden_size {
                if sum_mask > 0.0 {
                    pooled[k] /= sum_mask;
                }
                norm += pooled[k] * pooled[k];
            }

            norm = norm.sqrt();
            if norm > 0.0 {
                for k in 0..hidden_size {
                    pooled[k] /= norm;
                }
            }

            embeddings.push(pooled);
        }

        Ok(embeddings)
    }
}

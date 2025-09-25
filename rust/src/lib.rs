use cedar_policy::{
    Context, Decision, Entities, EntityUid, Policy, PolicySet, Request,
};
use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use std::convert::From;
use std::str::FromStr;
use serde_json::Value as JsonValue;
use regex::Regex;

/// Extract policy ID from Cedar source code with @id annotation
fn extract_policy_id_from_cedar_source(policy_str: &str) -> Option<cedar_policy::PolicyId> {
    // Use regex to find @id("policy_name") pattern
    let re = Regex::new(r#"@id\s*\(\s*"([^"]+)"\s*\)"#).unwrap();
    if let Some(captures) = re.captures(policy_str) {
        if let Some(id_match) = captures.get(1) {
            let id_str = id_match.as_str();
            // Create PolicyId from string
            match cedar_policy::PolicyId::from_str(id_str) {
                Ok(policy_id) => Some(policy_id),
                Err(_) => None,
            }
        } else {
            None
        }
    } else {
        None
    }
}

#[derive(Debug)]
enum CedarError {
    JsonError(String),
    ParseError(String),
    AuthorizationError(String),
    SchemaError(String),
}

impl std::fmt::Display for CedarError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            CedarError::JsonError(s) => write!(f, "JSON Error: {}", s),
            CedarError::ParseError(s) => write!(f, "Parse Error: {}", s),
            CedarError::AuthorizationError(s) => write!(f, "Authorization Error: {}", s),
            CedarError::SchemaError(s) => write!(f, "Schema Error: {}", s),
        }
    }
}

/// Convert Cedar errors to Python exceptions
impl From<CedarError> for PyErr {
    fn from(err: CedarError) -> PyErr {
        PyValueError::new_err(err.to_string())
    }
}

#[pyclass(name = "CedarPolicy")]
struct CedarPolicy {
    policy: Policy,
}


#[pymethods]
impl CedarPolicy {
    #[new]
    fn new(policy_str: &str) -> PyResult<Self> {
        // Detect if the input is JSON or Cedar source format
        let is_json = policy_str.trim_start().starts_with('{');
        
        let policy = if is_json {
            // Parse as JSON (original behavior)
            let json_value: JsonValue = serde_json::from_str(policy_str)
                .map_err(|e| PyValueError::new_err(format!("Failed to parse policy JSON: {}", e)))?;
            
            Policy::from_json(None, json_value)
                .map_err(|e| PyValueError::new_err(format!("Failed to create policy from JSON: {}", e)))?
        } else {
            // Parse as Cedar source code with proper ID handling
            // If the policy has @id annotation, use that, otherwise let Cedar auto-generate
            let policy_id = extract_policy_id_from_cedar_source(policy_str);
            Policy::parse(policy_id, policy_str)
                .map_err(|e| PyValueError::new_err(format!("Failed to parse Cedar policy: {}", e)))?
        };

        Ok(CedarPolicy { policy })
    }

    #[getter]
    fn id(&self) -> &str {
        self.policy.id().as_ref()
    }
}

/// Python wrapper for Cedar PolicySet
#[pyclass(name = "CedarPolicySet")]
struct CedarPolicySet {
    policies: PolicySet,
}

#[pymethods]
impl CedarPolicySet {
    #[new]
    fn new() -> Self {
        Self {
            policies: PolicySet::new(),
        }
    }

    fn add(&mut self, policy: &CedarPolicy) -> PyResult<()> {
        let policy_id_str = policy.policy.id().to_string();
        self.policies.add(policy.policy.clone()).map_err(|e| {
            PyValueError::new_err(format!(
                "Failed to add policy with id '{}'. Cedar error: {}",
                policy_id_str, e
            ))
        })
    }

    fn __repr__(&self) -> PyResult<String> {
        // Count policies manually since policies() returns an iterator without len()
        let count = self.policies.policies().count();
        Ok(format!("CedarPolicySet({} policies)", count))
    }
}

/// Python wrapper for Cedar Authorizer
#[pyclass(name = "CedarAuthorizer")]
struct CedarAuthorizer {
    authorizer: cedar_policy::Authorizer,
}

#[pymethods]
impl CedarAuthorizer {
    #[new]
    fn new() -> Self {
        CedarAuthorizer {
            authorizer: cedar_policy::Authorizer::new(),
        }
    }

    /// Authorize a request
    #[pyo3(signature = (policy_set, principal, action, resource, context_json=None, entities_json=None))]
    fn is_authorized(
        &self,
        policy_set: &CedarPolicySet,
        principal: &str,
        action: &str,
        resource: &str,
        context_json: Option<&str>,
        entities_json: Option<&str>,
    ) -> PyResult<bool> {
        let principal_uid = EntityUid::from_str(principal)
            .map_err(|e| CedarError::ParseError(format!("Invalid principal: {}", e)))?;
        let action_uid = EntityUid::from_str(action)
            .map_err(|e| CedarError::ParseError(format!("Invalid action: {}", e)))?;
        let resource_uid = EntityUid::from_str(resource)
            .map_err(|e| CedarError::ParseError(format!("Invalid resource: {}", e)))?;

        let context = match context_json {
            Some(json_str) => {
                let json_val: JsonValue = serde_json::from_str(json_str)
                    .map_err(|e| CedarError::JsonError(format!("Invalid context JSON: {}", e)))?;
                Context::from_json_value(json_val, None)
                    .map_err(|e| CedarError::JsonError(format!("Failed to create context: {}", e)))?
            },
            None => Context::empty(),
        };

        let entities = match entities_json {
            Some(json_str) => Entities::from_json_str(json_str, None)
                .map_err(|e| CedarError::JsonError(format!("Failed to parse entities JSON: {}", e)))?,
            None => Entities::empty(),
        };

        let request = Request::new(
            principal_uid,
            action_uid,
            resource_uid,
            context,
            None, // No schema
        ).map_err(|e| CedarError::ParseError(format!("Failed to create request: {}", e)))?;

        let response = self.authorizer.is_authorized(&request, &policy_set.policies, &entities);

        Ok(response.decision() == Decision::Allow)
    }

    /// Authorize a request and get a detailed response
    #[pyo3(signature = (policy_set, principal, action, resource, context_json=None, entities_json=None))]
    fn is_authorized_detailed(
        &self,
        policy_set: &CedarPolicySet,
        principal: &str,
        action: &str,
        resource: &str,
        context_json: Option<&str>,
        entities_json: Option<&str>,
    ) -> PyResult<(bool, Vec<String>, Vec<String>)> {
        let principal_uid = EntityUid::from_str(principal)
            .map_err(|e| CedarError::ParseError(format!("Invalid principal: {}", e)))?;
        let action_uid = EntityUid::from_str(action)
            .map_err(|e| CedarError::ParseError(format!("Invalid action: {}", e)))?;
        let resource_uid = EntityUid::from_str(resource)
            .map_err(|e| CedarError::ParseError(format!("Invalid resource: {}", e)))?;

        let context = match context_json {
            Some(json_str) => {
                let json_val: JsonValue = serde_json::from_str(json_str)
                    .map_err(|e| CedarError::JsonError(format!("Invalid context JSON: {}", e)))?;
                Context::from_json_value(json_val, None)
                    .map_err(|e| CedarError::JsonError(format!("Failed to create context: {}", e)))?
            },
            None => Context::empty(),
        };

        let entities = match entities_json {
            Some(json_str) => Entities::from_json_str(json_str, None)
                .map_err(|e| CedarError::JsonError(format!("Failed to parse entities JSON: {}", e)))?,
            None => Entities::empty(),
        };

        let request = Request::new(
            principal_uid,
            action_uid,
            resource_uid,
            context,
            None, // No schema
        ).map_err(|e| CedarError::ParseError(format!("Failed to create request: {}", e)))?;

        let response = self.authorizer.is_authorized(&request, &policy_set.policies, &entities);

        let allowed = response.decision() == Decision::Allow;
        let reasons: Vec<String> = response.diagnostics().reason().map(|p| p.to_string()).collect();
        let errors: Vec<String> = response.diagnostics().errors().map(|e| e.to_string()).collect();

        Ok((allowed, reasons, errors))
    }
}

/// A Python module implemented in Rust.
#[pymodule]
fn _rust(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<CedarPolicy>()?;
    m.add_class::<CedarPolicySet>()?;
    m.add_class::<CedarAuthorizer>()?;
    Ok(())
}

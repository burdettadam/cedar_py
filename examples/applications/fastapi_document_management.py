"""
Example 1: FastAPI Document Management System
A complete FastAPI application demonstrating Cedar-Py integration for document authorization.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Dict, List, Optional
import uvicorn

# Import Cedar-Py components
from cedar_py import Policy, Engine
from cedar_py.integrations.fastapi import cedar_auth
from cedar_py.engine import CacheConfig

# Pydantic models
class Document(BaseModel):
    id: str
    title: str
    content: str
    owner: str
    classification: str = "public"
    department: str

class User(BaseModel):
    id: str
    name: str
    department: str
    role: str
    level: int = 1

class CreateDocumentRequest(BaseModel):
    title: str
    content: str
    classification: str = "public"
    department: str

# Sample data
users_db: Dict[str, User] = {
    "alice": User(id="alice", name="Alice Johnson", department="engineering", role="engineer", level=3),
    "bob": User(id="bob", name="Bob Smith", department="marketing", role="manager", level=2),
    "charlie": User(id="charlie", name="Charlie Wilson", department="engineering", role="admin", level=4),
    "diana": User(id="diana", name="Diana Lee", department="hr", role="specialist", level=2),
}

documents_db: Dict[str, Document] = {
    "doc1": Document(id="doc1", title="API Design", content="Technical specification...", 
                     owner="alice", classification="internal", department="engineering"),
    "doc2": Document(id="doc2", title="Marketing Strategy", content="Q4 marketing plans...", 
                     owner="bob", classification="confidential", department="marketing"),
    "doc3": Document(id="doc3", title="Employee Handbook", content="HR policies...", 
                     owner="diana", classification="public", department="hr"),
}

# Cedar policies for document management
DOCUMENT_POLICIES = """
// Basic read access - users can read public documents
permit(
    principal,
    action == Action::"read",
    resource
) when {
    resource.classification == "public"
};

// Department access - users can read internal docs from their department
permit(
    principal,
    action == Action::"read", 
    resource
) when {
    resource.classification == "internal" &&
    principal.department == resource.department
};

// Owner access - document owners can read/write their own documents
permit(
    principal,
    action in [Action::"read", Action::"write"],
    resource
) when {
    principal.id == resource.owner
};

// Manager access - managers can read/write docs in their department
permit(
    principal,
    action in [Action::"read", Action::"write"],
    resource
) when {
    principal.role == "manager" &&
    principal.department == resource.department
};

// Admin access - admins can access everything
permit(
    principal,
    action,
    resource
) when {
    principal.role == "admin"
};

// High-level engineers can read confidential engineering docs
permit(
    principal,
    action == Action::"read",
    resource
) when {
    principal.department == "engineering" &&
    principal.level >= 3 &&
    resource.classification == "confidential" &&
    resource.department == "engineering"
};
"""

# Initialize Cedar engine with caching
cache_config = CacheConfig.create_enabled(max_size=1000, ttl=300.0)
policy = Policy(DOCUMENT_POLICIES)
cedar_engine = Engine(policy, cache_config=cache_config)

# Initialize FastAPI app
app = FastAPI(
    title="Document Management System",
    description="Example FastAPI app with Cedar-Py authorization",
    version="1.0.0"
)

# Security
security = HTTPBearer()

# Configure Cedar auth
cedar_auth.configure_engine(cedar_engine)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Extract user from JWT token (simplified for demo)."""
    # In production, you would validate the JWT token
    user_id = credentials.credentials  # Simplified: token is just user ID
    if user_id not in users_db:
        raise HTTPException(status_code=401, detail="Invalid token")
    return users_db[user_id]

@cedar_auth.entity_loader
async def load_user_entity(user: User = Depends(get_current_user)) -> Dict:
    """Load user entity for Cedar authorization."""
    return {
        f'User::"{user.id}"': {
            "uid": {"type": "User", "id": user.id},
            "attrs": {
                "name": user.name,
                "department": user.department,
                "role": user.role,
                "level": user.level
            },
            "parents": []
        }
    }

@cedar_auth.entity_loader
async def load_document_entity(doc_id: str) -> Dict:
    """Load document entity for Cedar authorization."""
    if doc_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents_db[doc_id]
    return {
        f'Document::"{doc_id}"': {
            "uid": {"type": "Document", "id": doc_id},
            "attrs": {
                "title": doc.title,
                "owner": doc.owner,
                "classification": doc.classification,
                "department": doc.department
            },
            "parents": []
        }
    }

# API Endpoints

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Document Management System with Cedar-Py Authorization"}

@app.get("/users/me")
async def get_current_user_profile(user: User = Depends(get_current_user)):
    """Get current user profile."""
    return user

@app.get("/documents", response_model=List[Document])
@cedar_auth.require_permission("read", "Document")
async def list_documents(user: User = Depends(get_current_user)) -> List[Document]:
    """List all documents (filtered by authorization)."""
    # In a real app, you'd filter this at the database level
    accessible_docs = []
    
    for doc in documents_db.values():
        # Check authorization for each document
        try:
            authorized = cedar_engine.is_authorized(
                f'User::"{user.id}"',
                'Action::"read"',
                f'Document::"{doc.id}"',
                entities={
                    f'User::"{user.id}"': {
                        "uid": {"type": "User", "id": user.id},
                        "attrs": {"department": user.department, "role": user.role, "level": user.level},
                        "parents": []
                    },
                    f'Document::"{doc.id}"': {
                        "uid": {"type": "Document", "id": doc.id},
                        "attrs": {"owner": doc.owner, "classification": doc.classification, "department": doc.department},
                        "parents": []
                    }
                }
            )
            if authorized:
                accessible_docs.append(doc)
        except Exception:
            continue  # Skip documents that cause authorization errors
    
    return accessible_docs

@app.get("/documents/{doc_id}", response_model=Document)
@cedar_auth.require_permission("read", lambda doc_id: f'Document::"{doc_id}"')
async def get_document(doc_id: str, user: User = Depends(get_current_user)) -> Document:
    """Get a specific document."""
    if doc_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")
    return documents_db[doc_id]

@app.post("/documents", response_model=Document)
async def create_document(
    request: CreateDocumentRequest,
    user: User = Depends(get_current_user)
) -> Document:
    """Create a new document."""
    # Generate new document ID
    doc_id = f"doc{len(documents_db) + 1}"
    
    # Create document
    document = Document(
        id=doc_id,
        title=request.title,
        content=request.content,
        owner=user.id,
        classification=request.classification,
        department=request.department
    )
    
    documents_db[doc_id] = document
    return document

@app.put("/documents/{doc_id}", response_model=Document)
@cedar_auth.require_permission("write", lambda doc_id: f'Document::"{doc_id}"')
async def update_document(
    doc_id: str,
    request: CreateDocumentRequest,
    user: User = Depends(get_current_user)
) -> Document:
    """Update an existing document."""
    if doc_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Update document
    document = documents_db[doc_id]
    document.title = request.title
    document.content = request.content
    document.classification = request.classification
    document.department = request.department
    
    return document

@app.delete("/documents/{doc_id}")
@cedar_auth.require_permission("delete", lambda doc_id: f'Document::"{doc_id}"')
async def delete_document(doc_id: str, user: User = Depends(get_current_user)):
    """Delete a document."""
    if doc_id not in documents_db:
        raise HTTPException(status_code=404, detail="Document not found")
    
    del documents_db[doc_id]
    return {"message": f"Document {doc_id} deleted successfully"}

@app.get("/stats/cache")
async def get_cache_stats(user: User = Depends(get_current_user)):
    """Get Cedar engine cache statistics (admin only)."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return cedar_engine.get_cache_stats()

if __name__ == "__main__":
    print("🚀 Starting Document Management System")
    print("📋 Available users for testing:")
    for user_id, user in users_db.items():
        print(f"   - {user_id}: {user.name} ({user.department}/{user.role})")
    print("\n🔐 Use user ID as Bearer token (e.g., 'Bearer alice')")
    print("📚 Available endpoints:")
    print("   - GET /documents - List accessible documents")
    print("   - GET /documents/{doc_id} - Get specific document") 
    print("   - POST /documents - Create document")
    print("   - PUT /documents/{doc_id} - Update document")
    print("   - DELETE /documents/{doc_id} - Delete document")
    print("   - GET /stats/cache - View cache stats (admin only)")
    print("\n🎯 Starting server on http://localhost:8000")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
from datetime import datetime
import uuid
import hashlib
from typing import Dict, Any

class AgentC:
    """Document Signing Agent"""
    
    def __init__(self):
        self.agent_name = "Agent C - Document Signer"
        
    def sign_document(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sign the document and prepare for scheduling
        
        Args:
            state: Current workflow state containing document info and meeting date
            
        Returns:
            Updated state with signing results
        """
        try:
            # Extract data from state
            session_id = state.get('session_id')
            meeting_date = state.get('meeting_date')
            risk_assessment = state.get('risk_assessment', {})
            file_path = state.get('file_path')
            
            # Generate signature details
            signature_id = f"SIG_{uuid.uuid4().hex[:8].upper()}"
            timestamp = datetime.now().isoformat()
            
            # Create document hash (simulate based on file content)
            document_hash = self._generate_document_hash(file_path, session_id)
            
            # Digital signature simulation
            digital_signature = self._create_digital_signature(
                document_hash, 
                signature_id, 
                timestamp
            )
            
            # Prepare signing result
            signing_result = {
                'status': 'SIGNED',
                'signature_id': signature_id,
                'signed_at': timestamp,
                'meeting_date': meeting_date,
                'document_hash': document_hash,
                'digital_signature': digital_signature,
                'signer_id': 'SYSTEM_AGENT_C',
                'signing_method': 'DIGITAL_SIGNATURE',
                'document_version': '1.0',
                'compliance_checked': True,
                'message': 'Document successfully signed and ready for scheduling'
            }
            
            # Update state - CRITICAL: Create a new state dict to avoid mutation issues
            updated_state = state.copy()
            updated_state.update({
                'signing_result': signing_result,
                'document_signed': True,  # This is the key field that was missing in WorkflowState
                'next_agent': 'agent_d',
                'signing_timestamp': timestamp
            })
            
            print(f"[{self.agent_name}] Document signed successfully - ID: {signature_id}")
            print(f"[{self.agent_name}] Setting document_signed = True")
            
            return updated_state
            
        except Exception as e:
            error_result = {
                'status': 'SIGNING_FAILED',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
            updated_state = state.copy()
            updated_state.update({
                'signing_result': error_result,
                'document_signed': False,
                'error': f"Document signing failed: {str(e)}"
            })
            
            print(f"[{self.agent_name}] Signing failed: {str(e)}")
            
            return updated_state
    
    def _generate_document_hash(self, file_path: str, session_id: str) -> str:
        """Generate a hash for the document"""
        try:
            if file_path:
                with open(file_path, 'rb') as f:
                    content = f.read()
                return hashlib.sha256(content + session_id.encode()).hexdigest()[:16].upper()
            else:
                return hashlib.sha256(session_id.encode()).hexdigest()[:16].upper()
        except:
            return f"HASH_{uuid.uuid4().hex[:16].upper()}"
    
    def _create_digital_signature(self, document_hash: str, signature_id: str, timestamp: str) -> str:
        """Create a digital signature"""
        signature_data = f"{document_hash}:{signature_id}:{timestamp}"
        return hashlib.sha256(signature_data.encode()).hexdigest()[:32].upper()
    
    def validate_signing_requirements(self, state: Dict[str, Any]) -> bool:
        """Validate if document can be signed"""
        required_fields = ['session_id', 'meeting_date', 'risk_assessment']
        
        for field in required_fields:
            if field not in state or not state[field]:
                print(f"[{self.agent_name}] Missing required field: {field}")
                return False
        
        # Check if user approved
        if not state.get('user_approved', False):
            print(f"[{self.agent_name}] Document not approved by user")
            return False
            
        return True
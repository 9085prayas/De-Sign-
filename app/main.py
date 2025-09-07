from flask import Flask, request, jsonify, g
from flask_cors import CORS
import os
from datetime import datetime
import uuid
from werkzeug.utils import secure_filename

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Fix imports
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Rest of your imports...
from auth.descope_auth import require_auth, DescopeAuth
from workflow import DocumentWorkflow, WorkflowState
from agents.agent_b import AgentB


# Initialize Flask app
app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize components
workflow_manager = DocumentWorkflow()
agent_b = AgentB()
auth_handler = DescopeAuth()

# In-memory storage (use database in production)
sessions = {}

@app.route('/', methods=['GET'])
def home():
    """Health check endpoint"""
    return jsonify({
        'message': 'Multi-Agent Document Processing API',
        'status': 'running',
        'version': '1.0',
        
    })

@app.route('/auth/profile', methods=['GET'])
@require_auth()
def get_profile():
    """Get user profile"""
    return jsonify({
        'user': g.current_user,
        'permissions': auth_handler.permissions,
        'message': 'Authentication successful'
    })

@app.route('/upload', methods=['POST'])
@require_auth(permission='upload_file')
def upload_file():
    """Step 1: Handle file upload and risk assessment"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Create uploads directory if it doesn't exist
        upload_dir = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save file
        filename = secure_filename(file.filename)
        session_id = str(uuid.uuid4())
        file_path = os.path.join(upload_dir, f"{session_id}_{filename}")
        file.save(file_path)
        
        print(f"File saved to: {file_path}")
        
        # Agent B: Risk Assessment
        agent_b_instance = AgentB()
        
        # Validate file
        if not agent_b_instance.validate_file_for_analysis(file_path):
            os.remove(file_path)  # Clean up
            return jsonify({'error': 'Invalid file type or size'}), 400
        
        # Analyze file
        risk_assessment = agent_b_instance.analyze_file(file_path, {
            'user_id': g.current_user['user_id'],
            'upload_time': datetime.now().isoformat()
        })
        
        # Store session data
        sessions[session_id] = {
            'user_id': g.current_user['user_id'],
            'user_email': g.current_user['email'],
            'file_path': file_path,
            'filename': filename,
            'risk_assessment': risk_assessment,
            'created_at': datetime.now().isoformat(),
            'status': 'analyzed'
        }
        
        print(f"Session created: {session_id}")
        
        return jsonify({
            'session_id': session_id,
            'risk_assessment': risk_assessment,
            'status': 'analysis_complete',
            'user': g.current_user['email']
        })
        
    except Exception as e:
        print(f"Upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/start-workflow', methods=['POST'])
@require_auth(permission='upload_file')
def start_workflow():
    """Step 2: Start workflow after risk assessment"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'error': 'Session ID is required'}), 400
        
        if session_id not in sessions:
            return jsonify({'error': 'Invalid session ID'}), 400
        
        session_data = sessions[session_id]
        
        # Check if user owns this session
        if session_data['user_id'] != g.current_user['user_id']:
            return jsonify({'error': 'Unauthorized access to session'}), 403
        
        # Create initial workflow state
        initial_state = WorkflowState(
            session_id=session_id,
            user_id=g.current_user['user_id'],
            file_path=session_data.get('file_path', ''),
            filename=session_data.get('filename', ''),
            risk_assessment=session_data.get('risk_assessment', {}),
            user_approved=False,
            meeting_date='',
            signing_result={},
            scheduling_result={},
            workflow_complete=False,
            final_status='',
            error='',
            waiting_for_input=True,
            input_type='',
            human_input=None,
            next_node=''
        )
        
        print(f"Starting workflow for session: {session_id}")
        
        # Start the workflow
        result = workflow_manager.start_workflow(initial_state)
        
        # Update session
        sessions[session_id]['workflow_state'] = result
        sessions[session_id]['status'] = 'workflow_started'
        
        print(f"Workflow started, waiting for: {result.get('input_type', 'unknown')}")
        
        return jsonify({
            'session_id': session_id,
            'workflow_started': True,
            'waiting_for_input': result.get('waiting_for_input', False),
            'input_type': result.get('input_type', ''),
            'risk_assessment': session_data.get('risk_assessment', {}),
            'message': 'Workflow started. Please review the risk assessment and approve or reject.'
        })
        
    except Exception as e:
        print(f"Start workflow error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/provide-input', methods=['POST'])
@require_auth()
def provide_input():
    """Step 3: Provide human input to continue workflow"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        input_data = data.get('input_data')
        
        print(f"[DEBUG] Available sessions: {list(sessions.keys())}")
        print(f"[DEBUG] Requested session: {session_id}")
        
        if not session_id or not input_data:
            return jsonify({'error': 'Session ID and input data are required'}), 400

        if session_id not in sessions:
            print(f"[ERROR] Session {session_id} not found in sessions")
            return jsonify({'error': 'Invalid session ID'}), 400

        # Get current workflow state
        current_state = workflow_manager.get_workflow_state(session_id)
        if not current_state:
            print(f"[ERROR] No workflow state found for session: {session_id}")
            
            # Try to check if session exists in sessions but not in workflow
            if session_id in sessions:
                print("[DEBUG] Session exists in sessions but no LangGraph state")
                return jsonify({'error': 'Workflow was not started properly. Please restart the workflow.'}), 400
            else:
                return jsonify({'error': 'No active workflow found'}), 400
        
        # Continue with existing logic...

        
        # Validate input based on expected type
        input_type = current_state.get('input_type')
        
        print(f"Providing input for session: {session_id}, type: {input_type}, data: {input_data}")
        
        if input_type == 'approval':
            if 'approved' not in input_data:
                return jsonify({'error': 'Approval decision required'}), 400
        elif input_type == 'meeting_date':
            if 'meeting_date' not in input_data or not input_data['meeting_date']:
                return jsonify({'error': 'Meeting date required'}), 400
        
        # Continue workflow with input
        result = workflow_manager.continue_workflow(session_id, input_data)
        
        # Update session
        sessions[session_id]['workflow_state'] = result
        
        # Prepare response based on workflow state
        response = {
            'session_id': session_id,
            'workflow_complete': result.get('workflow_complete', False),
            'waiting_for_input': result.get('waiting_for_input', False),
            'input_type': result.get('input_type', ''),
            'final_status': result.get('final_status', ''),
        }
        
        # Add specific results if available
        if result.get('signing_result'):
            response['signing_result'] = result['signing_result']
        
        if result.get('scheduling_result'):
            response['scheduling_result'] = result['scheduling_result']
        
        if result.get('error'):
            response['error'] = result['error']
        
        # Add appropriate message
        if result.get('workflow_complete'):
            if result.get('final_status') == 'SUCCESS':
                response['message'] = 'Workflow completed successfully!'
                response['final_response'] = 'YES'
                sessions[session_id]['status'] = 'completed_success'
            else:
                response['message'] = 'Workflow completed with errors.'
                response['final_response'] = 'NO'
                sessions[session_id]['status'] = 'completed_failed'
        elif result.get('waiting_for_input'):
            if result.get('input_type') == 'meeting_date':
                response['message'] = 'Please provide a meeting date to continue.'
                sessions[session_id]['status'] = 'waiting_meeting_date'
            else:
                response['message'] = f'Waiting for {result.get("input_type", "input")}.'
        
        print(f"Workflow response: {response.get('message', 'No message')}")
        
        return jsonify(response)
        
    except Exception as e:
        print(f"Provide input error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/workflow-status/<session_id>', methods=['GET'])
@require_auth(permission='view_status')
def get_workflow_status(session_id):
    """Get current workflow status"""
    try:
        if session_id not in sessions:
            return jsonify({'error': 'Session not found'}), 404
        
        session_data = sessions[session_id]
        
        # Check authorization
        if (session_data['user_id'] != g.current_user['user_id'] and 
            'admin' not in g.current_user.get('roles', [])):
            return jsonify({'error': 'Unauthorized access to session'}), 403
        
        # Get current workflow state
        workflow_state = workflow_manager.get_workflow_state(session_id)
        
        return jsonify({
            'session_id': session_id,
            'workflow_state': workflow_state,
            'session_data': {
                'status': session_data.get('status', 'unknown'),
                'created_at': session_data.get('created_at'),
                'user_email': session_data.get('user_email'),
                'filename': session_data.get('filename'),
                'risk_level': session_data.get('risk_assessment', {}).get('risk_level', 'unknown')
            }
        })
        
    except Exception as e:
        print(f"Get status error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/sessions', methods=['GET'])
@require_auth()
def list_sessions():
    """List all sessions for current user (for debugging)"""
    user_sessions = {}
    for session_id, session_data in sessions.items():
        if session_data['user_id'] == g.current_user['user_id']:
            user_sessions[session_id] = {
                'status': session_data.get('status', 'unknown'),
                'created_at': session_data.get('created_at'),
                'filename': session_data.get('filename'),
                'risk_level': session_data.get('risk_assessment', {}).get('risk_level', 'unknown')
            }
    
    return jsonify({
        'user_id': g.current_user['user_id'],
        'sessions': user_sessions,
        'total_sessions': len(user_sessions)
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("Starting Multi-Agent Document Processing Server...")
    print("Available endpoints:")
    print("  GET  / - Health check")
    print("  GET  /auth/profile - Get user profile")
    print("  POST /upload - Upload file for analysis")
    print("  POST /start-workflow - Start workflow")
    print("  POST /provide-input - Provide human input")
    print("  GET  /workflow-status/<session_id> - Get workflow status")
    print("  GET  /sessions - List user sessions")
    print("\nServer running on http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
